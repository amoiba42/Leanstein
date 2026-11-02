"""Paired statistics at the task-family level (SR-STAT-1..4)."""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass

import numpy as np
from scipy import stats as st


def signflip_test(x: np.ndarray, y: np.ndarray, *, n_perm: int = 100_000, seed: int = 99,
                  alternative: str = "greater") -> tuple[float, float]:
    """Paired sign-flip permutation test on per-family scores. Returns (mean diff, p-value).

    Exact enumeration when the number of non-zero differences is ≤ 16, otherwise Monte Carlo
    with the (+1)/(n+1) correction.
    """
    d = np.asarray(x, float) - np.asarray(y, float)
    obs = float(d.mean()) if len(d) else 0.0
    nz = d[d != 0]
    if len(nz) == 0:
        return obs, 1.0
    n = len(d)
    if len(nz) <= 16:
        signs = np.array(list(itertools.product([1, -1], repeat=len(nz))), float)
        stats_ = (signs * nz).sum(axis=1) / n
        total = len(stats_)
        if alternative == "greater":
            cnt = (stats_ >= obs - 1e-12).sum()
        elif alternative == "less":
            cnt = (stats_ <= obs + 1e-12).sum()
        else:
            cnt = (np.abs(stats_) >= abs(obs) - 1e-12).sum()
        return obs, float(cnt / total)
    rng = np.random.default_rng(seed)
    signs = rng.choice([-1.0, 1.0], size=(n_perm, len(nz)))
    stats_ = (signs * nz).sum(axis=1) / n
    if alternative == "greater":
        cnt = (stats_ >= obs - 1e-12).sum()
    elif alternative == "less":
        cnt = (stats_ <= obs + 1e-12).sum()
    else:
        cnt = (np.abs(stats_) >= abs(obs) - 1e-12).sum()
    return obs, float((cnt + 1) / (n_perm + 1))


def holm(pvals: list[float]) -> list[float]:
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [0.0] * m
    run = 0.0
    for rank, i in enumerate(order):
        v = min(1.0, (m - rank) * pvals[i])
        run = max(run, v)
        adj[i] = run
    return adj


def mcnemar_exact(b: int, c: int) -> dict[str, float]:
    """b = only-x solved, c = only-y solved. Exact binomial on discordant pairs."""
    n = b + c
    if n == 0:
        return {"b": b, "c": c, "p_two_sided": 1.0, "p_greater": 1.0}
    return {
        "b": b, "c": c,
        "p_two_sided": float(st.binomtest(b, n, 0.5, alternative="two-sided").pvalue),
        "p_greater": float(st.binomtest(b, n, 0.5, alternative="greater").pvalue),
    }


def cluster_bootstrap_diff(x: np.ndarray, y: np.ndarray, *, B: int = 10_000, seed: int = 99,
                           level: float = 0.95) -> tuple[float, float, float]:
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    d = x - y
    n = len(d)
    if n == 0:
        return 0.0, 0.0, 0.0
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(B, n))
    means = d[idx].mean(axis=1)
    lo, hi = np.quantile(means, [(1 - level) / 2, 1 - (1 - level) / 2])
    return float(d.mean()), float(lo), float(hi)


def bootstrap_mean(x: np.ndarray, *, B: int = 10_000, seed: int = 99) -> tuple[float, float, float]:
    x = np.asarray(x, float)
    if len(x) == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    m = x[rng.integers(0, len(x), size=(B, len(x)))].mean(axis=1)
    lo, hi = np.quantile(m, [0.025, 0.975])
    return float(x.mean()), float(lo), float(hi)


def cohens_h(p1: float, p2: float) -> float:
    return 2 * math.asin(math.sqrt(max(0.0, min(1.0, p1)))) - 2 * math.asin(math.sqrt(max(0.0, min(1.0, p2))))


def min_detectable(D: int, alpha: float = 0.05) -> int | None:
    """Smallest b (of D discordant) with one-sided binomial p ≤ alpha; None if impossible."""
    for b in range(D + 1):
        if D and st.binomtest(b, D, 0.5, alternative="greater").pvalue <= alpha:
            return b
    return None


@dataclass
class PairedResult:
    n_families: int
    rate_x: float
    rate_y: float
    diff: float
    ci_lo: float
    ci_hi: float
    p_signflip: float
    cohens_h: float
    only_x: int
    only_y: int
    both: int
    neither: int
    mcnemar_p_greater: float
    min_detectable: int | None


def paired_compare(x: np.ndarray, y: np.ndarray, *, B: int, n_perm: int, seed: int, alpha: float) -> PairedResult:
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    diff, lo, hi = cluster_bootstrap_diff(x, y, B=B, seed=seed)
    _, p = signflip_test(x, y, n_perm=n_perm, seed=seed)
    xb, yb = x > 0.5, y > 0.5  # "solved in the majority of seeds"
    b = int((xb & ~yb).sum())
    c = int((~xb & yb).sum())
    return PairedResult(
        n_families=len(x), rate_x=float(x.mean()) if len(x) else 0.0, rate_y=float(y.mean()) if len(y) else 0.0,
        diff=diff, ci_lo=lo, ci_hi=hi, p_signflip=p,
        cohens_h=cohens_h(float(x.mean()) if len(x) else 0, float(y.mean()) if len(y) else 0),
        only_x=b, only_y=c, both=int((xb & yb).sum()), neither=int((~xb & ~yb).sum()),
        mcnemar_p_greater=mcnemar_exact(b, c)["p_greater"], min_detectable=min_detectable(b + c, alpha),
    )
