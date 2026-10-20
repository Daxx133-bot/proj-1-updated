"""
weight_sensitivity.py -- POST HOC. NOT PREREGISTERED. Run on 2026-10-20, after the
confirmatory results were known. No test enters any preregistered family, and no weight
triplet is selected, recommended or adopted: the reported metric keeps FIXED_WEIGHTS
(0.4, 0.4, 0.2) (centrality/metric_constants.py).

Question: how much does the hybrid metric's association with the measured outcomes depend
on its weights? For every triplet (w_in, w_out, w_btw) on a 0.05 grid with
w_in + w_out + w_btw = 1 (231 triplets), hybrid_criticality is recomputed with the code that
produced the reported metric -- the centrality components from
tools/build_predictor_table.build() on the canonical graphs, the formula from
centrality.hybrid_weight_optimizer.compute_hybrid() -- and correlated at the service level
(gateways excluded, the preregistered analysis set) with:

  ancestor_affected_count  service median; both architectures; kill and latency faults
                           (analysis/final/service_level_data.csv). The outcome of H1b.
  delta_error_rate         service median under kill faults; both architectures. This is
                           the gateway's end-to-end error rate (see user_facing_impact.py).
                           EXPLORATORY. Error rate is the preregistered indicator for kill
                           faults only (preregistration v3 section 6.5), so latency faults
                           are not included for this outcome.

Statistic: Spearman's rho. p-value: two-sided permutation test, as in the preregistered
plan. Where the outcome vector has at most ARRANGEMENT_LIMIT distinct arrangements (all
ancestor_affected_count cells, and Hotel Reservation delta_error_rate), the null
distribution is enumerated exactly over those arrangements, which gives the same null as
enumerating all n! permutations (see exact_p_supplement.py). Social Network
delta_error_rate has no ties (11! orderings), so its p-values use fast_stats.permutation_p
with 10,000 random permutations from a fixed seed, the preregistered fallback.

Correction: Benjamini-Hochberg within each family of 231 (one family per architecture x
fault type x outcome). A triplet for which the metric is constant on the analysis set has
an undefined rho and is left out of its family.

Reads : data/graphs/{sn,hr}_CANONICAL.json, analysis/final/service_level_data.csv,
        analysis/final/predictors.csv (to check the reported triplet reproduces)
Writes: analysis/final/weight_sensitivity.csv          one row per triplet x cell
        analysis/final/weight_sensitivity_summary.csv  one row per cell
"""
from __future__ import annotations

import math
import os
import sys
from collections import Counter

import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)

from analysis.final.exact_p_supplement import bh  # noqa: E402
from analysis.final.fast_stats import permutation_p  # noqa: E402
from centrality.hybrid_weight_optimizer import compute_hybrid  # noqa: E402
from centrality.metric_constants import FIXED_WEIGHTS, HybridWeights  # noqa: E402
from tools.build_predictor_table import GRAPHS, build  # noqa: E402

LABEL = "POST HOC -- run after the confirmatory results were known; not preregistered"
STEP = 0.05
ARRANGEMENT_LIMIT = 3_000_000
N_PERM = 10_000
SEED = 20261020
FDR_Q = 0.05
ARCH_LABEL = {"socialnetwork": "Social Network", "hotelreservation": "Hotel Reservation"}
CELLS = [  # (architecture, fault type, outcome, status)
    ("socialnetwork", "kill", "ancestor_affected_count", "H1b outcome"),
    ("socialnetwork", "latency", "ancestor_affected_count", "H1b outcome"),
    ("hotelreservation", "kill", "ancestor_affected_count", "H1b outcome"),
    ("hotelreservation", "latency", "ancestor_affected_count", "H1b outcome"),
    ("socialnetwork", "kill", "delta_error_rate", "exploratory"),
    ("hotelreservation", "kill", "delta_error_rate", "exploratory"),
]


def triplets():
    k = int(round(1 / STEP))
    for i in range(k + 1):
        for j in range(k + 1 - i):
            yield HybridWeights(round(i * STEP, 2), round(j * STEP, 2),
                                round((k - i - j) * STEP, 2))


def unique_permutations(values):
    """Every distinct ordering of a multiset, as an array (one ordering per row)."""
    counts = Counter(values)
    keys = sorted(counts)
    n = len(values)
    out, cur = [], []

    def rec():
        if len(cur) == n:
            out.append(list(cur))
            return
        for k in keys:
            if counts[k]:
                counts[k] -= 1
                cur.append(k)
                rec()
                cur.pop()
                counts[k] += 1
    rec()
    return np.asarray(out, dtype=float)


def n_arrangements(values):
    total = math.factorial(len(values))
    for c in Counter(values).values():
        total //= math.factorial(c)
    return total


