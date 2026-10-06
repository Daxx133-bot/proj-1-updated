"""
fast_stats.py -- vectorised Spearman, permutation tests and BCa bootstrap.

These are performance replacements, not different statistics. Spearman's rho IS Pearson's r
on average ranks, which is exactly what `scipy.stats.spearmanr` computes and exactly what
`scipy.stats.rankdata` produces, so the identities below are algebraic rather than
approximations:

  * `rho` matches `scipy.stats.spearmanr(...).statistic` to floating-point tolerance.
  * In a PERMUTATION test only the numerator changes. Permuting y permutes its ranks, so
    mean(rank(y)) and ||rank(y) - mean|| are invariant; the whole test reduces to one
    matrix multiply against the fixed centred ranks of x.
  * In a BOOTSTRAP the resample changes the tie structure, so ranks must be recomputed --
    but `rankdata(..., axis=1)` does all resamples in one call.

`tests/test_fast_stats.py` asserts equivalence against scipy, including tie-heavy inputs of
the kind this dataset actually contains (n = 7 with a 5/2 split).

Why it matters here: the per-call overhead of `scipy.stats.spearmanr` is ~1.4 ms, and the
preregistered analysis needs ~2.5 million evaluations (10 000 permutations plus 10 000
bootstrap resamples, for each of ~240 tests). That is ~1 hour of pure interpreter overhead
for arithmetic that vectorises to seconds.
"""

from __future__ import annotations

import math
from itertools import permutations

import numpy as np
from scipy import stats

EXACT_PERM_LIMIT = 200_000


def rho(x: np.ndarray, y: np.ndarray) -> float:
    """Spearman's rho. NaN when either variable is constant (rho is then undefined)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size < 3:
        return float("nan")
    rx = stats.rankdata(x)
    ry = stats.rankdata(y)
    rx = rx - rx.mean()
    ry = ry - ry.mean()
    den = math.sqrt(float((rx * rx).sum()) * float((ry * ry).sum()))
    if den == 0.0:
        return float("nan")
    return float((rx * ry).sum() / den)


def _rowwise_rho_from_ranks(RX: np.ndarray, RY: np.ndarray) -> np.ndarray:
    RXc = RX - RX.mean(axis=1, keepdims=True)
    RYc = RY - RY.mean(axis=1, keepdims=True)
    num = (RXc * RYc).sum(axis=1)
    den = np.sqrt((RXc * RXc).sum(axis=1) * (RYc * RYc).sum(axis=1))
    out = np.full(num.shape, np.nan)
    ok = den > 0
    out[ok] = num[ok] / den[ok]
    return out


def permutation_p(x: np.ndarray, y: np.ndarray, n_perm: int,
                  rng: np.random.Generator) -> tuple[float, str, int]:
    """Two-sided permutation p-value for Spearman's rho.

    Exact enumeration when n! <= EXACT_PERM_LIMIT, otherwise `n_perm` random permutations
    with the add-one correction (a Monte-Carlo p-value of exactly zero is not credible).
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    obs = rho(x, y)
    if math.isnan(obs):
        return float("nan"), "undefined (a variable is constant)", 0

    n = x.size
    rx = stats.rankdata(x)
    ry = stats.rankdata(y)
    rxc = rx - rx.mean()
    ryc = ry - ry.mean()
    den = math.sqrt(float((rxc * rxc).sum()) * float((ryc * ryc).sum()))

    n_fact = math.factorial(n)
    if n_fact <= EXACT_PERM_LIMIT:
        P = np.array(list(permutations(range(n))), dtype=np.int64)
        rhos = (ryc[P] @ rxc) / den
        cnt = int((np.abs(rhos) >= abs(obs) - 1e-12).sum())
        return cnt / n_fact, f"exact enumeration of {n_fact} permutations", n_fact

    # Random permutations, done as one block.
    block = np.tile(ryc, (n_perm, 1))
    block = rng.permuted(block, axis=1)
    rhos = (block @ rxc) / den
    cnt = int((np.abs(rhos) >= abs(obs) - 1e-12).sum())
    return (cnt + 1) / (n_perm + 1), f"{n_perm} random permutations", n_perm


def bca_ci(x: np.ndarray, y: np.ndarray, n_boot: int, rng: np.random.Generator,
           alpha: float = 0.05) -> dict:
    """BCa bootstrap CI for Spearman's rho.

    Falls back to the percentile interval, and says so in `method`, whenever the BCa
    machinery is undefined -- which happens with this dataset's tie structure. The interval
    is never relabelled silently.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    theta = rho(x, y)
    if math.isnan(theta):
        return {"lo": float("nan"), "hi": float("nan"), "method": "undefined",
                "n_valid": 0, "note": "point estimate undefined"}

    n = x.size
    idx = rng.integers(0, n, size=(n_boot, n))
    RX = stats.rankdata(x[idx], axis=1)
    RY = stats.rankdata(y[idx], axis=1)
    boots = _rowwise_rho_from_ranks(RX, RY)
    valid = boots[~np.isnan(boots)]
    n_valid = int(valid.size)
    if n_valid < 100:
        return {"lo": float("nan"), "hi": float("nan"), "method": "failed",
                "n_valid": n_valid,
                "note": f"only {n_valid}/{n_boot} resamples yielded a defined rho"}

    lo_pct = float(np.percentile(valid, 100 * alpha / 2))
    hi_pct = float(np.percentile(valid, 100 * (1 - alpha / 2)))

    prop = float(np.mean(valid < theta))
    if prop <= 0.0 or prop >= 1.0:
        return {"lo": lo_pct, "hi": hi_pct, "method": "percentile", "n_valid": n_valid,
                "note": "BCa bias correction undefined (all resamples on one side of the "
                        "estimate); percentile interval reported instead"}
    z0 = float(stats.norm.ppf(prop))

    jk = np.array([rho(np.delete(x, i), np.delete(y, i)) for i in range(n)])
    jk = jk[~np.isnan(jk)]
    if jk.size < 3:
        return {"lo": lo_pct, "hi": hi_pct, "method": "percentile", "n_valid": n_valid,
                "note": "jackknife acceleration undefined; percentile interval reported"}
    jbar = float(jk.mean())
    num = float(((jbar - jk) ** 3).sum())
    den = float(6.0 * (((jbar - jk) ** 2).sum() ** 1.5))
    if den == 0.0:
        return {"lo": lo_pct, "hi": hi_pct, "method": "percentile", "n_valid": n_valid,
                "note": "jackknife variance zero; percentile interval reported"}
    a = num / den

    out = {}
    for tag, q in (("lo", alpha / 2), ("hi", 1 - alpha / 2)):
        z = float(stats.norm.ppf(q))
        adj = z0 + (z0 + z) / (1 - a * (z0 + z))
        out[tag] = float(np.percentile(valid, 100 * float(stats.norm.cdf(adj))))
    lo, hi = sorted((out["lo"], out["hi"]))
    return {"lo": lo, "hi": hi, "method": "BCa", "n_valid": n_valid,
            "note": f"z0={z0:.4f} a={a:.4f}"}
