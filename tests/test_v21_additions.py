"""v2.1 additions (adopted from the team's revision-3 notes): proof-tactic logging, Bhammer, B→C
cross-evaluation, the pre-freeze power simulation and the configuration guards. No Lean, no LLM."""
from __future__ import annotations

import json

import numpy as np
import pytest

from prl.analysis import crosseval as CE
from prl.analysis import stats as S
from prl.analysis.report import analyze, with_derived
from prl.conditions.protocols import proof_log, run_condition, tactic_menu
from prl.config import study_config
from prl.lean import leantext as LT
from prl.lean.portfolio import load_portfolio
from prl.lean.verify import Judge, VerifyResult, classify_failure
from tests.test_protocols_driver import CFG, FAM, INST, FakeGen, FakeJudge


# ---------------------------------------------------------------- proof_tactic_used (FR-ANA-8)
def test_proof_tactics_normalised():
    assert LT.proof_tactics("simp [foo, bar] <;> omega") == ["omega", "simp"]
    assert LT.proof_tactics("intro h\n  induction xs with\n  | nil => simp\n  | cons x xs ih => simp_all") == [
        "induction", "intro", "simp", "simp_all"]
    assert LT.proof_tactics("simp? -- grind in a comment\n") == ["simp"]
    assert LT.proof_tactics("first | (simp_all; done) | grind") == ["first", "grind", "simp_all"]


def test_automation_only_definition():
    reg = load_portfolio().single_call_automation
    assert LT.automation_only(LT.proof_tactics("unfold f\ngrind"), "", reg)
    assert LT.automation_only(LT.proof_tactics("simp_all <;> omega"), "", reg)
    assert not LT.automation_only(LT.proof_tactics("exact Nat.le_refl _"), "", reg)
    assert not LT.automation_only(LT.proof_tactics("intro h"), "", reg)          # glue alone is not a proof
    assert not LT.automation_only(["grind"], "theorem aux : True := trivial", reg)  # helper lemma


def test_attempt_records_carry_proof_tactics():
    rr = run_condition("B", INST, FAM, "m", 11, CFG, FakeJudge(), FakeGen(None, proof=True))
    assert all(a["proof_tactic_used"] == ["simp"] and a["automation_only_proof"] for a in rr.attempts)
    rr = run_condition("C", INST, FAM, "m", 11, CFG, FakeJudge(), FakeGen(None))
    assert all("proof_tactic_used" not in a for a in rr.attempts)
    assert proof_log({"proof": "exact foo", "proof_aux": ""}) == {"proof_tactic_used": ["exact"],
                                                                  "automation_only_proof": False}


# ---------------------------------------------------------------- Bhammer (FR-ANA-9)
def test_bhammer_prompt_lists_the_frozen_portfolio_and_nothing_else_differs():
    menu = tactic_menu(FAM, INST.start["code_aux"], INST.start["code"])
    assert "grind [hasOppositeSign" in menu and "decide" in menu and "\n" in menu
    firsts = {}
    for c in ("B", "Bhammer"):
        g = FakeGen(1, proof=True)
        run_condition(c, INST, FAM, "m", 11, CFG, FakeJudge(), g)
        firsts[c] = g.calls[0][1]["content"]
    assert menu in firsts["Bhammer"] and menu not in firsts["B"]
    assert firsts["B"].split("## Instructions")[0] == firsts["Bhammer"].split("## Instructions")[0]


def test_bhammer_feedback_is_B_feedback():
    g = FakeGen(None, proof=True)
    run_condition("Bhammer", INST, FAM, "m", 11, CFG, FakeJudge(), g)
    assert "Fix the implementation and/or the proof" in g.calls[1][-1]["content"]


# ---------------------------------------------------------------- B→C cross-evaluation (FR-ANA-7)
GOOD = "(a < 0 && b > 0) || (a > 0 && b < 0)"


class XJudge:
    """Portfolio proves GOOD (tests pass) and `a * b < 0` (tests 'fail' here: weak-spec bucket)."""

    def __init__(self):
        self.calls = 0

    def verify(self, fam, cand, mode, *, tests="all", skip_static=False, full_vector=False, force_portfolio=False):
        assert mode == "portfolio" and force_portfolio and not cand.get("proof")
        self.calls += 1
        code = cand["code"].strip()
        vr = VerifyResult(mode, True, [], compile_ok=True, visible_pass=code == GOOD, hidden_pass=code == GOOD)
        if code in (GOOD, "a * b < 0"):
            vr.proof_ok, vr.proof_source, vr.closing_entry = True, "portfolio", "simp_all"
        vr.failure_kind = classify_failure(vr)
        return vr


