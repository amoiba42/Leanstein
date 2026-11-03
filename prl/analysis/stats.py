"""Paired statistics at the task-family level (SR-STAT-1..5) and the pre-freeze power simulation."""
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


# ---- pre-freeze power simulation (SR-STAT-4)

CATS = ("both", "only_x", "only_y", "neither")  # majority-solved category of a family (x = C, y = baseline)
_DEFAULT_PAIR = {"both": (1.0, 1.0), "only_x": (1.0, 0.0), "only_y": (0.0, 1.0), "neither": (0.0, 0.0)}


def _signflip_p_batch(d: np.ndarray, signs: np.ndarray) -> np.ndarray:
    """One-sided (greater) Monte-Carlo sign-flip p-values for many simulated studies at once.
    d: (sims, n) family-score differences; signs: (n_perm, n) shared ±1 matrix."""
    obs = d.mean(axis=1)
    null = d @ signs.T / d.shape[1]  # (sims, n_perm)
    return ((null >= obs[:, None] - 1e-12).sum(axis=1) + 1) / (signs.shape[0] + 1)


def simulate_power(probs: dict[str, float], n: int, *, pairs: dict[str, list[tuple[float, float]]] | None = None,
                   alpha: float = 0.05, sims: int = 500, n_perm: int = 999, seed: int = 4242) -> dict[str, float]:
    """Rejection rates of the primary sign-flip test and the supporting exact McNemar test for `n` families.

    Each simulated family draws its majority category from `probs` (p_both, p10 = only_x, p01 = only_y,
    p_neither) and then a (score_x, score_y) pair over the three seeds from the pilot pairs of that category
    (or the pure 0/1 pair if the pilot has none). This keeps the task-clustered unit of the real test:
    one paired observation per family, never per seed."""
    from statsmodels.stats.contingency_tables import mcnemar

    rng = np.random.default_rng(seed)
    p = np.array([max(0.0, probs[c]) for c in CATS], float)
    p = p / p.sum()
    pools = [np.array(pairs.get(c) or [_DEFAULT_PAIR[c]], float) if pairs else np.array([_DEFAULT_PAIR[c]])
             for c in CATS]
    cat = rng.choice(len(CATS), size=(sims, n), p=p)
    x = np.empty((sims, n))
    y = np.empty((sims, n))
    for k, pool in enumerate(pools):
        m = cat == k
        pick = pool[rng.integers(0, len(pool), size=int(m.sum()))]
        x[m], y[m] = pick[:, 0], pick[:, 1]
    signs = rng.choice([-1.0, 1.0], size=(n_perm, n))
    p_sf = _signflip_p_batch(x - y, signs)
    xb, yb = x > 0.5, y > 0.5
    b = (xb & ~yb).sum(axis=1)
    c = (~xb & yb).sum(axis=1)
    rej_mc = 0
    for bi, ci in zip(b, c, strict=True):
        if bi > ci:  # one-sided: only x-favouring discordance can reject
            t = mcnemar([[0, int(bi)], [int(ci), 0]], exact=True)
            rej_mc += (t.pvalue / 2) <= alpha
    return {"n": n, "power_signflip": float((p_sf <= alpha).mean()), "power_mcnemar": float(rej_mc / sims)}


def pilot_power(p01: float, p10: float, p_both: float, *, pairs: dict[str, list[tuple[float, float]]] | None = None,
                alpha: float = 0.05, target: float = 0.80, seeds: int = 3, sims: int = 500, n_perm: int = 999,
                seed: int = 4242, n_min: int = 10, n_max: int = 600) -> dict[str, object]:
    """Smallest number of confirmatory families whose sign-flip rejection rate reaches `target`.

    p01 = P(baseline solved, C failed), p10 = P(C solved, baseline failed), p_both; p_neither is the rest.
    Family outcomes are majority-solved over `seeds` seeds. Bisection over n (power is monotone up to
    simulation noise); returns None for `required_n` if even `n_max` families do not reach the target."""
    probs = {"both": p_both, "only_x": p10, "only_y": p01, "neither": max(0.0, 1.0 - p01 - p10 - p_both)}

    def pw(n: int) -> dict[str, float]:
        return simulate_power(probs, n, pairs=pairs, alpha=alpha, sims=sims, n_perm=n_perm, seed=seed)

    top = pw(n_max)
    if p10 <= p01 or top["power_signflip"] < target:
        return {"required_n": None, "at_n_max": top, "probs": probs, "seeds": seeds}
    lo, hi = n_min, n_max
    if pw(lo)["power_signflip"] >= target:
        hi = lo
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if pw(mid)["power_signflip"] >= target:
            hi = mid
        else:
            lo = mid
    return {"required_n": hi, "at_required": pw(hi), "probs": probs, "seeds": seeds}
