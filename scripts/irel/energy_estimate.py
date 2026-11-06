#!/usr/bin/env python3
"""Per-condition energy estimate from the post-hoc calibration (deviation D-4).

GPU (estimate): every model call in the study is charged a * completion_tokens + b * prompt_tokens, with a and b
(J/token) measured for that model on our slice by energy_calib.py (mean of three cycles; the min and max over
cycles give the range). CPU (estimate): each run's Lean seconds x the pre-registered 5.47 W per thread.
CO2: total x 0.716 kg/kWh (pre-registered). Writes results/rq5_energy_estimate.{csv,md}.

Usage: python scripts/irel/energy_estimate.py CALIB_DIR [RESULTS_DIR]
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prl.analysis.report import _md_table  # noqa: E402
from prl.driver.runner import read_jsonl  # noqa: E402

STUDIES = {"main": ["main", "main-shaping", "main-gemma", "main-goedel", "main-bhammer"], "heldout": ["heldout"]}
W_PER_THREAD, KG_PER_KWH = 5.47, 0.716


def coefficients(calib_dir: Path) -> pd.DataFrame:
    rows = []
    for f in sorted(calib_dir.glob("calib_*_p12.json")):
        d = json.loads(f.read_text())
        c = pd.DataFrame(d["cycles"])
        rows.append({"model": d["model"], "a_mean": c.j_per_completion_token.mean(), "a_min": c.j_per_completion_token.min(),
                     "a_max": c.j_per_completion_token.max(), "b_mean": c.j_per_prompt_token.mean(),
                     "b_min": c.j_per_prompt_token.min(), "b_max": c.j_per_prompt_token.max(),
                     "idle_w": pd.Series([w["baseline_w"] for w in d["windows"]]).mean()})
    return pd.DataFrame(rows)


def estimate(group: str, coef: pd.DataFrame) -> pd.DataFrame:
    att, runs = [], []
    for st in STUDIES[group]:
        d = ROOT / "runs" / st
        att += [{"model": a["model"], "condition": a["condition"], "tin": a.get("tokens_in") or 0,
                 "tout": a.get("tokens_out") or 0} for a in read_jsonl(d / "attempts.jsonl")]
        runs += [{"model": r["model"], "condition": r["condition"], "lean_s": r.get("lean_s_total") or 0.0,
                  "success": bool(r.get("success"))} for r in read_jsonl(d / "runs.jsonl")]
    a = pd.DataFrame(att).groupby(["model", "condition"])[["tin", "tout"]].sum()
    r = pd.DataFrame(runs).groupby(["model", "condition"]).agg(runs=("success", "size"), repairs=("success", "sum"),
                                                                lean_s=("lean_s", "sum"))
    t = a.join(r).reset_index().merge(coef, on="model", how="left")
    for k in ("mean", "min", "max"):
        t[f"gpu_kj_{k}"] = (t[f"a_{k}"] * t.tout + t[f"b_{k}"] * t.tin) / 1000
    t["cpu_kj"] = t.lean_s * W_PER_THREAD / 1000
    t["total_kj"] = t.gpu_kj_mean + t.cpu_kj
    t["kj_per_repair"] = t.total_kj / t.repairs.where(t.repairs > 0)
    t["kj_per_repair_lo"] = (t.gpu_kj_min + t.cpu_kj) / t.repairs.where(t.repairs > 0)
    t["kj_per_repair_hi"] = (t.gpu_kj_max + t.cpu_kj) / t.repairs.where(t.repairs > 0)
    t["co2_g"] = t.total_kj * 1000 / 3.6e6 * KG_PER_KWH * 1000
    t["co2_g_per_repair"] = t.co2_g / t.repairs.where(t.repairs > 0)
    t.insert(0, "split", group)
    return t


def main():
    calib = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "results"
    coef = coefficients(calib)
    t = pd.concat([estimate(g, coef) for g in STUDIES])
    coef.to_csv(out / "energy_coefficients.csv", index=False)
    t.to_csv(out / "rq5_energy_estimate.csv", index=False)
    cols = ["split", "model", "condition", "runs", "repairs", "gpu_kj_mean", "cpu_kj", "total_kj", "kj_per_repair",
            "kj_per_repair_lo", "kj_per_repair_hi", "co2_g_per_repair"]
    md = ["# RQ5 energy (estimate, deviation D-4)", "",
          "GPU energy = calibrated J per completion token and per prompt token (marginal board power of GPU 1 over its "
          "idle baseline, our slice, study serving settings) x the tokens each condition used. CPU = Lean seconds x "
          f"{W_PER_THREAD} W/thread. CO2 at {KG_PER_KWH} kg/kWh. Range = min/max of the three calibration cycles. "
          "Static (idle) GPU power is shared with other tenants and not attributed.", "",
          "## Coefficients", "", _md_table(coef, "{:.4f}"), "",
          "## Per condition", "", _md_table(t[cols], "{:.2f}"), ""]
    (out / "rq5_energy_estimate.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
