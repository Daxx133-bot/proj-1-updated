"""
hybrid_weight_optimizer.py — leakage-free weight selection and structural baselines.

WHAT CHANGED AND WHY
--------------------
The previous version of this file grid-searched (w1, w2, w3) to maximise Spearman rho
against the outcome variable, then that same rho was reported in the manuscript as a
validation result. There was no held-out split. The reported figure was a maximum over
~66 candidate triplets presented as a single test, computed on a dataset that was 45%
fabricated. See _audit/AUDIT_REPORT.md section E.2.

This version removes that path entirely. There is no default behaviour: you must pass
--protocol explicitly, and each protocol is honest by construction.

  --protocol fixed
      Weights come from centrality/metric_constants.py::FIXED_WEIGHTS and are NEVER
      touched by outcome data. No search happens. The module refuses to run any search
      under this protocol.

  --protocol cross-arch
      The grid search runs on the TUNING architecture only (Social Network). The winning
      triplet is frozen and written to a lockfile. Evaluation on the HELD-OUT
      architecture (Hotel Reservation) is a separate command that reads the lockfile and
      refuses to run if the lockfile is absent, or if it has already been evaluated once.
      One architecture is tuned on; the other is spent exactly once.

Both protocols refuse to touch quarantined data.

This module also provides two structural baseline metrics that do not depend on any
outcome data, for comparison against the hybrid metric:

  descendant_count(v)        — size of the set reachable from v in the directed graph
  dominator_subtree_size(v)  — number of nodes v dominates, from the entry node

Usage:
    python centrality/hybrid_weight_optimizer.py --protocol fixed --graph sdg/output/sdg.json
    python centrality/hybrid_weight_optimizer.py --protocol cross-arch --stage tune \\
        --graph sdg/output/sdg.json --results data/raw/sn_controlled_sep18-20.csv
    python centrality/hybrid_weight_optimizer.py --protocol cross-arch --stage evaluate \\
        --graph sdg/output/hotel/sdg.json --results data/raw/hr_controlled_sep18-20.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
from typing import Optional

import networkx as nx
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from centrality.metric_constants import (  # noqa: E402
    FIXED_WEIGHTS,
    GRID_STEP,
    HELDOUT_ARCHITECTURE,
    TUNING_ARCHITECTURE,
    HybridWeights,
)

ROOT = Path(__file__).resolve().parent.parent
LOCKFILE = ROOT / "centrality" / "output" / "tuned_weights.lock.json"


# ── Guards ────────────────────────────────────────────────────────────────────

def refuse_quarantined(path: Path) -> None:
    """Hard stop if asked to read anything under _quarantine/."""
    if "_quarantine" in Path(path).resolve().parts:
        raise SystemExit(
            f"[REFUSED] {path} is quarantined. See _quarantine/QUARANTINE_LOG.md."
        )


# ── Structural metrics (no outcome data involved) ─────────────────────────────

def descendant_count(G: nx.DiGraph) -> dict[str, int]:
    """Number of nodes reachable from each node, excluding the node itself.

    The transitive blast radius a failure could reach by following call edges. Unlike
    out-degree this counts the whole downstream cone, so an orchestrator one hop above a
    deep subtree scores higher than one above a shallow one.

    Cycles are handled correctly: nx.descendants returns the reachable set, so a node in
    a cycle counts the other cycle members once each, not repeatedly.
    """
    return {n: len(nx.descendants(G, n)) for n in G.nodes()}


def ancestor_count(G: nx.DiGraph) -> dict[str, int]:
    """Number of nodes that can reach each node, excluding the node itself.

    PRIMARY PREDICTOR (locked 2026-09-25). If X calls Y and Y dies, X's request to Y
    fails or hangs, so X degrades -- and so does anything that calls X, transitively.
    The set that degrades is therefore Y's ANCESTOR set. Y's descendants merely stop
    receiving traffic and go idle, which is not an impact. See
    `_audit/CAUSAL_DIRECTION.md` and `measurement/blast_radius.py`.

    Implemented by reversing the graph and reusing `descendant_count`: the ancestors of
    v in G are exactly the descendants of v in G-reversed, so there is one traversal
    implementation to get right rather than two. `nx.DiGraph.reverse(copy=False)` returns
    a read-only reversed *view*, so this costs no copy of the graph.

    Cycles are handled by inheritance from descendant_count: the reachable set is a set,
    so each cycle member is counted once.
    """
    return descendant_count(G.reverse(copy=False))


def dominator_subtree_size(G: nx.DiGraph, entry: Optional[str] = None) -> dict[str, int]:
    """Number of nodes each node dominates, counted from the entry node.

    v dominates u when every path from `entry` to u passes through v. The dominated set
    is therefore the set of services that become *unreachable* if v fails -- a stricter
    and more operationally meaningful blast radius than descendant_count, which counts
    everything downstream regardless of whether an alternative route exists.

    Args:
        G: the service dependency graph.
        entry: the ingress node. Defaults to the unique node with in-degree 0
            (nginx-web-server / frontend). If several exist, the one with the highest
            out-degree is chosen and the choice is reported.

    Returns:
        node -> count of nodes it dominates, excluding itself. Nodes unreachable from
        `entry` get 0.
    """
    if entry is None:
        entry = _infer_entry(G)

    # nx.immediate_dominators gives idom for every node reachable from entry.
    idom = nx.immediate_dominators(G, entry)

    # Build the dominator tree, then each node's dominated count is its subtree size - 1.
    dom_tree = nx.DiGraph()
    dom_tree.add_nodes_from(idom.keys())
    for node, parent in idom.items():
        if node != parent:          # the entry node is its own immediate dominator
            dom_tree.add_edge(parent, node)

    # Iterate over the dominator tree, not over idom.keys(): networkx omits the entry
    # node from the idom mapping, so keying off idom silently leaves the entry at 0 --
    # exactly the node with the largest dominated set.
    sizes = {n: 0 for n in G.nodes()}
    for node in dom_tree.nodes():
        sizes[node] = len(nx.descendants(dom_tree, node))
    return sizes


def _infer_entry(G: nx.DiGraph) -> str:
    """Pick the ingress node: the sole source, else the source with the most out-edges."""
    sources = [n for n in G.nodes() if G.in_degree(n) == 0]
    if not sources:
        raise ValueError(
            "graph has no node with in-degree 0; pass entry= explicitly"
        )
    if len(sources) > 1:
        sources.sort(key=lambda n: -G.out_degree(n))
        print(f"  [INFO] multiple entry candidates {sources}; using '{sources[0]}'")
    return sources[0]


# ── Hybrid metric ─────────────────────────────────────────────────────────────

def compute_hybrid(
    centrality_df: pd.DataFrame,
    weights: HybridWeights,
) -> pd.DataFrame:
    """Apply the hybrid formula for a given weight triplet.

    Criticality(v) = w_in*C_in + w_out*C_out*fan_out_weight + w_btw*C_btw
    """
    weights.validate()
    df = centrality_df.copy()
    max_out = df["out_degree"].max()
    df["fan_out_weight"] = df["out_degree"] / max_out if max_out > 0 else 0.0
    df["hybrid_criticality"] = (
        weights.w_in * df["in_degree"]
        + weights.w_out * df["out_degree"] * df["fan_out_weight"]
        + weights.w_btw * df["betweenness"]
    ).round(6)
    return df


# ── Loading ───────────────────────────────────────────────────────────────────

def load_graph(path: Path) -> nx.DiGraph:
    refuse_quarantined(path)
    with open(path, "r", encoding="utf-8") as fh:
        return nx.node_link_graph(json.load(fh), edges="edges")


def load_outcomes(path: Path, outcome: str) -> pd.DataFrame:
    """Aggregate the outcome variable per service.

    Censored recovery observations are DROPPED here rather than imputed. Averaging a
    censored value as if it were a duration is exactly the defect this refactor exists to
    prevent. Dropping them biases toward fast recoveries, which is why the
    preregistration specifies survival analysis as the primary test -- this aggregation
    is for the weight search only.
    """
    refuse_quarantined(path)
    df = pd.read_csv(path)

    if outcome not in df.columns:
        raise SystemExit(f"[FAIL] outcome column '{outcome}' not in {path}")

    if "recovery_censored" in df.columns and outcome == "recovery_time_s":
        n_before = len(df)
        df = df[~df["recovery_censored"].astype(str).str.lower().isin(["true", "1"])]
        dropped = n_before - len(df)
        if dropped:
            print(f"  [INFO] dropped {dropped} censored observations from the weight "
                  f"search (they are NOT imputed)")

    df = df[pd.to_numeric(df[outcome], errors="coerce").notna()]
    return df.groupby("service", as_index=False)[outcome].mean()


# ── Protocols ─────────────────────────────────────────────────────────────────

def run_fixed(graph_path: Path, centrality_path: Path) -> None:
    """Apply FIXED_WEIGHTS. No outcome data is read. No search is performed."""
    print("=" * 70)
    print("PROTOCOL: fixed")
    print("=" * 70)
    print(f"  Weights: w_in={FIXED_WEIGHTS.w_in}, w_out={FIXED_WEIGHTS.w_out}, "
          f"w_btw={FIXED_WEIGHTS.w_btw}")
    print("  Source:  centrality/metric_constants.py::FIXED_WEIGHTS")
    print("  Outcome data is NOT read under this protocol.")

    G = load_graph(graph_path)
    refuse_quarantined(centrality_path)
    cent = pd.read_csv(centrality_path)

    out = compute_hybrid(cent, FIXED_WEIGHTS)
    out = _attach_structural(out, G)
    print()
    print(out[["service", "in_degree", "out_degree", "betweenness",
               "descendant_count", "dominator_subtree_size",
               "hybrid_criticality"]].to_string(index=False))


def run_cross_arch_tune(
    graph_path: Path, centrality_path: Path, results_path: Path, outcome: str,
    step: float,
) -> None:
    """Search the grid on the TUNING architecture only, then freeze the winner."""
    print("=" * 70)
    print(f"PROTOCOL: cross-arch / stage=tune  (architecture: {TUNING_ARCHITECTURE})")
    print("=" * 70)

    if LOCKFILE.exists():
        raise SystemExit(
            f"[REFUSED] {LOCKFILE} already exists. Weights are already frozen.\n"
            f"          Re-tuning after seeing a result is leakage. Delete the lockfile\n"
            f"          deliberately and record why, if you truly mean to re-tune."
        )

    G = load_graph(graph_path)
    refuse_quarantined(centrality_path)
    cent = pd.read_csv(centrality_path)
    outcomes = load_outcomes(results_path, outcome)

    steps = [round(i * step, 6) for i in range(int(1 / step) + 1)]
    triplets = [
        HybridWeights(a, b, round(1.0 - a - b, 6))
        for a, b in product(steps, steps)
        if -1e-9 <= round(1.0 - a - b, 6) <= 1.0 + 1e-9
    ]

    rows = []
    for w in triplets:
        merged = compute_hybrid(cent, w).merge(outcomes, on="service")
        if len(merged) < 3 or merged["hybrid_criticality"].nunique() < 2:
            continue
        rho, p = stats.spearmanr(merged["hybrid_criticality"], merged[outcome])
        rows.append({"w_in": w.w_in, "w_out": w.w_out, "w_btw": w.w_btw,
                     "rho": round(float(rho), 6), "p": round(float(p), 6),
                     "n_services": len(merged)})

    if not rows:
        raise SystemExit("[FAIL] no valid weight triplet produced a correlation")

    grid = pd.DataFrame(rows).sort_values("rho", ascending=False)
    grid_path = ROOT / "centrality" / "output" / "weight_grid_tuning_arch.csv"
    grid_path.parent.mkdir(parents=True, exist_ok=True)
    grid.to_csv(grid_path, index=False)

    best = grid.iloc[0]
    LOCKFILE.parent.mkdir(parents=True, exist_ok=True)
    LOCKFILE.write_text(json.dumps({
        "protocol": "cross-arch",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "tuned_on_architecture": TUNING_ARCHITECTURE,
        "tuned_on_results": str(results_path),
        "outcome": outcome,
        "grid_step": step,
        "n_triplets_searched": len(grid),
        "w_in": float(best["w_in"]), "w_out": float(best["w_out"]),
        "w_btw": float(best["w_btw"]),
        "tuning_rho": float(best["rho"]), "tuning_p": float(best["p"]),
        "heldout_architecture": HELDOUT_ARCHITECTURE,
        "evaluated": False,
    }, indent=2), encoding="utf-8")

    print(f"  Searched {len(grid)} triplets at step {step}")
    print(f"  Best on tuning architecture: w_in={best['w_in']}, w_out={best['w_out']}, "
          f"w_btw={best['w_btw']}  rho={best['rho']} p={best['p']}")
    print(f"  Grid written to {grid_path.relative_to(ROOT)}")
    print(f"  Weights FROZEN in {LOCKFILE.relative_to(ROOT)}")
    print()
    print("  NOTE: this rho is a MAXIMUM OVER A SEARCH on the tuning architecture.")
    print("        It is not a validation result and must never be reported as one.")
    print(f"        Only the held-out {HELDOUT_ARCHITECTURE} evaluation is reportable.")


def run_cross_arch_evaluate(
    graph_path: Path, centrality_path: Path, results_path: Path, outcome: str,
) -> None:
    """Evaluate the frozen weights once on the held-out architecture."""
    print("=" * 70)
    print(f"PROTOCOL: cross-arch / stage=evaluate  (held out: {HELDOUT_ARCHITECTURE})")
    print("=" * 70)

    if not LOCKFILE.exists():
        raise SystemExit(
            f"[REFUSED] {LOCKFILE} not found. Run --stage tune first.\n"
            f"          Evaluating without frozen weights is not a held-out test."
        )

    lock = json.loads(LOCKFILE.read_text(encoding="utf-8"))
    if lock.get("evaluated"):
        raise SystemExit(
            f"[REFUSED] the held-out architecture has already been evaluated once\n"
            f"          (at {lock.get('evaluated_at')}, rho={lock.get('heldout_rho')}).\n"
            f"          Evaluating twice turns the held-out set into a tuning set."
        )

    weights = HybridWeights(lock["w_in"], lock["w_out"], lock["w_btw"])
    print(f"  Frozen weights: w_in={weights.w_in}, w_out={weights.w_out}, "
          f"w_btw={weights.w_btw}")
    print(f"  Frozen at {lock['frozen_at']} on {lock['tuned_on_architecture']}")

    load_graph(graph_path)
    refuse_quarantined(centrality_path)
    cent = pd.read_csv(centrality_path)
    outcomes = load_outcomes(results_path, outcome)

    merged = compute_hybrid(cent, weights).merge(outcomes, on="service")
    rho, p = stats.spearmanr(merged["hybrid_criticality"], merged[outcome])

    lock.update({
        "evaluated": True,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "heldout_results": str(results_path),
        "heldout_rho": round(float(rho), 6),
        "heldout_p": round(float(p), 6),
        "heldout_n_services": len(merged),
    })
    LOCKFILE.write_text(json.dumps(lock, indent=2), encoding="utf-8")

    print()
    print(f"  HELD-OUT RESULT: rho = {rho:.4f}, p = {p:.4f}, n = {len(merged)} services")
    print()
    print("  This is the reportable number, whatever it says. Per CLAUDE.md rule 4,")
    print("  a null result is reported as null. The lockfile is now spent.")


def _attach_structural(df: pd.DataFrame, G: nx.DiGraph) -> pd.DataFrame:
    anc = ancestor_count(G)
    desc = descendant_count(G)
    dom = dominator_subtree_size(G)
    df = df.copy()
    df["ancestor_count"] = df["service"].map(anc).fillna(0).astype(int)
    df["descendant_count"] = df["service"].map(desc).fillna(0).astype(int)
    df["dominator_subtree_size"] = df["service"].map(dom).fillna(0).astype(int)
    return df


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Leakage-free hybrid weight selection. --protocol is required.",
    )
    ap.add_argument("--protocol", required=True, choices=["fixed", "cross-arch"],
                    help="'fixed' uses metric_constants.FIXED_WEIGHTS and never reads "
                         "outcome data. 'cross-arch' tunes on one architecture and "
                         "evaluates once on the other. There is no default.")
    ap.add_argument("--stage", choices=["tune", "evaluate"],
                    help="Required for --protocol cross-arch.")
    ap.add_argument("--graph", required=True, type=Path)
    ap.add_argument("--centrality", type=Path,
                    default=ROOT / "centrality" / "output" / "centrality_table.csv")
    ap.add_argument("--results", type=Path,
                    help="Raw results CSV from data/raw/. Not used by --protocol fixed.")
    ap.add_argument("--outcome", default="recovery_time_s")
    ap.add_argument("--step", type=float, default=GRID_STEP)
    args = ap.parse_args()

    if args.protocol == "fixed":
        if args.results:
            raise SystemExit(
                "[REFUSED] --protocol fixed must not be given --results. Fixed weights "
                "are never selected using outcome data."
            )
        run_fixed(args.graph, args.centrality)
        return 0

    if not args.stage:
        raise SystemExit("[FAIL] --protocol cross-arch requires --stage tune|evaluate")
    if not args.results:
        raise SystemExit("[FAIL] --protocol cross-arch requires --results")

    if args.stage == "tune":
        run_cross_arch_tune(args.graph, args.centrality, args.results,
                            args.outcome, args.step)
    else:
        run_cross_arch_evaluate(args.graph, args.centrality, args.results, args.outcome)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