def _attempt(run_id, idx, code, compile_ok=True, proof_ok=False, cond="B"):
    return {"run_id": run_id, "attempt_idx": idx, "family_id": FAM.family_id, "instance_id": INST.instance_id,
            "condition": cond, "model": "m", "seed": 11, "extract_ok": True, "code_aux": "", "code": code,
            "proof": "simp", "failure_kind": "proof", "verify": {"compile_ok": compile_ok, "proof_ok": proof_ok}}


def test_crosseval_buckets_and_dedup(tmp_path, monkeypatch):
    monkeypatch.setattr(CE, "get_family", lambda fid: FAM)
    rows = [_attempt("r1", 0, GOOD), _attempt("r1", 1, GOOD), _attempt("r2", 0, "a * b < 0"),
            _attempt("r3", 0, "a * b ≤ 0"), _attempt("r4", 0, GOOD, compile_ok=False),
            _attempt("r5", 0, GOOD, proof_ok=True), _attempt("r6", 0, GOOD, cond="C")]
    (tmp_path / "attempts.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    j = XJudge()
    counts = CE.cross_evaluate(tmp_path, j, workers=1, log=lambda *_: None)
    assert counts == {"c_proves_tests_pass": 2, "c_proves_tests_fail": 1, "c_cannot_prove": 1,
                      "c_rejected_integrity": 0}
    assert j.calls == 3  # identical code verified once
    recs = [json.loads(x) for x in (tmp_path / "crosseval.jsonl").read_text(encoding="utf-8").splitlines()]
    assert all(r["analysis_kind"] == "b_to_c_cross_eval" for r in recs) and len(recs) == 4
    assert CE.cross_evaluate(tmp_path, j, workers=1, log=lambda *_: None)["c_proves_tests_pass"] == 0  # resumable
    assert j.calls == 3


# ---------------------------------------------------------------- power simulation (SR-STAT-4)
def test_pilot_power_finds_n_for_a_large_effect_and_none_without_effect():
    big = S.pilot_power(p01=0.02, p10=0.30, p_both=0.2, alpha=0.0125, sims=200, n_perm=499, n_max=200)
    assert big["required_n"] is not None and 10 <= big["required_n"] <= 80
    none = S.pilot_power(p01=0.10, p10=0.10, p_both=0.2, alpha=0.0125, sims=200, n_perm=499, n_max=200)
    assert none["required_n"] is None


def test_simulate_power_uses_family_pairs():
    pairs = {"only_x": [(2 / 3, 1 / 3)], "only_y": [(1 / 3, 2 / 3)], "both": [(1.0, 1.0)], "neither": [(0.0, 0.0)]}
    probs = {"both": 0.2, "only_x": 0.3, "only_y": 0.02, "neither": 0.48}
    a = S.simulate_power(probs, 60, pairs=pairs, alpha=0.0125, sims=200, n_perm=499, seed=1)
    b = S.simulate_power(probs, 60, alpha=0.0125, sims=200, n_perm=499, seed=1)
    assert 0 <= a["power_signflip"] <= b["power_signflip"] <= 1  # partial-seed scores carry less signal
    assert np.isfinite(a["power_mcnemar"])


# ---------------------------------------------------------------- analysis integration
def _runs(path):
    rows = []
    for c in ("B", "C"):
        for f in range(1, 7):
            for s in (11, 23, 37):
                ok = (c == "C") or f <= 3
                rows.append({"run_id": f"{c}{f}{s}", "instance_id": f"verina_basic_{f}__mut__x__0",
                             "family_id": f"verina_basic_{f}", "kind": "mutant", "split": "main", "condition": c,
                             "model": "qwen3.5-2b", "seed": s, "n_attempts": 2, "total_tokens": 500,
                             "infer_s_total": 2.0, "lean_s_total": 1.0, "stop_reason": "success" if ok else "n_gen",
                             "success": ok, "success_attempt_idx": 1 if ok else None,
                             "outcome": "verified_repair" if ok else "unresolved", "final_code_aux": "",
                             "final_code": "x", "proof_source": ("model" if c == "B" else "portfolio") if ok else "none",
                             "closing_entry": None, "proof_tactic_used": ["grind"] if (ok and c == "B") else None,
                             "automation_only_proof": (f == 1) if (ok and c == "B") else None,
                             "dist_to_ref": 0.3 if ok else None, "dist_to_start": 0.1 if ok else None,
                             "equiv_to_ref": False if ok else None, "ref_auto": False, "features": None,
                             "flags": [], "prereg_sha": "x", "ts": 0})
    path.mkdir(parents=True, exist_ok=True)
    (path / "runs.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    ce = [{"analysis_kind": CE.ANALYSIS_KIND, "run_id": "B511", "attempt_idx": 0, "family_id": "verina_basic_5",
           "condition": "B", "model": "qwen3.5-2b", "seed": 11, "bucket": "c_proves_tests_pass"}]
    (path / "crosseval.jsonl").write_text("".join(json.dumps(r) + "\n" for r in ce), encoding="utf-8")