class Null:
    """The permutation null for one outcome vector, enumerated once when feasible."""

    def __init__(self, y):
        self.y = np.asarray(y, dtype=float)
        ry = stats.rankdata(self.y)
        self.ryc = ry - ry.mean()
        self.n_dis = n_arrangements(list(ry))
        self.arr = (unique_permutations(list(self.ryc)) if self.n_dis <= ARRANGEMENT_LIMIT
                    else None)

    def test(self, x, rng):
        x = np.asarray(x, dtype=float)
        rx = stats.rankdata(x)
        rxc = rx - rx.mean()
        den = math.sqrt(float((rxc * rxc).sum()) * float((self.ryc * self.ryc).sum()))
        if den == 0.0:
            return float("nan"), float("nan"), "undefined (metric constant)", 0
        obs = float((rxc * self.ryc).sum() / den)
        if self.arr is not None:
            rhos = self.arr @ rxc / den
            hits = int((np.abs(rhos) >= abs(obs) - 1e-12).sum())
            return obs, hits / self.n_dis, "exact (%d arrangements)" % self.n_dis, self.n_dis
        p, method, n = permutation_p(x, self.y, N_PERM, rng)
        return obs, p, method, n


def main():
    svc = pd.read_csv(os.path.join(HERE, "service_level_data.csv"))
    comps = {app: build(app, path) for app, path in GRAPHS.items()}

    # The reported triplet must reproduce the stored metric exactly.
    pred = pd.read_csv(os.path.join(HERE, "predictors.csv"))
    for app, df in comps.items():
        got = compute_hybrid(df, FIXED_WEIGHTS).set_index("service")["hybrid_criticality"]
        ref = pred[pred.architecture == app].set_index("service")["hybrid_criticality"]
        assert np.allclose(got.loc[ref.index].to_numpy(), ref.to_numpy(), atol=1e-9), app

    rng = np.random.default_rng(SEED)
    grid = list(triplets())
    assert len(grid) == 231
    rows = []
    for app, fault, outcome, status in CELLS:
        d = svc[(svc.app == app) & (svc.fault_type == fault) & svc.in_analysis_set] \
            .sort_values("service")
        services = d.service.tolist()
        null = Null(d[outcome].to_numpy(dtype=float))
        cell = []
        for w in grid:
            h = compute_hybrid(comps[app], w).set_index("service")["hybrid_criticality"]
            rho, p, method, n = null.test(h.loc[services].to_numpy(dtype=float), rng)
            cell.append({
                "label": LABEL, "architecture": app, "architecture_label": ARCH_LABEL[app],
                "fault_type": fault, "outcome": outcome, "outcome_status": status,
                "w_in": w.w_in, "w_out": w.w_out, "w_btw": w.w_btw,
                "is_reported_triplet": w == FIXED_WEIGHTS,
                "n_services": len(services), "spearman_rho": rho, "p_permutation": p,
                "p_method": method, "null_size": n,
            })
        adj, m = bh([c["p_permutation"] for c in cell])
        for c, a in zip(cell, adj):
            c["p_bh_within_231"] = a
            c["bh_family_size"] = m
            c["significant_bh_q05"] = bool(a <= FDR_Q) if a == a else False
        rows += cell
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(HERE, "weight_sensitivity.csv"), index=False)

    summ = []
    for (app, fault, outcome), g in df.groupby(["architecture", "fault_type", "outcome"],
                                                sort=False):
        ok = g[g.spearman_rho.notna()]
        rep = g[g.is_reported_triplet].iloc[0]
        summ.append({
            "label": LABEL, "architecture": app, "architecture_label": ARCH_LABEL[app],
            "fault_type": fault, "outcome": outcome,
            "outcome_status": g.outcome_status.iloc[0],
            "triplets": len(g), "triplets_defined": len(ok),
            "triplets_undefined": int(g.spearman_rho.isna().sum()),
            "rho_min": ok.spearman_rho.min(), "rho_median": ok.spearman_rho.median(),
            "rho_max": ok.spearman_rho.max(),
            "triplets_rho_positive": int((ok.spearman_rho > 0).sum()),
            "triplets_rho_negative": int((ok.spearman_rho < 0).sum()),
            "triplets_rho_zero": int((ok.spearman_rho == 0).sum()),
            "triplets_p_raw_below_05": int((ok.p_permutation < 0.05).sum()),
            "triplets_significant_bh": int(ok.significant_bh_q05.sum()),
            "p_raw_min": ok.p_permutation.min(),
            "p_bh_min": ok.p_bh_within_231.min(),
            "reported_rho": rep.spearman_rho, "reported_p": rep.p_permutation,
            "reported_p_bh_within_231": rep.p_bh_within_231,
            "triplets_rho_above_reported": int((ok.spearman_rho > rep.spearman_rho + 1e-12)
                                               .sum()),
            "p_method": "; ".join(sorted(set(g.p_method.str.replace(r"\d+ arr", "n arr",
                                                                    regex=True)))),
        })
    pd.DataFrame(summ).to_csv(os.path.join(HERE, "weight_sensitivity_summary.csv"),
                              index=False)
    print(pd.DataFrame(summ).drop(columns=["label"]).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
