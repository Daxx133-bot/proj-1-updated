"""
leave_one_out.py -- POST-HOC ROBUSTNESS CHECK. NOT PART OF THE PREREGISTERED
CONFIRMATORY FAMILY.

Recomputes the Social Network ancestor_count vs ancestor_affected_count Spearman
correlation 11 times, each time dropping one of the 11 services from the analysis set,
for both fault types. Its purpose is to show how much of the reported rho depends on any
single service.

This analysis was specified AFTER the confirmatory results were known. It is therefore
exploratory in the strictest sense: it is not FDR-corrected, it carries no inferential
weight, and it does not change the preregistered verdict (0 of 44 confirmatory and 0 of
44 replication tests survive BH-FDR at q = 0.05) in either direction. The p-values below
are nominal, uncorrected, and reported for description only.

Inputs : data/campaign/runs/*.json (ancestor_affected_count per run)
          data/graphs/sn_CANONICAL.json (ancestor_count)
Output : analysis/final/leave_one_out.csv
"""
from __future__ import annotations

import glob
import itertools
import json
import math
import os
from collections import defaultdict

import numpy as np
import pandas as pd
from scipy import stats

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNS = os.path.join(REPO, "data", "campaign", "runs")
GRAPH = os.path.join(REPO, "data", "graphs", "sn_CANONICAL.json")
OUT = os.path.join(REPO, "analysis", "final", "leave_one_out.csv")

EXACT_LIMIT = 5_000_000      # n = 10 -> 3,628,800 permutations, enumerated exactly
MC_RESAMPLES = 2_000_000     # n = 11 -> 39,916,800, too many; Monte-Carlo instead
MC_SEED = 20260928


def ancestor_counts() -> dict[str, int]:
    g = json.load(open(GRAPH, encoding="utf-8"))
    callers = defaultdict(set)
    for e in g["edges"]:
        callers[e["target"]].add(e["source"])

    def anc(n):
        seen, stack = set(), [n]
        while stack:
            for c in callers.get(stack.pop(), ()):
                if c not in seen:
                    seen.add(c)
                    stack.append(c)
        return seen

    return {n["id"]: len(anc(n["id"])) for n in g["nodes"]}


def spearman(x, y):
    rx, ry = stats.rankdata(x), stats.rankdata(y)
    rxc, ryc = rx - rx.mean(), ry - ry.mean()
    den = math.sqrt(float((rxc * rxc).sum()) * float((ryc * ryc).sum()))
    if den == 0.0:
        return float("nan"), rxc, ryc, den
    return float((rxc * ryc).sum() / den), rxc, ryc, den


def perm_p(x, y):
    """Two-sided permutation p for Spearman's rho: exact when feasible, else Monte-Carlo."""
    obs, rxc, ryc, den = spearman(x, y)
    if math.isnan(obs):
        return float("nan"), "undefined (an input is constant)"
    n = len(x)
    n_fact = math.factorial(n)
    if n_fact <= EXACT_LIMIT:
        hits = 0
        it = itertools.permutations(range(n))
        while True:
            chunk = list(itertools.islice(it, 200_000))
            if not chunk:
                break
            P = np.asarray(chunk, dtype=np.int64)
            hits += int((np.abs(ryc[P] @ rxc / den) >= abs(obs) - 1e-12).sum())
        return hits / n_fact, f"exact enumeration of {n_fact:,} permutations"
    rng = np.random.default_rng(MC_SEED)
    hits, done = 0, 0
    while done < MC_RESAMPLES:
        blk = min(200_000, MC_RESAMPLES - done)
        B = rng.permuted(np.tile(ryc, (blk, 1)), axis=1)
        hits += int((np.abs(B @ rxc / den) >= abs(obs) - 1e-12).sum())
        done += blk
    return (hits + 1) / (MC_RESAMPLES + 1), f"{MC_RESAMPLES:,} random permutations (seed {MC_SEED})"


def main() -> None:
    ac = ancestor_counts()
    obs = defaultdict(lambda: defaultdict(list))
    for f in sorted(glob.glob(os.path.join(RUNS, "*.json"))):
        r = json.load(open(f, encoding="utf-8"))
        if r["app"] != "socialnetwork":
            continue
        obs[r["fault_type"]][r["service"]].append(r["ancestor_affected_count"])

    rows = []
    for fault in sorted(obs):
        services = sorted(obs[fault])
        med = {s: float(np.median(obs[fault][s])) for s in services}
        for excluded in [None] + services:
            keep = [s for s in services if s != excluded]
            x = np.array([ac[s] for s in keep], dtype=float)
            y = np.array([med[s] for s in keep], dtype=float)
            rho, _, _, _ = spearman(x, y)
            p, method = perm_p(x, y)
            rows.append({
                "analysis": "post-hoc robustness check, not part of the preregistered "
                            "confirmatory family",
                "architecture": "socialnetwork",
                "fault_type": fault,
                "service_excluded": "NONE (full set, reference)" if excluded is None else excluded,
                "n_services": len(keep),
                "excluded_ancestor_count": "" if excluded is None else ac[excluded],
                "excluded_median_ancestor_affected_count": "" if excluded is None else med[excluded],
                "rho": round(rho, 6),
                "p_permutation_nominal_uncorrected": round(p, 6),
                "p_method": method,
                "delta_rho_vs_full_set": "",
            })
            print(f"[{fault}] exclude {str(excluded):24s} n={len(keep):2d} "
                  f"rho={rho:+.6f} p={p:.6f}")

    df = pd.DataFrame(rows)
    for fault, g in df.groupby("fault_type"):
        full = g.loc[g.service_excluded.str.startswith("NONE"), "rho"].iloc[0]
        df.loc[g.index, "delta_rho_vs_full_set"] = (g["rho"] - full).round(6)
    df.loc[df.service_excluded.str.startswith("NONE"), "delta_rho_vs_full_set"] = ""
    df.to_csv(OUT, index=False)
    print(f"\nwrote {OUT}  ({len(df)} rows)")


if __name__ == "__main__":
    main()
