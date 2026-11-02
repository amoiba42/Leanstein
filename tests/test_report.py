"""Analysis is a pure function of logs: idempotent, deterministic (NFR-REP-1)."""
from __future__ import annotations

import json
import random

from prl.analysis.report import analyze
from prl.config import study_config


def _fake_runs(path, seed=0):
    rng = random.Random(seed)
    fams = [f"verina_basic_{i}" for i in (1, 2, 3, 4, 5, 6, 7, 8)]
    rows = []
    for m in ("qwen3.5-2b", "qwen3.5-4b"):
        for c in ("A", "B", "BP", "C", "Cplain"):
            p = {"A": .1, "B": .15, "BP": .3, "C": .45, "Cplain": .3}[c]
            for f in fams:
                for s in (11, 23, 37):
                    ok = rng.random() < p
                    rows.append({"run_id": f"{m}{c}{f}{s}", "instance_id": f + "__mut__x__0", "family_id": f,
                                 "kind": "mutant", "split": "main", "condition": c, "model": m, "seed": s,
                                 "n_attempts": 3, "total_tokens": 900, "infer_s_total": 5.0, "lean_s_total": 4.0,
                                 "stop_reason": "success" if ok else "n_gen", "success": ok,
                                 "success_attempt_idx": 2 if ok else None,
                                 "outcome": "verified_repair" if ok else "unresolved", "final_code_aux": "",
                                 "final_code": "a * b < 0", "proof_source": "portfolio" if ok and c in ("BP", "C", "Cplain") else ("model" if ok else "none"),
                                 "closing_entry": "simp_all" if ok and c in ("BP", "C", "Cplain") else None,
                                 "dist_to_ref": 0.4 if ok else None, "dist_to_start": 0.2 if ok else None,
                                 "equiv_to_ref": False if ok else None, "ref_auto": f.endswith(("1", "2")),
                                 "features": None, "flags": [], "prereg_sha": "x", "ts": 0})
    path.mkdir(parents=True, exist_ok=True)
    with open(path / "runs.jsonl", "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


def test_analyze_idempotent(tmp_path):
    _fake_runs(tmp_path / "study")
    cfg = {**study_config(), "analysis": {**study_config()["analysis"], "bootstrap": 500, "permutations": 2000}}
    analyze([tmp_path / "study"], cfg, tmp_path / "out1")
    analyze([tmp_path / "study"], cfg, tmp_path / "out2")
    for name in ("rq1_main.md", "comparisons.csv", "rq2_mechanism.md", "rq5_costs.md", "outcomes.csv"):
        a = (tmp_path / "out1" / name).read_text(encoding="utf-8")
        b = (tmp_path / "out2" / name).read_text(encoding="utf-8")
        assert a == b, name
    txt = (tmp_path / "out1" / "rq1_main.md").read_text(encoding="utf-8")
    assert "## Primary" in txt and "| qwen3.5-2b |" in txt
