"""Exploratory (not pre-registered): C against B and BP on the bug instances whose reference implementation the
portfolio can NOT prove (`ref_auto == False`). On these instances a verified repair cannot be a plain revert to
the reference, so the comparison isolates repairs that need an automation-friendly re-shaping.

    uv run python scripts/exploratory_shaping.py   # -> results/exploratory_shaping.{csv,md}

Same statistics as the confirmatory tests (family score = mean over seeds of "any instance solved"; one-sided
sign-flip test; 95% family-cluster bootstrap CI), but no multiplicity correction: these tests are exploratory.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from prl.analysis.report import _md_table, compare, load_runs, with_derived  # noqa: E402
from prl.config import study_config  # noqa: E402


def main() -> None:
    cfg = study_config()
    df = with_derived(load_runs([ROOT / "runs" / s for s in ("main", "main-gemma")]))
    df = df[df.kind.isin(["natural", "mutant"])]
    rows = []
    for subset, sub in (("reference not provable", df[df.ref_auto == False]),  # noqa: E712
                        ("reference provable", df[df.ref_auto == True]),  # noqa: E712
                        ("all (primary pool)", df)):
        for model in ("qwen3.5-2b", "qwen3.5-4b", "gemma-4-e4b-it"):
            for x, y in (("C", "B"), ("C", "BP")):
                r = compare(sub, x, y, model, ("natural", "mutant"), cfg)
                if r:
                    rows.append({"subset": subset, **r})
    out = pd.DataFrame(rows)
    keep = ["subset", "model", "x", "y", "n_families", "rate_x", "rate_y", "diff", "ci_lo", "ci_hi", "p_signflip",
            "only_x", "only_y"]
    out = out[keep]
    out.to_csv(ROOT / "results" / "exploratory_shaping.csv", index=False)
    md = ["# Exploratory: C against B and BP where the reference is not provable", "",
          "Not a pre-registered test (no Holm correction). `reference not provable` keeps only bug instances whose "
          "reference implementation the frozen portfolio cannot prove (condition T), so a verified repair there "
          "must have a different shape from the reference. Family score = mean over seeds of 'any instance "
          "solved'; one-sided sign-flip p; 95% family-cluster bootstrap CI. Studies `main` and `main-gemma`.",
          "", _md_table(out)]
    (ROOT / "results" / "exploratory_shaping.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
