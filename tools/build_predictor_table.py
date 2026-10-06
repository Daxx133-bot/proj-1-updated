"""
build_predictor_table.py -- structural predictors per service, for the preregistration.

Pure graph computation from data/graphs/*_CANONICAL.json. Touches no outcome data, so it
can be run at any time without leakage. Writes data/analysis/predictor_table.csv.

PRIMARY predictor (locked 2026-09-25):  ancestor_count
COMPARATORS: hybrid_criticality (fan-out corrected, FIXED_WEIGHTS), degree, in_degree,
             out_degree, betweenness, closeness, eigenvector, pagerank, composite_score,
             descendant_count, dominator_subtree_size.

Gateway services (in-degree 0) are computed and printed but marked
in_analysis_set=False: a gateway has no ancestors by construction, so it cannot vary on
the primary predictor, and killing it takes the whole application down. They appear in
the paper as labelled qualitative examples only.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import networkx as nx
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from centrality.compute_centrality import (  # noqa: E402
    add_composite_score,
    add_ranks,
    compute_all_centralities,
)
from centrality.hybrid_weight_optimizer import (  # noqa: E402
    ancestor_count,
    compute_hybrid,
    descendant_count,
    dominator_subtree_size,
)
from centrality.metric_constants import FIXED_WEIGHTS  # noqa: E402
from measurement.blast_radius import is_gateway  # noqa: E402

GRAPHS = {"socialnetwork": ROOT / "data" / "graphs" / "sn_CANONICAL.json",
          "hotelreservation": ROOT / "data" / "graphs" / "hr_CANONICAL.json"}

# Every predictor the confirmatory analysis will correlate against an outcome.
PREDICTORS = [
    "ancestor_count",           # PRIMARY
    "hybrid_criticality",       # the paper's original metric -- now hypothesised
                                # ANTI-predictive; see _audit/CAUSAL_DIRECTION.md
    "degree", "in_degree", "out_degree", "betweenness", "closeness",
    "eigenvector", "pagerank", "composite_score",
    "descendant_count", "dominator_subtree_size",
]

# Higher value = predicted MORE impactful, for every predictor except composite_score,
# which is a mean of normalised ranks where LOWER = more central.
LOWER_IS_MORE_CENTRAL = {"composite_score"}


def build(app: str, path: Path) -> pd.DataFrame:
    G = nx.node_link_graph(json.loads(path.read_text(encoding="utf-8")), edges="edges")
    df = compute_all_centralities(G)
    df = add_composite_score(add_ranks(df))
    df = compute_hybrid(df, FIXED_WEIGHTS)
    anc, desc, dom = ancestor_count(G), descendant_count(G), dominator_subtree_size(G)
    df["ancestor_count"] = df["service"].map(anc)
    df["descendant_count"] = df["service"].map(desc)
    df["dominator_subtree_size"] = df["service"].map(dom)
    df["in_degree_raw"] = df["service"].map(dict(G.in_degree()))
    df["out_degree_raw"] = df["service"].map(dict(G.out_degree()))
    df["is_gateway"] = df["service"].map(lambda s: is_gateway(G, s))
    df["in_analysis_set"] = ~df["is_gateway"]
    df.insert(0, "architecture", app)
    return df


def rank_within(df: pd.DataFrame, col: str) -> pd.Series:
    """Rank 1 = predicted MOST impactful by that predictor. Ties share the min rank."""
    asc = col in LOWER_IS_MORE_CENTRAL
    return df[col].rank(ascending=asc, method="min").astype(int)


def main() -> int:
    frames = [build(app, p) for app, p in GRAPHS.items()]
    full = pd.concat(frames, ignore_index=True)

    out = ROOT / "data" / "analysis" / "predictor_table.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    cols = (["architecture", "service", "in_degree_raw", "out_degree_raw",
             "is_gateway", "in_analysis_set"] + PREDICTORS)
    full[cols].to_csv(out, index=False)

    for app, p in GRAPHS.items():
        df = full[full["architecture"] == app].copy()
        keep = df[df["in_analysis_set"]].copy().reset_index(drop=True)

        print("=" * 118)
        print(f"{app.upper()}   ({len(df)} services, {len(keep)} in the analysis set "
              f"after gateway exclusion)")
        print("=" * 118)
        hdr = (f"{'service':<24}{'gw':>4}{'in':>4}{'out':>4}" +
               "".join(f"{c[:9]:>10}" for c in PREDICTORS))
        print(hdr)
        print("-" * len(hdr))
        for _, r in df.sort_values("ancestor_count", ascending=False).iterrows():
            vals = "".join(
                (f"{r[c]:>10.4f}" if isinstance(r[c], float) else f"{r[c]:>10}")
                for c in PREDICTORS)
            print(f"{r['service']:<24}{('GW' if r['is_gateway'] else ''):>4}"
                  f"{r['in_degree_raw']:>4}{r['out_degree_raw']:>4}{vals}")

        # ---- rank comparison, analysis set only ----
        print()
        print(f"  RANKS WITHIN THE ANALYSIS SET (1 = predicted most impactful, n={len(keep)})")
        rk = pd.DataFrame({"service": keep["service"]})
        for c in PREDICTORS:
            rk[c] = rank_within(keep, c)
        hdr2 = f"{'service':<24}" + "".join(f"{c[:9]:>10}" for c in PREDICTORS)
        print("  " + hdr2)
        print("  " + "-" * (len(hdr2)))
        for _, r in rk.sort_values("ancestor_count").iterrows():
            print(f"  {r['service']:<24}" +
                  "".join(f"{r[c]:>10}" for c in PREDICTORS))

        anc = sorted(keep["ancestor_count"])
        # ---- predictor health, analysis set only ----
        print()
        print("  PREDICTOR HEALTH (analysis set). A predictor with 1 distinct level")
        print("  cannot be correlated with anything -- Spearman is undefined, and that")
        print("  is a degeneracy of the graph, NOT a null result.")
        print(f"  {'predictor':<24}{'levels':>8}{'min':>10}{'max':>10}"
              f"{'rho vs ancestor_count':>24}")
        print("  " + "-" * 76)
        for c in PREDICTORS:
            v = keep[c].to_numpy(dtype=float)
            lv = len(set(v.round(9)))
            if c == "ancestor_count":
                note = "(primary)"
            elif lv < 2:
                note = "DEGENERATE - undefined"
            else:
                sign = -1.0 if c in LOWER_IS_MORE_CENTRAL else 1.0
                rho = spearmanr(keep["ancestor_count"], sign * v).statistic
                note = f"{rho:+.3f}"
            print(f"  {c:<24}{lv:>8}{v.min():>10.4f}{v.max():>10.4f}{note:>24}")

        print(f"\n  ancestor_count levels = {sorted(set(anc))}, values = {anc}")
        print(f"  distinct levels = {len(set(anc))}/{len(anc)}  "
              f"(ties limit the attainable Spearman rho)")

        # ---- the headline disagreement ----
        focus = [s for s in ("compose-post-service", "media-service") if s in set(rk["service"])]
        if focus:
            print("\n  PRIMARY vs HYBRID on the services the paper singled out:")
            print(f"  {'service':<24}{'anc_rank':>10}{'|anc|':>7}"
                  f"{'hyb_rank':>10}{'hybrid':>10}{'out_deg':>9}{'|desc|':>8}")
            for s in focus:
                i = rk.index[rk["service"] == s][0]
                k = keep.index[keep["service"] == s][0]
                print(f"  {s:<24}{rk.at[i, 'ancestor_count']:>10}"
                      f"{keep.at[k, 'ancestor_count']:>7}"
                      f"{rk.at[i, 'hybrid_criticality']:>10}"
                      f"{keep.at[k, 'hybrid_criticality']:>10.4f}"
                      f"{keep.at[k, 'out_degree_raw']:>9}"
                      f"{keep.at[k, 'descendant_count']:>8}")
        print()

    print(f"[WROTE] {out.relative_to(ROOT)}  ({len(full)} services)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
