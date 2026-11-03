"""Pre-freeze power note from the pilot (SR-STAT-4, implementation plan R-7).

For each primary model and primary comparison (C vs B, C vs BP) the pilot gives family-level majority-solved
outcomes. Twenty pilot families give noisy proportions, so three scenarios are simulated:

* ``point``       – the observed proportions (add-½ smoothed so empty cells are not impossible)
* ``pessimistic`` – p10 (C-only) at the lower and p01 (baseline-only) at the upper 80% Jeffreys bound
* ``optimistic``  – the reverse

The simulated test is the confirmatory one: one-sided paired sign-flip on family scores (mean over the three
seeds), at the Bonferroni bound of the Holm procedure (alpha / number of primary tests), which is the
smallest per-test level Holm can require. The exact McNemar rate on the majority binary is reported beside
it. Power applies to the confirmatory `main` split; the required count is converted to total eligible
families as ceil(n_main / (1 - heldout_frac)) + pilot_n.

The note is written to ``prereg/power_note.json`` (frozen with the rest of prereg/) and
``results/power_note.md``. VERINA is fixed, so an underpowered result cannot add families; it is recorded as a
limitation before the freeze.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from scipy import stats as st

from prl.analysis import stats as S
from prl.analysis.report import PRIMARY_COMPARISONS, _md_table, family_scores, load_runs, primary_pool
from prl.config import PATHS, ensure_dir, read_json

NOTE_PATH = PATHS.prereg / "power_note.json"


def _jeffreys(k: int, n: int, level: float = 0.80) -> tuple[float, float]:
    a = (1 - level) / 2
    return float(st.beta.ppf(a, k + 0.5, n - k + 0.5)), float(st.beta.ppf(1 - a, k + 0.5, n - k + 0.5))


def pilot_estimates(sx, sy) -> tuple[dict[str, int], dict[str, list[tuple[float, float]]]]:
    fams = sorted(set(sx.index) & set(sy.index))
    counts = dict.fromkeys(S.CATS, 0)
    pairs: dict[str, list[tuple[float, float]]] = {c: [] for c in S.CATS}
    for f in fams:
        x, y = float(sx[f]), float(sy[f])
        c = ("both" if y > 0.5 else "only_x") if x > 0.5 else ("only_y" if y > 0.5 else "neither")
        counts[c] += 1
        pairs[c].append((x, y))
    return counts, pairs


def scenarios(counts: dict[str, int]) -> dict[str, dict[str, float]]:
    n = sum(counts.values())
    sm = {c: (counts[c] + 0.5) / (n + 2.0) for c in S.CATS}
    lo10, hi10 = _jeffreys(counts["only_x"], n)
    lo01, hi01 = _jeffreys(counts["only_y"], n)
    out = {"point": {"p10": sm["only_x"], "p01": sm["only_y"], "p_both": sm["both"]},
           "pessimistic": {"p10": lo10, "p01": hi01, "p_both": sm["both"]},
           "optimistic": {"p10": hi10, "p01": lo01, "p_both": sm["both"]}}
    for v in out.values():  # keep a valid distribution
        tot = v["p10"] + v["p01"] + v["p_both"]
        if tot > 1:
            v["p_both"] = max(0.0, 1 - v["p10"] - v["p01"])
    return out


def power_note(pilot_dir: Path, cfg: dict[str, Any], *, log=print) -> dict[str, Any]:
    df = load_runs([pilot_dir])
    if df.empty:
        raise RuntimeError(f"no pilot runs in {pilot_dir}")
    pc = cfg["analysis"].get("power", {})
    target = float(pc.get("target", 0.80))
    sims, n_perm = int(pc.get("sims", 500)), int(pc.get("permutations", 999))
    seed, n_max = int(pc.get("seed", 4242)), int(pc.get("n_max", 600))
    primary_models = list(cfg["models"]["primary"])
    m_tests = len(PRIMARY_COMPARISONS) * len(primary_models)
    alpha = float(cfg["analysis"]["alpha"])
    alpha_eff = alpha / m_tests
    sp = cfg["splits"]
    split_file = PATHS.data / "splits.json"
    n_main = len(read_json(split_file)["main"]) if split_file.exists() else None
    kinds, pool_rule = primary_pool(df, cfg)
    rows, detail = [], []
    for m in primary_models:
        for x, y in PRIMARY_COMPARISONS:
            sx, sy = family_scores(df, x, m, kinds), family_scores(df, y, m, kinds)
            counts, pairs = pilot_estimates(sx, sy)
            if sum(counts.values()) == 0:
                continue
            for name, sc in scenarios(counts).items():
                r = S.pilot_power(sc["p01"], sc["p10"], sc["p_both"], pairs=pairs, alpha=alpha_eff, target=target,
                                  seeds=len(cfg["seeds"]), sims=sims, n_perm=n_perm, seed=seed, n_max=n_max)
                req = r["required_n"]
                at_main = (S.simulate_power(r["probs"], n_main, pairs=pairs, alpha=alpha_eff, sims=sims,
                                            n_perm=n_perm, seed=seed) if n_main else None)
                row = {"model": m, "x": x, "y": y, "scenario": name, "pilot_families": sum(counts.values()),
                       **{f"pilot_{k}": v for k, v in counts.items()},
                       "p10": round(sc["p10"], 4), "p01": round(sc["p01"], 4), "p_both": round(sc["p_both"], 4),
                       "required_main_families": req,
                       "required_total_eligible": (math.ceil(req / (1 - float(sp["heldout_frac"]))) + int(sp["pilot_n"]))
                       if req else None,
                       "main_families_available": n_main,
                       "power_at_available": at_main["power_signflip"] if at_main else None,
                       "mcnemar_power_at_available": at_main["power_mcnemar"] if at_main else None}
                rows.append(row)
                detail.append({**row, "sim": r})
                log(f"power {m} {x} vs {y} [{name}]: required main families = {req}, "
                    f"power at {n_main} = {row['power_at_available']}")
    note = {"unit": "task family; score = mean over seeds of 'any instance solved'; majority-solved binary for "
                    "McNemar",
            "test": "one-sided paired sign-flip permutation (primary), exact McNemar (supporting)",
            "alpha": alpha, "alpha_per_test": alpha_eff, "primary_tests": m_tests, "target_power": target,
            "seeds": list(cfg["seeds"]), "sims": sims, "permutations": n_perm, "simulation_seed": seed,
            "bug_pool": pool_rule, "pilot_dir": pilot_dir.name, "rows": rows}
    NOTE_PATH.write_text(json.dumps(note, indent=1, sort_keys=True), encoding="utf-8")
    out = ensure_dir(PATHS.results)
    import pandas as pd
    (out / "power_note.md").write_text(
        "# Pre-freeze power note (SR-STAT-4)\n\n"
        f"Primary test simulated at alpha/{m_tests} = {alpha_eff:.4f} per test (Bonferroni bound of Holm), "
        f"target power {target:.0%}, {sims} simulated studies, {n_perm} sign-flips each, seed {seed}. "
        f"Seeds per family: {len(cfg['seeds'])}. Bug pool: {pool_rule}.\n\n"
        "`required_main_families` = confirmatory (`main`) families needed; `required_total_eligible` adds the "
        "held-out share and the pilot. Empty = not reachable within the simulated range.\n\n"
        + _md_table(pd.DataFrame(rows)), encoding="utf-8")
    return note


def has_power_note() -> bool:
    return NOTE_PATH.exists()
