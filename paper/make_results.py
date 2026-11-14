"""Turn `prl analyze` outputs into paper/results.tex (macros) and paper/results_tables.tex (tables).

Usage: python paper/make_results.py MAIN_DIR [HELDOUT_DIR] [PILOT_IREL_DIR]
  MAIN_DIR     output of `prl analyze --study main,main-shaping,main-gemma,main-goedel,main-bhammer`
  HELDOUT_DIR  output of `prl analyze --study heldout --out results/heldout`
  PILOT_IREL_DIR  output of the pilot replication analysis (exploratory)

The generated sentences only state numbers. Interpretation is written by hand in main.tex.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
COND_ORDER = ["A", "B", "BP", "Bhammer", "C", "Cplain", "S", "Splain"]
COND_TEX = {"Cplain": "C-plain", "Splain": "S-plain", "B_noauto": "B\\_noauto"}


def tex(s: object) -> str:
    return str(s).replace("_", "\\_").replace("%", "\\%")


def ct(c: str) -> str:
    return COND_TEX.get(c, c)


def pct(x: float) -> str:
    return "---" if pd.isna(x) else f"{100 * x:.1f}\\%"


def sg(v: float) -> str:
    """Signed one-decimal number without a negative zero."""
    t = f"{v:+.1f}"
    return "0.0" if t in ("+0.0", "-0.0") else t.replace("-", "$-$")


def pval(p: float) -> str:
    if pd.isna(p):
        return "---"
    return "$<0.001$" if p < 0.001 else f"{p:.3f}"


def read(d: Path | None, name: str) -> pd.DataFrame:
    if d is None or not (d / name).exists():
        return pd.DataFrame()
    return pd.read_csv(d / name)


def rate_table(costs: pd.DataFrame, caption: str, label: str) -> str:
    if costs.empty:
        return ""
    models = list(dict.fromkeys(costs.model))
    conds = [c for c in COND_ORDER if c in set(costs.condition)]
    head = " & ".join(ct(c) for c in conds)
    rows = []
    for m in models:
        sub = costs[costs.model == m].set_index("condition")
        cells = []
        for c in conds:
            if c in sub.index:
                r = sub.loc[c]
                cells.append(f"{pct(r.success_rate)}\\,\\scriptsize({int(r.runs)})")
            else:
                cells.append("")
        rows.append(f"{tex(m)} & " + " & ".join(cells) + " \\\\")
    return ("\\begin{table*}[t]\\centering\\small\n"
            f"\\caption{{{caption}}}\\label{{{label}}}\n"
            f"\\begin{{tabular}}{{@{{}}l{'r' * len(conds)}@{{}}}}\\toprule\n"
            f"Model & {head} \\\\\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\\end{tabular}\n\\end{table*}\n")


def comp_table(comp: pd.DataFrame, caption: str, label: str, primary: bool) -> str:
    if comp.empty:
        return ""
    c = comp[comp.primary] if primary else comp[(~comp.primary) & (comp.bugs.isin(["primary_pool", "shaping"]))]
    if c.empty:
        return ""
    rows = []
    for _, r in c.iterrows():
        p = r.p_holm if primary else r.p_signflip
        rows.append(f"{tex(r.model)} & {ct(r.x)} vs {ct(r.y)} & {int(r.n_families)} & {pct(r.rate_x)} & {pct(r.rate_y)} & "
                    f"{sg(100 * r['diff'])} [{sg(100 * r.ci_lo)}, {sg(100 * r.ci_hi)}] & {pval(p)} & {r.cohens_h:.2f} & "
                    f"{int(r.only_x)}/{int(r.only_y)} \\\\")
    pcol = "$p_\\text{Holm}$" if primary else "$p$"
    return ("\\begin{table*}[t]\\centering\\small\n"
            f"\\caption{{{caption}}}\\label{{{label}}}\n"
            "\\begin{tabular}{@{}llrrrlrrr@{}}\\toprule\n"
            f"Model & Comparison & Fam. & $x$ & $y$ & Diff. (pp) [95\\% CI] & {pcol} & $h$ & only $x$/$y$ \\\\\\midrule\n"
            + "\n".join(rows) + "\n\\bottomrule\\end{tabular}\n\\end{table*}\n")


def robustness_table(comp: pd.DataFrame, shp: pd.DataFrame, caption: str, label: str) -> str:
    """C vs B and C vs BP by bug source (natural / mutant) and on families whose reference the portfolio cannot
    prove (results/exploratory_shaping.csv, from scripts/exploratory_shaping.py)."""
    if comp.empty:
        return ""
    models = ["qwen3.5-2b", "qwen3.5-4b", "gemma-4-e4b-it"]
    parts = []
    for bugs, name in (("natural", "Natural bugs only"), ("mutant", "Mutants only")):
        parts.append((name, comp[(comp.bugs == bugs) & (comp.x == "C") & (comp.y.isin(["B", "BP"]))
                                 & (comp.model.isin(models))]))
    if not shp.empty:
        parts.append(("Ref.\\ not provable", shp[shp.subset == "reference not provable"]))
    rows = []
    for name, c in parts:
        c = c.assign(_m=c.model.map(models.index)).sort_values(["_m", "y"])
        for i, (_, r) in enumerate(c.iterrows()):
            lead = f"\\multirow{{{len(c)}}}{{*}}{{{name}}}" if i == 0 else ""
            rows.append(f"{lead} & {tex(r.model)} & {ct(r.x)} vs {ct(r.y)} & {int(r.n_families)} & {pct(r.rate_x)} & "
                        f"{pct(r.rate_y)} & {sg(100 * r['diff'])} [{sg(100 * r.ci_lo)}, {sg(100 * r.ci_hi)}] & "
                        f"{pval(r.p_signflip)} & {int(r.only_x)}/{int(r.only_y)} \\\\")
        rows.append("\\midrule")
    rows = rows[:-1]
    return ("\\begin{table*}[t]\\centering\\small\n"
            f"\\caption{{{caption}}}\\label{{{label}}}\n"
            "\\begin{tabular}{@{}lllrrrlrr@{}}\\toprule\n"
            "Subset & Model & Comparison & Fam. & $x$ & $y$ & Diff. (pp) [95\\% CI] & $p$ & only $x$/$y$ \\\\\\midrule\n"
            + "\n".join(rows) + "\n\\bottomrule\\end{tabular}\n\\end{table*}\n")


def energy_table(en: pd.DataFrame, caption: str, label: str) -> str:
    """Estimated energy per verified repair (deviation D-4), main split."""
    if en.empty:
        return ""
    e = en[en.split == "main"].copy()
    e["ci"] = e.condition.map({c: i for i, c in enumerate(COND_ORDER)})
    e = e.sort_values(["model", "ci"])
    rows = []
    for _, r in e.iterrows():
        per = "---" if pd.isna(r.kj_per_repair) else (f"{r.kj_per_repair:.1f} "
                                                      f"\\scriptsize[{r.kj_per_repair_lo:.1f}, {r.kj_per_repair_hi:.1f}]")
        co2 = "---" if pd.isna(r.co2_g_per_repair) else f"{r.co2_g_per_repair:.2f}"
        rows.append(f"{tex(r.model)} & {ct(r.condition)} & {int(r.repairs)} & {r.gpu_kj_mean:.0f} & {r.cpu_kj:.0f} & "
                    f"{per} & {co2} \\\\")
    return ("\\begin{table*}[t]\\centering\\small\n"
            f"\\caption{{{caption}}}\\label{{{label}}}\n"
            "\\begin{tabular}{@{}llrrrrr@{}}\\toprule\n"
            "Model & Cond. & Repairs & GPU kJ & CPU kJ & kJ per repair [range] & g CO$_2$ per repair \\\\\\midrule\n"
            + "\n".join(rows) + "\n\\bottomrule\\end{tabular}\n\\end{table*}\n")


def outcome_table(out: pd.DataFrame, caption: str, label: str) -> str:
    if out.empty:
        return ""
    labs = [c for c in ["verified_repair", "correct_unverified", "verified_wrong", "integrity_violation", "unresolved"]
            if c in out.columns]
    rows = []
    for _, r in out.iterrows():
        rows.append(f"{tex(r.model)} & {ct(r.condition)} & " + " & ".join(str(int(r[c])) for c in labs) + f" & {int(r.n_runs)} \\\\")
    head = " & ".join(tex(c).replace("\\_", " ") for c in labs)
    return ("\\begin{table*}[t]\\centering\\small\n"
            f"\\caption{{{caption}}}\\label{{{label}}}\n"
            f"\\begin{{tabular}}{{@{{}}ll{'r' * (len(labs) + 1)}@{{}}}}\\toprule\n"
            f"Model & Cond. & {head} & runs \\\\\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\\end{tabular}\n\\end{table*}\n")


# Validated categorical slots (dataviz reference palette, light mode): blue, orange, aqua. Text stays in ink colours.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def _style(ax) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelcolor=INK, labelsize=8)
    ax.yaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def family_scores(runs: pd.DataFrame) -> pd.DataFrame:
    """Family score = mean over seeds of 'any instance of the family solved' (the pre-registered unit)."""
    any_solved = runs.groupby(["model", "condition", "family_id", "seed"]).success.max().reset_index()
    return any_solved.groupby(["model", "condition", "family_id"]).success.mean().reset_index(name="score")


def make_figures(main_dir: Path | None) -> list[str]:
    """fig_rates.pdf (family-level rate with 95% family bootstrap CI) and fig_costs.pdf (tokens per repair)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    made = []
    if main_dir is None or not (main_dir / "runs_flat.csv").exists():
        return made
    runs = pd.read_csv(main_dir / "runs_flat.csv")
    runs = runs[runs.kind.isin(["mutant", "natural"]) & runs.model.isin(["qwen3.5-2b", "qwen3.5-4b"])]
    runs["success"] = runs.success.astype(str).str.lower().eq("true")
    fs = family_scores(runs)
    conds = [c for c in ["A", "B", "BP", "Bhammer", "C", "Cplain"] if c in set(fs.condition)]
    models = sorted(fs.model.unique())
    rng = np.random.default_rng(99)
    fig, ax = plt.subplots(figsize=(7.0, 2.4))
    w = 0.38
    for j, m in enumerate(models):
        means, lo, hi = [], [], []
        for c in conds:
            v = fs[(fs.model == m) & (fs.condition == c)].score.to_numpy()
            boots = rng.choice(v, size=(2000, len(v)), replace=True).mean(axis=1) if len(v) else np.array([0.0])
            means.append(v.mean() if len(v) else 0.0)
            lo.append(np.percentile(boots, 2.5))
            hi.append(np.percentile(boots, 97.5))
        x = np.arange(len(conds)) + (j - 0.5) * (w + 0.02)
        means = np.array(means)
        ax.bar(x, 100 * means, width=w, color=SERIES[j], label=m, edgecolor="white", linewidth=1.5)
        ax.errorbar(x, 100 * means, yerr=[100 * (means - np.array(lo)), 100 * (np.array(hi) - means)],
                    fmt="none", ecolor=INK, elinewidth=0.8, capsize=2)
    ax.set_xticks(np.arange(len(conds)), [COND_TEX.get(c, c).replace("\\_", "_") for c in conds])
    ax.set_ylabel("families repaired (%)", color=INK, fontsize=8)
    _style(ax)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(HERE / "fig_rates.pdf")
    plt.close(fig)
    made.append("fig_rates.pdf")

    costs = read(main_dir, "rq5_costs.csv")
    if not costs.empty and "tokens_per_success" in costs:
        costs = costs[costs.model.isin(models)]
        fig, ax = plt.subplots(figsize=(3.4, 2.3))
        cc = [c for c in conds if c in set(costs.condition)]
        for j, m in enumerate(models):
            sub = costs[costs.model == m].set_index("condition")
            y = [sub.tokens_per_success.get(c, np.nan) / 1000 for c in cc]
            ax.plot(range(len(cc)), y, marker="o", markersize=5, linewidth=0, color=SERIES[j], label=m)
        ax.set_xticks(range(len(cc)), [COND_TEX.get(c, c).replace("\\_", "_") for c in cc])
        ax.set_yscale("log")
        ax.set_ylabel("k tokens per verified repair (log)", color=INK, fontsize=8)
        _style(ax)
        ax.legend(frameon=False, fontsize=7)
        fig.tight_layout()
        fig.savefig(HERE / "fig_costs.pdf")
        plt.close(fig)
        made.append("fig_costs.pdf")
    return made


