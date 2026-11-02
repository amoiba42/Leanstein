"""Generate all result tables and figures from logs (FR-ANA-*, NFR-REP-1). Pure function of inputs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from prl.analysis import stats as S
from prl.analysis.features import BINARY_FEATURES, features
from prl.analysis.mechanism import classify
from prl.config import PATHS, ensure_dir
from prl.driver.runner import read_jsonl
from prl.tasks import verina as V

PRIMARY_COMPARISONS = [("C", "B"), ("C", "BP")]
SECONDARY_COMPARISONS = [("C", "Cplain"), ("C", "A"), ("BP", "B"), ("S", "Splain")]


def _md_table(df: pd.DataFrame, floatfmt: str = "{:.3f}") -> str:
    if df.empty:
        return "_(no data)_\n"
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, float):
                cells.append("" if np.isnan(v) else floatfmt.format(v))
            else:
                cells.append(str(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


def load_runs(study_dirs: list[Path]) -> pd.DataFrame:
    rows = []
    for d in study_dirs:
        rows += read_jsonl(d / "runs.jsonl")
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["success"] = df["success"].astype(bool)
    return df


def family_scores(df: pd.DataFrame, cond: str, model: str, kinds: tuple[str, ...]) -> pd.Series:
    """Family score = mean over seeds of (any instance of the family solved)."""
    sub = df[(df.condition == cond) & (df.model == model) & (df.kind.isin(kinds))]
    if sub.empty:
        return pd.Series(dtype=float)
    per_seed = sub.groupby(["family_id", "seed"])["success"].max()
    return per_seed.groupby("family_id").mean()


def compare(df: pd.DataFrame, x: str, y: str, model: str, kinds: tuple[str, ...], cfg: dict) -> dict[str, Any] | None:
    sx, sy = family_scores(df, x, model, kinds), family_scores(df, y, model, kinds)
    fams = sorted(set(sx.index) & set(sy.index))
    if not fams:
        return None
    a = cfg["analysis"]
    r = S.paired_compare(sx[fams].values, sy[fams].values, B=int(a["bootstrap"]), n_perm=int(a["permutations"]),
                         seed=int(a["seed"]), alpha=float(a["alpha"]))
    return {"model": model, "x": x, "y": y, **r.__dict__}


def outcome_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    t = df.groupby(["model", "condition", "outcome"]).size().unstack(fill_value=0)
    t["n_runs"] = t.sum(axis=1)
    return t.reset_index()


def mechanism_table(df: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    rd = float(cfg["analysis"]["revert_distance"])
    s = df[df.success & df.condition.isin(["C", "Cplain", "BP", "B", "A"])].copy()
    if s.empty:
        return pd.DataFrame(), pd.DataFrame()
    s["mech"] = [classify(success=True, ref_auto=bool(r.ref_auto), equiv_to_ref=bool(r.equiv_to_ref),
                          dist_to_ref=r.dist_to_ref, revert_distance=rd) for r in s.itertuples()]
    share = s.groupby(["model", "condition", "mech"]).size().unstack(fill_value=0).reset_index()
    rates = []
    for (m, c), g in df[df.kind.isin(["mutant", "natural"])].groupby(["model", "condition"]):
        for ra, gg in g.groupby("ref_auto"):
            rates.append({"model": m, "condition": c, "ref_auto": bool(ra), "n_runs": len(gg),
                          "success_rate": gg.success.mean(),
                          "median_dist_to_ref": gg.dist_to_ref.dropna().median() if gg.success.any() else np.nan})
    return share, pd.DataFrame(rates)


def cost_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    g = df.groupby(["model", "condition"])
    t = pd.DataFrame({
        "runs": g.size(), "success_rate": g.success.mean(), "mean_attempts": g.n_attempts.mean(),
        "mean_tokens": g.total_tokens.mean(), "mean_infer_s": g.infer_s_total.mean(), "mean_lean_s": g.lean_s_total.mean(),
    })
    succ = df[df.success].groupby(["model", "condition"])
    t["tokens_per_success"] = df.groupby(["model", "condition"]).total_tokens.sum() / succ.size()
    return t.reset_index()


def sensitivity_n(df: pd.DataFrame, ns=(2, 4, 8)) -> pd.DataFrame:
    rows = []
    for (m, c), g in df.groupby(["model", "condition"]):
        for n in ns:
            ok = g.success & (g.success_attempt_idx.fillna(1e9) < n)
            rows.append({"model": m, "condition": c, "N": n, "success_rate": ok.mean()})
    return pd.DataFrame(rows)


def closing_entries(df: pd.DataFrame) -> pd.DataFrame:
    s = df[df.success & (df.proof_source == "portfolio")]
    if s.empty:
        return pd.DataFrame()
    s = s.assign(entry=s.closing_entry.str.split("@").str[0])
    return s.groupby(["condition", "entry"]).size().rename("n").reset_index().sort_values(["condition", "n"], ascending=[True, False])


def shapes_from_T(fams: list) -> pd.DataFrame:
    rows = []
    for f in fams:
        if not f.eligible:
            continue
        ft = features(f.fn, f.region("code_aux"), f.region("code"), f.signature.params)
        rows.append({"family_id": f.family_id, "closed": int(bool(f.ref["T"]["closed"])), **ft})
    return pd.DataFrame(rows)


def shapes_table(df_feat: pd.DataFrame, seed: int = 99, B: int = 2000) -> pd.DataFrame:
    if df_feat.empty:
        return df_feat
    rows = []
    rng = np.random.default_rng(seed)
    for k in BINARY_FEATURES:
        if k not in df_feat or df_feat[k].nunique() < 2:
            continue
        on, off = df_feat[df_feat[k] > 0].closed, df_feat[df_feat[k] == 0].closed
        diffs = []
        y = df_feat.closed.values
        f = (df_feat[k] > 0).values
        for _ in range(B):
            idx = rng.integers(0, len(y), len(y))
            yy, ff = y[idx], f[idx]
            if ff.any() and (~ff).any():
                diffs.append(yy[ff].mean() - yy[~ff].mean())
        lo, hi = (np.quantile(diffs, [0.025, 0.975]) if diffs else (np.nan, np.nan))
        rows.append({"feature": k, "n_with": int(f.sum()), "p_closed_with": on.mean(), "p_closed_without": off.mean(),
                     "diff": on.mean() - off.mean(), "ci_lo": lo, "ci_hi": hi})
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("diff", ascending=False)


def shapes_from_runs(df: pd.DataFrame) -> pd.DataFrame:
    """Every final candidate of code-only runs that passed tests, labelled by portfolio success."""
    rows = []
    for r in df[df.condition.isin(["C", "Cplain", "S", "Splain"])].itertuples():
        if not isinstance(r.final_code, str) or not r.final_code.strip():
            continue
        if not (r.success or r.outcome == "correct_unverified"):
            continue
        fam = V.get_family(r.family_id)
        ft = features(fam.fn, r.final_code_aux or "", r.final_code, fam.signature.params)
        rows.append({"family_id": r.family_id, "closed": int(bool(r.success)), **ft})
    return pd.DataFrame(rows)


def _plot_rates(df: pd.DataFrame, out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    t = df[df.kind.isin(["mutant", "natural"])].groupby(["model", "condition"]).success.mean().unstack()
    if t.empty:
        return
    order = [c for c in ["A", "B", "BP", "C", "Cplain"] if c in t.columns]
    ax = t[order].plot(kind="bar", figsize=(8, 4), rot=0)
    ax.set_ylabel("verified-repair rate (runs)")
    ax.set_title("Verified repair rate by condition and model")
    plt.tight_layout()
    plt.savefig(out, dpi=120, metadata={"Software": None})
    plt.close()


def analyze(study_dirs: list[Path], cfg: dict, out_dir: Path | None = None) -> dict[str, Any]:
    out = ensure_dir(out_dir or PATHS.results)
    ensure_dir(out / "figures")
    fams = V.all_saved()
    summary: dict[str, Any] = {}

    # ---- T coverage (does not need runs; skipped before `prl tasks check` has produced families)
    elig = [f for f in fams if f.eligible]
    if fams:
        tdf = pd.DataFrame([{
            "family_id": f.family_id, "tier": f.tier, "eligible": f.eligible, "exclusion": f.exclusion_reason,
            "T_closed": bool(f.ref.get("T", {}).get("closed")), "T_entry": f.ref.get("T", {}).get("entry"),
            "ref_proof": f.ref.get("proof"), "hidden_pass": f.ref.get("hidden_pass"),
        } for f in fams])
        tdf["eligible"] = tdf["eligible"].fillna(False).astype(bool)  # unchecked families count as not eligible
        tdf["T_closed"] = tdf["T_closed"].fillna(False).astype(bool)
        tdf.to_csv(out / "t_coverage.csv", index=False)
        cov = tdf[tdf.eligible].groupby("tier").T_closed.agg(["sum", "count", "mean"]).reset_index()
        cov.loc[len(cov)] = ["all", int(tdf[tdf.eligible].T_closed.sum()), int(tdf.eligible.sum()),
                             float(tdf[tdf.eligible].T_closed.mean()) if len(elig) else 0.0]
        ent = tdf[tdf.T_closed].T_entry.fillna("").str.split("@").str[0].value_counts().rename_axis("entry").reset_index(name="n")
        ref_proof = tdf[tdf.eligible].groupby(["ref_proof", "T_closed"]).size().rename("n").reset_index()
        (out / "t_coverage.md").write_text(
            "# Condition T: portfolio coverage on reference implementations\n\n"
            f"Screened {len(tdf)} VERINA tasks; eligible {int(tdf.eligible.sum())}; excluded "
            f"{int((~tdf.eligible).sum())} ({tdf[~tdf.eligible].exclusion.value_counts().to_dict()}).\n\n"
            "## Coverage by tier\n\n" + _md_table(cov) + "\n## Closing entry\n\n" + _md_table(ent)
            + "\n## Coverage vs. availability of a human reference proof\n\n" + _md_table(ref_proof),
            encoding="utf-8")
        summary["T_coverage"] = float(tdf[tdf.eligible].T_closed.mean()) if len(elig) else 0.0

    # ---- shapes on references (RQ4, part 1)
    sh = shapes_table(shapes_from_T(fams))
    sh.to_csv(out / "rq4_shapes_reference.csv", index=False)

    df = load_runs(study_dirs)
    if df.empty:
        (out / "rq4_shapes.md").write_text("# RQ4 code shapes (reference implementations)\n\n" + _md_table(sh), encoding="utf-8")
        return summary
    df.to_csv(out / "runs_flat.csv", index=False)
    outcome_table(df).to_csv(out / "outcomes.csv", index=False)

    # ---- RQ1 + secondary comparisons
    models = sorted(df.model.unique())
    primary_kinds, pool_note = primary_pool(df, cfg)
    summary["primary_pool"] = {"kinds": list(primary_kinds), "rule": pool_note}
    rows = []
    for m in models:
        pools = [(primary_kinds, "primary_pool"), (("mutant",), "mutant"), (("natural",), "natural")]
        if primary_kinds != ("mutant", "natural"):
            pools.append((("mutant", "natural"), "all_bugs"))
        for kinds, label in pools:
            for (x, y) in PRIMARY_COMPARISONS + SECONDARY_COMPARISONS:
                k = ("shaping",) if (x, y) == ("S", "Splain") else kinds
                if (x, y) == ("S", "Splain") and label != "primary_pool":
                    continue
                r = compare(df, x, y, m, k, cfg)
                if r:
                    r["bugs"] = "shaping" if k == ("shaping",) else label
                    r["primary"] = (x, y) in PRIMARY_COMPARISONS and label == "primary_pool" and m in cfg["models"]["primary"]
                    rows.append(r)
    comp = pd.DataFrame(rows)
    if not comp.empty:
        prim = comp[comp.primary]
        comp["p_holm"] = np.nan
        if len(prim):
            comp.loc[prim.index, "p_holm"] = S.holm(prim.p_signflip.tolist())
        comp.to_csv(out / "comparisons.csv", index=False)
        cols = ["model", "bugs", "x", "y", "n_families", "rate_x", "rate_y", "diff", "ci_lo", "ci_hi", "p_signflip",
                "p_holm", "cohens_h", "only_x", "only_y", "both", "neither", "mcnemar_p_greater", "min_detectable"]
        (out / "rq1_main.md").write_text(
            "# RQ1 (confirmatory) and secondary paired comparisons\n\n"
            "Family-level scores = mean over seeds of 'any instance solved'. One-sided sign-flip permutation test "
            "(x > y); Holm correction over the primary tests only; 95% family-cluster bootstrap CI.\n\n"
            f"Primary bug pool: {pool_note}\n\n"
            "## Primary\n\n" + _md_table(comp[comp.primary][cols]) + "\n## Secondary / exploratory\n\n"
            + _md_table(comp[~comp.primary][[c for c in cols if c != "p_holm"]]), encoding="utf-8")
        summary["primary"] = comp[comp.primary][["model", "x", "y", "rate_x", "rate_y", "diff", "p_holm"]].to_dict("records")

    # ---- RQ2 mechanism
    share, rates = mechanism_table(df, cfg)
    s_rows = df[df.kind == "shaping"].groupby(["model", "condition"]).success.agg(["sum", "count", "mean"]).reset_index()
    (out / "rq2_mechanism.md").write_text(
        "# RQ2 mechanism: shaping vs reverting\n\n"
        "*revert* = repair identical to the reference, or within the pre-registered distance of an "
        "automation-provable reference; *shaping* = the reference itself is NOT provable by the portfolio, so the "
        "verified repair must have a different, automation-friendly shape; *other* = remaining successes.\n\n"
        "## Mechanism class of successful runs\n\n" + _md_table(share) + "\n## Success rate by reference provability\n\n"
        + _md_table(rates) + "\n## Study S: re-shaping correct but automation-resistant references\n\n" + _md_table(s_rows),
        encoding="utf-8")

    # ---- RQ4 shapes (runs)
    shr = shapes_table(shapes_from_runs(df))
    shr.to_csv(out / "rq4_shapes_runs.csv", index=False)
    (out / "rq4_shapes.md").write_text(
        "# RQ4 code shapes\n\n## Reference implementations (condition T)\n\n" + _md_table(sh)
        + "\n## Test-passing candidates from code-only conditions (C, C-plain, S, S-plain)\n\n" + _md_table(shr)
        + "\n## Closing portfolio entry of verified repairs\n\n" + _md_table(closing_entries(df)), encoding="utf-8")

    # ---- RQ5 costs, outcomes, sensitivity
    ct = cost_table(df)
    sens = sensitivity_n(df)
    ct.to_csv(out / "rq5_costs.csv", index=False)
    sens.to_csv(out / "sensitivity_n.csv", index=False)
    (out / "rq5_costs.md").write_text("# RQ5 costs and outcomes\n\n## Cost per condition\n\n" + _md_table(ct)
                                      + "\n## Outcome labels\n\n" + _md_table(outcome_table(df), "{:.0f}")
                                      + "\n## Sensitivity to the generation budget N (post-hoc truncation)\n\n"
                                      + _md_table(sens.pivot_table(index=["model", "condition"], columns="N",
                                                                   values="success_rate").reset_index()),
                                      encoding="utf-8")
    en = energy_table(study_dirs, df)
    if not en.empty:
        en.to_csv(out / "rq5_energy.csv", index=False)
        with open(out / "rq5_costs.md", "a", encoding="utf-8") as fh:
            fh.write("\n## Energy per (model, condition) block\n\nGPU energy is measured (NVML counter); Lean CPU "
                     "energy and CO2 are estimates (see prereg/study.yaml `energy`).\n\n" + _md_table(en))
    flags = df.explode("flags").dropna(subset=["flags"]).groupby(["condition", "flags"]).size().rename("n").reset_index()
    flags.to_csv(out / "integrity_flags.csv", index=False)
    _plot_rates(df, out / "figures" / "rates.png")
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    return summary


def primary_pool(df: pd.DataFrame, cfg: dict) -> tuple[tuple[str, ...], str]:
    """Pre-registered rule (study.yaml `bugs`): natural bugs if they cover enough confirmatory families."""
    b = cfg.get("bugs", {})
    need = int(b.get("min_natural_families", 60))
    conf = df[df.split.isin(["main", "heldout"])] if "split" in df else df
    n_nat = conf[conf.kind == "natural"].family_id.nunique()
    if b.get("primary", "natural") == "natural" and n_nat >= need:
        return ("natural",), f"natural bugs ({n_nat} families >= {need})"
    return ("mutant", "natural"), f"natural + mutant (natural covers {n_nat} < {need} families: pre-registered fallback)"


def energy_table(study_dirs: list[Path], df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for d in study_dirs:
        rows += read_jsonl(d / "energy.jsonl")
    if not rows:
        return pd.DataFrame()
    e = pd.DataFrame(rows).groupby(["model", "condition"])[["gpu_j", "cpu_j_est", "co2_g_est", "lean_cpu_s"]].sum()
    succ = df[df.success].groupby(["model", "condition"]).size()
    e["verified_repairs"] = succ.reindex(e.index).fillna(0).astype(int)
    e["J_per_repair"] = (e.gpu_j.fillna(0) + e.cpu_j_est) / e.verified_repairs.replace(0, np.nan)
    return e.reset_index()


def audit_sample(study_dirs: list[Path], frac: float, seed: int, out: Path) -> pd.DataFrame:
    """Stratified `frac` of successes plus EVERY success that carries a degeneracy flag (G11)."""
    df = load_runs(study_dirs)
    s = df[df.success]
    if s.empty:
        return s
    n = max(1, int(round(frac * len(s))))
    samp = s.groupby(["condition"], group_keys=False).apply(
        lambda g: g.sample(n=max(1, int(round(n * len(g) / len(s)))), random_state=seed))
    flagged = s[s.flags.apply(lambda f: bool(f) if isinstance(f, list) else False)]
    samp = pd.concat([samp, flagged]).drop_duplicates(subset=["run_id"])
    cols = ["run_id", "family_id", "instance_id", "condition", "model", "seed", "final_code_aux", "final_code",
            "closing_entry", "proof_source", "flags"]
    samp = samp[cols].assign(audit_spec_gaming="", audit_natural_code="", audit_notes="")
    ensure_dir(out.parent)
    samp.to_csv(out, index=False)
    return samp


def audit_merge(sample_csv: Path, out_md: Path) -> str:
    """Summarise the manually filled audit CSV (columns audit_spec_gaming / audit_natural_code: yes|no)."""
    if not sample_csv.exists():
        return f"no audit sample at {sample_csv}"
    d = pd.read_csv(sample_csv).fillna("")
    filled = d[d.audit_spec_gaming.astype(str).str.strip() != ""]
    gaming = filled.audit_spec_gaming.astype(str).str.lower().str.startswith("y")
    t = filled.assign(spec_gaming=gaming).groupby("condition").agg(
        audited=("run_id", "size"), spec_gaming=("spec_gaming", "sum")).reset_index()
    text = (f"# Audit summary\n\n{len(filled)}/{len(d)} sampled successes audited.\n\n" + _md_table(t)
            + "\nRuns judged spec-gaming are reported and excluded from verified repairs in the final report.\n")
    ensure_dir(out_md.parent)
    out_md.write_text(text, encoding="utf-8")
    return text
