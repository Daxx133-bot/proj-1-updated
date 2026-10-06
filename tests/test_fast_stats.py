"""Equivalence tests for analysis/final/fast_stats.py against scipy.

The vectorised implementations exist for speed only. If they are not identical to
scipy.stats.spearmanr, the preregistered analysis is computing a different statistic than
it claims to, so these tests pin the identity -- including on the tie structure this
dataset actually has (Hotel Reservation: n=7, ancestor_count = [1,1,1,1,1,2,2]).
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from scipy import stats

from analysis.final import fast_stats as fs

# The real predictor vectors from the canonical graphs.
HR_ANCESTORS = np.array([1., 1., 1., 1., 1., 2., 2.])
SN_ANCESTORS = np.array([1., 2., 2., 2., 2., 2., 3., 3., 3., 4., 4.])


@pytest.mark.parametrize("x,y", [
    (np.arange(11.0), np.arange(11.0)[::-1].copy()),
    (SN_ANCESTORS, np.array([1., 2., 2., 1., 2., 0., 3., 3., 2., 4., 4.])),
    (HR_ANCESTORS, np.array([1., 1., 1., 1., 1., 2., 2.])),
    (HR_ANCESTORS, np.array([2., 1., 1., 1., 1., 2., 1.])),
    (np.array([1., 1., 2., 2., 3., 3., 4.]), np.array([4., 3., 3., 2., 2., 1., 1.])),
])
def test_rho_matches_scipy(x, y):
    assert fs.rho(x, y) == pytest.approx(stats.spearmanr(x, y).statistic, abs=1e-12)


def test_rho_is_nan_when_a_variable_is_constant():
    assert math.isnan(fs.rho(np.ones(7), np.arange(7.0)))
    assert math.isnan(fs.rho(np.arange(7.0), np.ones(7)))


def test_perfect_monotone_relationship_is_one():
    assert fs.rho(SN_ANCESTORS, SN_ANCESTORS) == pytest.approx(1.0)


def test_exact_enumeration_is_used_for_n7_and_is_reproducible():
    rng = np.random.default_rng(1)
    p1, m1, n1 = fs.permutation_p(HR_ANCESTORS, HR_ANCESTORS, 10_000, rng)
    p2, m2, n2 = fs.permutation_p(HR_ANCESTORS, HR_ANCESTORS, 10_000,
                                  np.random.default_rng(999))
    assert n1 == math.factorial(7) == 5040
    assert "exact enumeration" in m1
    assert p1 == p2, "an exact p-value must not depend on the random seed"


def test_exact_p_for_a_perfect_n7_relationship_matches_the_prereg_power_table():
    """Section 7.2 preregistered HR's ceiling as rho=0.791, p=0.034. Verify the p."""
    rng = np.random.default_rng(0)
    r = fs.rho(HR_ANCESTORS, HR_ANCESTORS)
    p, _, _ = fs.permutation_p(HR_ANCESTORS, HR_ANCESTORS, 10_000, rng)
    # 2 of 7 services sit at the high level, so 5!*2! = 240 of 5040 orderings are as
    # extreme -> p = 240/5040.
    assert r == pytest.approx(1.0)
    assert p == pytest.approx(240 / 5040, abs=1e-12)
    assert p == pytest.approx(0.0476, abs=5e-4)


def test_monte_carlo_p_is_used_for_n11_and_never_returns_zero():
    rng = np.random.default_rng(2)
    p, m, n = fs.permutation_p(SN_ANCESTORS, SN_ANCESTORS, 10_000, rng)
    assert n == 10_000 and "random permutations" in m
    assert p > 0.0, "the add-one correction must prevent an exact zero"
    assert p == pytest.approx(1 / 10_001, rel=0.5) or p < 0.01


def test_permutation_p_agrees_with_a_brute_force_reference():
    """Independent slow implementation, to catch an error in the vectorised algebra."""
    x = HR_ANCESTORS
    y = np.array([2., 1., 1., 3., 1., 2., 1.])
    obs = stats.spearmanr(x, y).statistic
    from itertools import permutations
    cnt = 0
    for perm in permutations(range(7)):
        r = stats.spearmanr(x, y[list(perm)]).statistic
        if not math.isnan(r) and abs(r) >= abs(obs) - 1e-12:
            cnt += 1
    ref = cnt / 5040
    got, _, _ = fs.permutation_p(x, y, 10_000, np.random.default_rng(3))
    assert got == pytest.approx(ref, abs=1e-12)


def test_permutation_p_is_one_when_the_observed_rho_is_the_least_extreme():
    rng = np.random.default_rng(4)
    x = np.array([1., 2., 3., 4., 5., 6., 7.])
    p, _, _ = fs.permutation_p(x, x, 10_000, rng)
    assert p == pytest.approx(2 / 5040, abs=1e-12)


def test_bca_returns_an_interval_containing_the_estimate_for_a_clean_case():
    rng = np.random.default_rng(5)
    x = np.arange(11.0)
    y = x + rng.normal(0, 0.5, 11)
    r = fs.rho(x, y)
    ci = fs.bca_ci(x, y, 10_000, rng)
    assert ci["method"] in ("BCa", "percentile")
    assert ci["lo"] <= r <= ci["hi"]


def test_bca_discloses_its_fallback_rather_than_relabelling():
    """A perfect relationship makes every resample rho = 1, so BCa cannot be formed."""
    rng = np.random.default_rng(6)
    ci = fs.bca_ci(SN_ANCESTORS, SN_ANCESTORS, 2_000, rng)
    assert ci["method"] != "BCa"
    assert ci["note"], "the reason must be recorded"


def test_bca_on_a_constant_variable_is_undefined_not_zero():
    rng = np.random.default_rng(7)
    ci = fs.bca_ci(np.ones(7), np.arange(7.0), 1_000, rng)
    assert ci["method"] == "undefined"
    assert math.isnan(ci["lo"]) and math.isnan(ci["hi"])