def main() -> None:
    main_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    held_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    pilot_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    comp, costs, outc = read(main_dir, "comparisons.csv"), read(main_dir, "rq5_costs.csv"), read(main_dir, "outcomes.csv")
    hcomp, hcosts = read(held_dir, "comparisons.csv"), read(held_dir, "rq5_costs.csv")
    pcosts = read(pilot_dir, "rq5_costs.csv")

    tables = [
        comp_table(comp, "RQ1, confirmatory: paired family-level comparisons on the \\texttt{main} split, primary bug "
                   "pool (natural $\\cup$ mutant). One-sided sign-flip test, Holm over the four primary tests; "
                   "95\\% family-cluster bootstrap CI; Cohen's $h$; families solved only by $x$ / only by $y$.",
                   "tab:rq1", True),
        rate_table(costs, "Verified-repair rate per run on the \\texttt{main} split (runs in brackets).", "tab:rates"),
        comp_table(comp, "Secondary and exploratory comparisons on \\texttt{main} (uncorrected one-sided $p$). Never "
                   "pooled with the primary estimates.", "tab:secondary", False),
        robustness_table(comp, read(main_dir, "exploratory_shaping.csv"),
                         "Exploratory robustness checks on \\texttt{main} (not pre-registered; uncorrected one-sided "
                         "sign-flip $p$). Natural bugs cover only 33 families. \\emph{Ref.\\ not provable}: families "
                         "whose reference implementation the portfolio cannot prove, so that a verified repair cannot "
                         "be a plain revert to the reference.", "tab:robust"),
        outcome_table(outc, "Outcome labels per run on \\texttt{main}.", "tab:outcomes"),
        energy_table(read(main_dir, "rq5_energy_estimate.csv"),
                     "RQ5 energy on \\texttt{main} (estimate, deviation D-4). GPU: tokens used $\\times$ joules per "
                     "token calibrated on our slice for each model (marginal board power over idle; range over three "
                     "calibration cycles). CPU: Lean seconds $\\times$ 5.47\\,W per thread. CO$_2$ at 0.716\\,kg/kWh.",
                     "tab:energy"),
        comp_table(hcomp, "Held-out replication (analysed once and separately; not confirmatory).", "tab:heldout", True),
        rate_table(pcosts, "Pilot (calibration split: 20 families, 41 buggy instances, seed 11; per-run rate, runs "
                   "in brackets). Never pooled with the study.", "tab:pilotirel"),
    ]
    (HERE / "results_tables.tex").write_text("% Generated by make_results.py. Do not edit by hand.\n" + "\n".join(t for t in tables if t),
                                             encoding="utf-8")

    def sentence_primary(c: pd.DataFrame, where: str) -> str:
        if c.empty or not c.primary.any():
            return "\\tbd{" + where + "}"
        parts = []
        for _, r in c[c.primary].iterrows():
            parts.append(f"for {tex(r.model)}, {ct(r.x)} {pct(r.rate_x)} vs {ct(r.y)} {pct(r.rate_y)} "
                         f"({100 * r['diff']:+.1f}\\,pp, 95\\% CI [{100 * r.ci_lo:+.1f}, {100 * r.ci_hi:+.1f}], "
                         f"$p_\\text{{Holm}}$ = {pval(r.p_holm)})")
        return "Family-level verified-repair rates: " + "; ".join(parts) + "."

    macros = {
        "resRQOneText": sentence_primary(comp, "RQ1") + " Full results in \\cref{tab:rq1,tab:rates,tab:outcomes}.",
        "resHeldoutText": sentence_primary(hcomp, "held-out") + (" See \\cref{tab:heldout}." if not hcomp.empty else ""),
    }
    old = (HERE / "results.tex").read_text(encoding="utf-8") if (HERE / "results.tex").exists() else ""
    # never overwrite a text that has been written by hand: only fill macros that are missing or still TBD
    for k in list(macros):
        pre = f"\\newcommand{{\\{k}}}{{"
        if pre in old and not old.split(pre, 1)[1].lstrip().startswith("\\tbd"):
            del macros[k]
    lines = []
    for ln in old.splitlines():
        name = ln.split("{\\", 1)[1].split("}", 1)[0] if ln.startswith("\\newcommand{\\") else None
        if name in macros:
            continue
        lines.append(ln)
    lines += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in macros.items()]
    (HERE / "results.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote results.tex and results_tables.tex; figures:", make_figures(main_dir))


if __name__ == "__main__":
    main()
