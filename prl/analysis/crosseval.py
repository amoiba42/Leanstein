"""B→C cross-evaluation (FR-ANA-7): secondary analysis, never part of the primary B or C estimates.

Every attempt of a proof-writing condition (default: B) whose code compiled but whose model proof failed is
re-verified as *code only* through C's complete pipeline: static integrity, visible and hidden tests, the
frozen portfolio and `#print axioms`. The portfolio is run even when tests fail, so each candidate lands in
exactly one bucket:

* ``c_proves_tests_pass``  – the portfolio proves it and all tests pass: a verified repair B's proof missed
* ``c_proves_tests_fail``  – the portfolio proves it but tests fail: the spec is too weak for this
                             behaviour (a finding about the contract, never counted as a repair)
* ``c_cannot_prove``       – the portfolio does not close the theorem (includes timeouts)
* ``c_rejected_integrity`` – C's static checks reject the code (expected to be rare; reported separately)

No model is called; only Lean (CPU). Records go to ``runs/<study>/crosseval.jsonl`` with
``analysis_kind="b_to_c_cross_eval"``; the step is resumable and de-duplicates identical code per family.
"""
from __future__ import annotations

import concurrent.futures as cf
from pathlib import Path
from typing import Any

import pandas as pd

from prl.conditions.protocols import verify_with_infra_retry
from prl.config import sha256_text
from prl.driver.runner import JsonlWriter, read_jsonl
from prl.lean.verify import VerifyResult
from prl.tasks.verina import get_family

ANALYSIS_KIND = "b_to_c_cross_eval"
BUCKETS = ("c_proves_tests_pass", "c_proves_tests_fail", "c_cannot_prove", "c_rejected_integrity")


def eligible(attempt: dict[str, Any]) -> bool:
    """Code compiled, the model's proof did not close the theorem."""
    v = attempt.get("verify") or {}
    return bool(attempt.get("extract_ok")) and bool(v.get("compile_ok")) and not v.get("proof_ok")


def code_key(family_id: str, cand: dict[str, str]) -> str:
    return sha256_text(family_id + "\x00" + cand["code_aux"] + "\x00" + cand["code"])[:20]


def bucket(vr: VerifyResult) -> str:
    if not vr.static_ok or not vr.integrity_ok:
        return "c_rejected_integrity"
    if not vr.proof_ok:
        return "c_cannot_prove"
    return "c_proves_tests_pass" if vr.tests_pass else "c_proves_tests_fail"


def cross_evaluate(study_dir: Path, judge, *, conditions: tuple[str, ...] = ("B",), workers: int = 4,
                   log=print) -> dict[str, int]:
    attempts = [a for a in read_jsonl(study_dir / "attempts.jsonl") if a.get("condition") in conditions and eligible(a)]
    out_path = study_dir / "crosseval.jsonl"
    done = {(r["run_id"], r["attempt_idx"]) for r in read_jsonl(out_path)}
    known: dict[str, dict[str, Any]] = {r["code_key"]: r for r in read_jsonl(out_path)}
    todo = [a for a in attempts if (a["run_id"], a["attempt_idx"]) not in done]
    log(f"cross-evaluation: {len(attempts)} eligible attempts, {len(attempts) - len(todo)} done, {len(todo)} to do")
    writer = JsonlWriter(out_path)

    def verify_code(fid: str, cand: dict[str, str]) -> dict[str, Any]:
        vr = verify_with_infra_retry(judge, get_family(fid), cand, "portfolio", force_portfolio=True)
        return {"bucket": bucket(vr), "closing_entry": vr.closing_entry, "c_failure_kind": vr.failure_kind,
                "visible_pass": vr.visible_pass, "hidden_pass": vr.hidden_pass, "axioms": vr.axioms}

    # verify each distinct code once, then write one record per attempt
    uniq: dict[str, tuple[str, dict[str, str]]] = {}
    for a in todo:
        cand = {"code_aux": a.get("code_aux", ""), "code": a.get("code", "")}
        k = code_key(a["family_id"], cand)
        if k not in known:
            uniq.setdefault(k, (a["family_id"], cand))
    with cf.ThreadPoolExecutor(max(1, workers)) as ex:
        futs = {ex.submit(verify_code, fid, cand): k for k, (fid, cand) in uniq.items()}
        for n, f in enumerate(cf.as_completed(futs), 1):
            known[futs[f]] = f.result()
            if n % 20 == 0 or n == len(futs):
                log(f"cross-evaluation: {n}/{len(futs)} distinct candidates verified")
    counts = dict.fromkeys(BUCKETS, 0)
    for a in todo:
        cand = {"code_aux": a.get("code_aux", ""), "code": a.get("code", "")}
        k = code_key(a["family_id"], cand)
        res = {kk: known[k][kk] for kk in ("bucket", "closing_entry", "c_failure_kind", "visible_pass",
                                           "hidden_pass", "axioms")}
        counts[res["bucket"]] += 1
        writer.write({"analysis_kind": ANALYSIS_KIND, "run_id": a["run_id"], "attempt_idx": a["attempt_idx"],
                      "family_id": a["family_id"], "instance_id": a["instance_id"], "condition": a["condition"],
                      "model": a["model"], "seed": a["seed"], "study_id": a.get("study_id"), "code_key": k,
                      "b_failure_kind": a.get("failure_kind"), **res})
    return counts


def load_crosseval(study_dirs: list[Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for d in study_dirs:
        rows += read_jsonl(d / "crosseval.jsonl")
    return pd.DataFrame(rows)


def crosseval_tables(ce: pd.DataFrame, runs: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(attempt-level bucket counts, run-level rescue rates) per (model, condition)."""
    if ce.empty:
        return pd.DataFrame(), pd.DataFrame()
    att = ce.groupby(["model", "condition", "bucket"]).size().unstack(fill_value=0)
    for b in BUCKETS:
        if b not in att:
            att[b] = 0
    att = att[list(BUCKETS)]
    att["eligible_attempts"] = att.sum(axis=1)
    att = att.reset_index()
    rows = []
    rescued = set(ce[ce.bucket == "c_proves_tests_pass"].run_id)
    weak = set(ce[ce.bucket == "c_proves_tests_fail"].run_id)
    if not runs.empty:
        for (m, c), g in runs[runs.condition.isin(ce.condition.unique())].groupby(["model", "condition"]):
            failed = g[~g.success]
            rows.append({"model": m, "condition": c, "runs": len(g), "failed_runs": len(failed),
                         "failed_runs_rescued_by_C": int(failed.run_id.isin(rescued).sum()),
                         "rescue_rate_of_failed": float(failed.run_id.isin(rescued).mean()) if len(failed) else float("nan"),
                         "runs_with_weak_spec_candidate": int(g.run_id.isin(weak).sum())})
    return att, pd.DataFrame(rows)