def test_derived_B_noauto_and_crosseval_report(tmp_path):
    import pandas as pd
    _runs(tmp_path / "s")
    df = pd.DataFrame([json.loads(x) for x in (tmp_path / "s" / "runs.jsonl").read_text().splitlines()])
    d = with_derived(df)
    assert d[d.condition == "B"].success.sum() == 9 and d[d.condition == "B_noauto"].success.sum() == 6
    cfg = {**study_config(), "analysis": {**study_config()["analysis"], "bootstrap": 200, "permutations": 500}}
    analyze([tmp_path / "s"], cfg, tmp_path / "out")
    comp = pd.read_csv(tmp_path / "out" / "comparisons.csv")
    assert {"B", "B_noauto"} <= set(comp.y) and not comp[comp.y == "B_noauto"].primary.any()
    txt = (tmp_path / "out" / "crosseval.md").read_text(encoding="utf-8")
    assert "c_proves_tests_pass" in txt and "| qwen3.5-2b | B |" in txt
    costs = pd.read_csv(tmp_path / "out" / "rq5_costs.csv")
    assert "B_noauto" not in set(costs.condition)  # derived rows never enter costs


# ---------------------------------------------------------------- configuration guards
def test_wall_guard_minimum():
    cfg = study_config()
    with pytest.raises(ValueError):
        Judge({**cfg, "lean": {**cfg["lean"], "wall_guard_s": 20}})


def test_portfolio_rejects_unbounded_heartbeats(tmp_path):
    p = tmp_path / "pf.yaml"
    p.write_text("version: 1\nmax_entries: 2\ntiers:\n  L: {heartbeats: 0}\nentries:\n"
                 "  - {id: simp, tier: L, script: simp}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_portfolio(str(p))


def test_freeze_requires_power_note(monkeypatch):
    import prl.analysis.power as PW
    from prl import cli
    monkeypatch.setattr(PW, "has_power_note", lambda: False)
    called = []
    monkeypatch.setattr("prl.prereg.freeze", lambda note="": called.append(note))
    assert cli.main(["freeze"]) == 2 and not called


def test_study_config_declares_new_arms():
    cfg = study_config()
    assert cfg["exploratory_conditions"] == ["Bhammer"] and cfg["crosseval_conditions"] == ["B"]
    assert "Bhammer" not in cfg["conditions"]  # never part of the main plan by default


def test_primary_pool_uses_dataset_count_and_heldout_is_labelled(tmp_path):
    import pandas as pd

    from prl.analysis.report import primary_pool
    cfg = {"bugs": {"primary": "natural", "min_natural_families": 60}}
    pilot = pd.DataFrame({"split": ["pilot"], "kind": ["natural"], "family_id": ["a"]})
    assert primary_pool(pilot, cfg, n_natural=75)[0] == ("natural",)   # pilot rows do not decide the pool
    assert primary_pool(pilot, cfg, n_natural=10)[0] == ("mutant", "natural")
    _runs(tmp_path / "h")
    rows = [json.loads(x) for x in (tmp_path / "h" / "runs.jsonl").read_text().splitlines()]
    (tmp_path / "h" / "runs.jsonl").write_text("".join(json.dumps({**r, "split": "heldout"}) + "\n" for r in rows))
    cfg = {**study_config(), "analysis": {**study_config()["analysis"], "bootstrap": 200, "permutations": 500}}
    analyze([tmp_path / "h"], cfg, tmp_path / "out")
    assert (tmp_path / "out" / "rq1_main.md").read_text(encoding="utf-8").startswith(
        "# RQ1 (held-out replication, not confirmatory)")
