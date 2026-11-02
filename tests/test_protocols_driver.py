"""Protocol + driver tests with a fake generator and a fake judge (no Lean, no LLM)."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from prl.conditions.protocols import Budget, run_condition
from prl.driver.runner import Runner, plan, read_jsonl
from prl.lean.verify import VerifyResult
from prl.tasks import verina as V
from prl.tasks.instances import Instance

FAM = V.load_family(V.PATHS.verina_tasks / "verina_basic_1")
GOOD = "(a < 0 && b > 0) || (a > 0 && b < 0)"


def _out(code: str, proof: bool = False) -> str:
    s = f"```lean\n{FAM.header}\n  {code}\n```"
    if proof:
        s += f"\n```lean\ntheorem {FAM.fn}_spec_satisfied {FAM.theorem_stmt} := by\n  simp\n```"
    return s


@dataclass
class Comp:
    text: str
    tokens_in: int = 100
    tokens_out: int = 50
    finish_reason: str = "stop"
    elapsed_s: float = 1.0


class FakeGen:
    """Returns wrong code until the k-th call, then GOOD."""

    def __init__(self, succeed_at: int | None = None, proof: bool = False):
        self.n = 0
        self.succeed_at = succeed_at
        self.proof = proof
        self.calls: list[list[dict]] = []

    def complete(self, model, messages, *, seed, temperature, top_p, max_tokens):
        self.calls.append(messages)
        self.n += 1
        code = GOOD if (self.succeed_at is not None and self.n >= self.succeed_at) else "a * b ≤ 0"
        return Comp(_out(code, self.proof))


class FakeJudge:
    def verify(self, fam, cand, mode, *, tests="all", skip_static=False, full_vector=False):
        ok = cand["code"].strip() == GOOD
        vr = VerifyResult(mode, True, [], compile_ok=True, visible_pass=ok, hidden_pass=ok,
                          test_vector=[ok], n_visible_fail=0 if ok else 1)
        if ok:
            vr.proof_ok, vr.proof_source, vr.closing_entry = True, "portfolio", "simp_all"
        else:
            vr.entry_goals = {"simp": "⊢ False"}
        from prl.lean.verify import classify_failure
        vr.failure_kind = classify_failure(vr)
        return vr

    def witness_line(self, fam, cand, vr):
        return None if vr.tests_pass else "Failing test: hasOppositeSign (a := 0, b := 1) returned true, expected false."


CFG = {"study_id": "t", "budget": {"n_gen": 8, "max_total_tokens": 48000, "max_completion_tokens": 512, "max_infer_s": 240},
       "decoding": {"temperature": 0.7, "top_p": 0.95}, "c_round_k": 2, "history_turns": 2}
INST = Instance("verina_basic_1__mut__x__0", "verina_basic_1", "mutant", {"code_aux": "", "code": "a * b ≤ 0"},
                witness={"source": "visible", "index": 0, "input_lean": {"a": "0", "b": "1"}, "expected": "false",
                         "actual": "true"})


@pytest.mark.parametrize("cond", ["A", "B", "BP", "C", "Cplain"])
def test_success_stops_early(cond):
    g = FakeGen(succeed_at=3, proof=cond in ("A", "B", "BP"))
    rr = run_condition(cond, INST, FAM, "m", 11, CFG, FakeJudge(), g)
    assert rr.success and rr.success_idx == 2 and rr.stop_reason == "success" and len(rr.attempts) == 3


@pytest.mark.parametrize("cond", ["A", "B", "BP", "C", "Cplain"])
def test_budget_exhausts_at_n_gen(cond):
    rr = run_condition(cond, INST, FAM, "m", 11, CFG, FakeJudge(), FakeGen(None, cond in ("A", "B", "BP")))
    assert not rr.success and rr.stop_reason == "n_gen" and len(rr.attempts) == 8


def test_token_cap_binds():
    cfg = {**CFG, "budget": {**CFG["budget"], "max_total_tokens": 450}}
    rr = run_condition("C", INST, FAM, "m", 11, cfg, FakeJudge(), FakeGen(None))
    assert rr.stop_reason == "tokens" and len(rr.attempts) == 3  # 150 tokens per call


def test_condition_A_has_no_history_and_distinct_seeds():
    g = FakeGen(None, proof=True)
    rr = run_condition("A", INST, FAM, "m", 11, CFG, FakeJudge(), g)
    assert all(len(m) == 2 for m in g.calls)
    assert len({a["seed_used"] for a in rr.attempts}) == 8


def test_C_rounds_share_history_and_hint_feedback():
    g = FakeGen(None)
    run_condition("C", INST, FAM, "m", 11, CFG, FakeJudge(), g)
    lens = [len(m) for m in g.calls]
    assert lens[:2] == [2, 2] and lens[2:4] == [4, 4]  # feedback only after a round of k=2
    fb = g.calls[2][-1]["content"]
    assert "Failing test" in fb and "Do NOT write any proof" in fb


def test_Cplain_feedback_has_no_information():
    g = FakeGen(None)
    run_condition("Cplain", INST, FAM, "m", 11, CFG, FakeJudge(), g)
    fb = g.calls[2][-1]["content"]
    assert fb.startswith("The candidate was rejected. Try again.") and "Failing" not in fb


def test_turn0_information_equal_across_conditions():
    firsts = {}
    for c in ("B", "BP", "C", "Cplain"):
        g = FakeGen(1, proof=c in ("B", "BP"))
        run_condition(c, INST, FAM, "m", 11, CFG, FakeJudge(), g)
        firsts[c] = g.calls[0][1]["content"]
    for c in firsts:
        assert "Failing test" in firsts[c]
        assert firsts[c].split("## Instructions")[0] == firsts["B"].split("## Instructions")[0]


def test_prompt_never_leaks_reference_or_hidden():
    g = FakeGen(None)
    run_condition("C", INST, FAM, "m", 11, CFG, FakeJudge(), g)
    ref_body = FAM.region("code").strip()
    for msgs in g.calls:
        text = "\n".join(m["content"] for m in msgs)
        # the start code differs from the reference by the mutation, so the reference body must not appear
        assert ref_body not in text.replace("a * b ≤ 0", "")
        assert "data/hidden" not in text and "hidden_tests" not in text
        # the human reference proof must never be shown
        assert "Int.mul_neg_of_neg_of_pos" not in text and "mul_neg_iff" not in text


def test_budget_class():
    b = Budget(2, 1000, 10)
    b.charge(10, 1)
    assert b.exhausted() is None
    b.charge(10, 1)
    assert b.exhausted() == "n_gen"


def test_driver_resume_identical(tmp_path, monkeypatch):
    import prl.driver.runner as DR
    monkeypatch.setattr(DR, "get_family", lambda fid: FAM)
    insts = {INST.instance_id: INST}
    specs = plan([INST], ["C", "B"], ["m"], [11, 23])
    r1 = Runner(tmp_path / "a", CFG, FakeJudge(), FakeGen(None), run_workers=1, log=lambda *_: None)
    r1.run_all(specs[:2], insts)          # simulate a crash after two runs
    r1.attempts.write({"run_id": "orphan", "attempt_idx": 0})  # torn partial run
    r2 = Runner(tmp_path / "a", CFG, FakeJudge(), FakeGen(None), run_workers=1, log=lambda *_: None)
    r2.run_all(specs, insts)
    runs = read_jsonl(tmp_path / "a" / "runs.jsonl")
    att = read_jsonl(tmp_path / "a" / "attempts.jsonl")
    assert len(runs) == 4 and len({r["run_id"] for r in runs}) == 4
    assert all(a["run_id"] != "orphan" for a in att)
    assert len(att) == sum(r["n_attempts"] for r in runs)
    r3 = Runner(tmp_path / "a", CFG, FakeJudge(), FakeGen(None), run_workers=1, log=lambda *_: None)
    assert r3.run_all(specs, insts)["ok"] == 0  # nothing left to do
