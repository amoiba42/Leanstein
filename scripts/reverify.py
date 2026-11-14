"""Re-verify every logged success in Lean (post-study check; no model calls).

For each successful run, the successful attempt's code, helpers and (for proof-writing conditions) proof are read
back from `runs/<study>/attempts.jsonl` (or `.gz`) and given again to the trusted judge (`prl.lean.verify.Judge`)
in the condition's mode, with the verification cache disabled. The judge repeats every check of the study:
static integrity, compile, visible and hidden tests, the locked-specification hash, the proof (the model's proof,
or the frozen portfolio in its frozen order) and the axiom check.

    uv run python scripts/reverify.py [--studies main,heldout,...] [--threads 4] [--out results/reverify]

Resumable: results are appended to `<out>/reverify.jsonl`; finished runs are skipped. `--summary` only rewrites
`<out>/summary.md` and `<out>/reverify.csv` from that file.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

STUDIES = ["main", "main-gemma", "main-goedel", "main-bhammer", "main-shaping", "heldout"]


def _lines(path: Path):
    gz = path.with_name(path.name + ".gz")
    if path.exists():
        f = open(path, encoding="utf-8")
    elif gz.exists():
        f = gzip.open(gz, "rt", encoding="utf-8")
    else:
        return
    with f:
        for ln in f:
            ln = ln.strip()
            if ln:
                yield json.loads(ln)


def successes(study: str) -> list[dict]:
    d = ROOT / "runs" / study
    runs = {r["run_id"]: r for r in _lines(d / "runs.jsonl") if r.get("success")}
    found: dict[str, dict] = {}
    for a in _lines(d / "attempts.jsonl"):
        if a.get("success") and a["run_id"] in runs and a["run_id"] not in found:
            found[a["run_id"]] = a
    out = []
    for rid, r in runs.items():
        out.append({"study": study, "run": r, "attempt": found.get(rid)})
    return out


def summarize(out: Path) -> None:
    import pandas as pd

    rows = list(_lines(out / "reverify.jsonl"))
    if not rows:
        print("no results yet")
        return
    df = pd.DataFrame(rows)
    df.sort_values(["study", "model", "condition", "family_id", "run_id"]).to_csv(out / "reverify.csv", index=False)
    g = df.groupby(["study", "model", "condition"]).agg(
        logged_successes=("run_id", "size"), reverified=("re_success", "sum"),
        same_proof_source=("same_source", "sum"), same_closing_entry=("same_entry", "sum")).reset_index()
    tot = len(df)
    ok = int(df.re_success.sum())
    lines = ["# Re-verification of every logged success", "",
             "Each successful run's logged code (and, for proof-writing conditions, proof) was given again to the "
             "trusted judge in the condition's mode with the verification cache disabled: static integrity, "
             "compile, visible and hidden tests, locked-specification hash, proof and axioms. No model was called. "
             "Script: `scripts/reverify.py`. Machine: Windows 11 laptop, Lean 4.24.0, Mathlib v4.24.0.", "",
             f"**{ok} of {tot} logged successes re-verify** ({ok / tot:.1%}).", "",
             "| study | model | condition | logged successes | re-verified | same proof source | same closing entry |",
             "|---|---|---|---|---|---|---|"]
    for r in g.itertuples():
        lines.append(f"| {r.study} | {r.model} | {r.condition} | {r.logged_successes} | {r.reverified} | "
                     f"{r.same_proof_source} | {r.same_closing_entry} |")
    bad = df[~df.re_success]
    lines += ["", "## Runs that did not re-verify", ""]
    if bad.empty:
        lines.append("None.")
    else:
        lines += ["| study | run_id | model | condition | family | failure | detail |", "|---|---|---|---|---|---|---|"]
        for r in bad.itertuples():
            det = str(r.detail).replace("|", "\\|").replace("\n", " ")[:160]
            lines.append(f"| {r.study} | {r.run_id} | {r.model} | {r.condition} | {r.family_id} | {r.failure_kind} | {det} |")
    diff = df[df.re_success & ~df.same_entry]
    lines += ["", f"Re-verified runs whose first closing portfolio entry differs from the log: {len(diff)} "
              "(the closing entry is the first entry, in the frozen order, that closes the goal within its "
              "heartbeat budget; a different entry can win when an earlier one is close to its limit)."]
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:8]))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--studies", default=",".join(STUDIES))
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--out", default="results/reverify")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="smoke test: verify only the first N")
    a = ap.parse_args()
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    if a.summary:
        summarize(out)
        return
    os.environ.setdefault("PRL_LEAN_WORKERS", str(a.threads))
    from prl.conditions.protocols import MODE
    from prl.config import PATHS, read_json
    from prl.lean import runner
    from prl.lean.verify import Judge
    from prl.tasks.verina import Family

    done = {r["run_id"] for r in _lines(out / "reverify.jsonl")}
    todo = []
    for s in a.studies.split(","):
        items = successes(s)
        todo += [it for it in items if it["run"]["run_id"] not in done]
        print(f"{s}: {len(items)} logged successes", flush=True)
    if a.limit:
        todo = todo[:a.limit]
    print(f"to verify: {len(todo)}", flush=True)
    judge = Judge(use_cache=False)
    fams: dict[str, Family] = {}
    lock = threading.Lock()
    fh = open(out / "reverify.jsonl", "a", encoding="utf-8")

    def fam(fid: str) -> Family:
        with lock:
            if fid not in fams:
                fams[fid] = Family.from_json(read_json(PATHS.families / f"{fid}.json"))
            return fams[fid]

    def one(it: dict) -> dict:
        r, at = it["run"], it["attempt"]
        rec = {"study": it["study"], "run_id": r["run_id"], "model": r["model"], "condition": r["condition"],
               "family_id": r["family_id"], "instance_id": r["instance_id"], "seed": r["seed"],
               "logged_source": r.get("proof_source"), "logged_entry": r.get("closing_entry")}
        if at is None:
            rec.update(re_success=False, failure_kind="no_logged_attempt", detail="", re_source=None,
                       re_entry=None, same_source=False, same_entry=False, lean_s=0.0)
            return rec
        cand = {k: at.get(k) or "" for k in ("code_aux", "code", "proof_aux", "proof")}
        mode = MODE[r["condition"]]
        vr = judge.verify(fam(r["family_id"]), cand, mode)
        if vr.infra_error:  # verifier crash: retry once in a fresh worker
            vr = judge.verify(fam(r["family_id"]), cand, mode)
        detail = "; ".join((vr.lean_errors or []) + (vr.proof_errors or []) + (vr.integrity_reasons or []))
        rec.update(re_success=vr.success, failure_kind=vr.failure_kind, detail=detail[:400],
                   re_source=vr.proof_source, re_entry=vr.closing_entry,
                   same_source=vr.proof_source == r.get("proof_source"),
                   same_entry=(vr.closing_entry or None) == (r.get("closing_entry") or None),
                   lean_s=round(vr.lean_s, 2), axioms=vr.axioms)
        return rec

    t0 = time.time()
    n = ok = 0
    try:
        with ThreadPoolExecutor(a.threads) as ex:
            futs = [ex.submit(one, it) for it in todo]
            for f in as_completed(futs):
                rec = f.result()
                n += 1
                ok += bool(rec["re_success"])
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fh.flush()
                if n % 50 == 0 or n == len(todo):
                    el = time.time() - t0
                    print(f"{n}/{len(todo)} done, {ok} re-verified, {el / 60:.1f} min, "
                          f"eta {el / n * (len(todo) - n) / 60:.0f} min", flush=True)
    finally:
        fh.close()
        runner.shutdown()
    summarize(out)


if __name__ == "__main__":
    main()
