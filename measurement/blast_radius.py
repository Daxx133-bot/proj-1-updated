"""
blast_radius.py — classify which services degrade during a fault, by graph relationship.

WHY THIS EXISTS
---------------
The old `downstream_affected_count` was a single number that conflated two unrelated
mechanisms and, despite its name, never counted downstream services at all. Pilot
evidence (`_audit/PILOT_FINDINGS.md`, 8 runs): **zero descendants degraded in any run**,
including `compose-post-service`, which has 10 of them.

THE CAUSAL CHAIN, DERIVED
-------------------------
Let X -> Y mean "X calls Y". Now kill Y:

  * X (a CALLER of Y, i.e. an ANCESTOR) issues an RPC to Y, gets connection-refused or a
    timeout, and therefore errors or slows. X DEGRADES. X's own callers then see X slow,
    so the effect climbs transitively up the ancestor set.

  * Z (a CALLEE of Y, i.e. a DESCENDANT) is never called, because Y is dead and Y was the
    thing that called Z. Z simply receives LESS traffic. Z goes IDLE. Z does NOT degrade,
    and an idle service shows no latency or error anomaly at all.

So failure propagates UP the call graph (toward callers), not down.

WHICH CENTRALITY PREDICTS IT
----------------------------
It follows that the size of the degraded set is governed by |ancestors(Y)| -- a
transitive IN-degree property. OUT-degree (fan-out) predicts how many services go idle,
which is not an impact at all.

This contradicts the hypothesis the hybrid metric was built on, which amplifies
out-degree. The pilot bears it out: `compose-post-service` (out-degree 7, 10 descendants)
degraded 1 service; `media-service` (out-degree 0, 0 descendants) degraded 2 ancestors
plus 5 unrelated. Across all 8 pilot runs `ancestor_affected_count == |ancestors|`
exactly, and `descendant_affected_count` was 0 every time.

THE THIRD CATEGORY
------------------
`unrelated_affected_count` captures services that are neither ancestors nor descendants
of the faulted node. In the pilot this was non-zero only for `media-service`, where the
degraded set included `compose-post-service`'s other callees and their callees. The
likely mechanism is synchronous fan-out contention: the caller blocks on the dead
dependency, and its sibling calls queue behind it. It is kept as a SEPARATE column rather
than folded into a total, because it is a different mechanism and must not be allowed to
silently inflate the primary outcome.
"""

from __future__ import annotations

from typing import Iterable

import networkx as nx

ANCESTOR = "ancestor"
DESCENDANT = "descendant"
UNRELATED = "unrelated"


def classify_affected(
    graph: nx.DiGraph,
    faulted_service: str,
    affected_services: Iterable[str],
) -> dict[str, object]:
    """Split the degraded set by graph relationship to the faulted service.

    Args:
        graph: the service dependency graph (edge X->Y means "X calls Y").
        faulted_service: the service the fault was injected into.
        affected_services: services observed to degrade during the fault window.

    Returns:
        Counts and member lists for each of the three categories, plus the structural
        sizes |ancestors| and |descendants| so a run record is self-describing and the
        classification can be re-checked without reloading the graph.
    """
    if faulted_service not in graph:
        raise ValueError(f"{faulted_service!r} is not a node in the graph")

    ancestors = nx.ancestors(graph, faulted_service)
    descendants = nx.descendants(graph, faulted_service)

    anc, desc, unrel = [], [], []
    for svc in affected_services:
        svc = svc.strip()
        if not svc or svc == faulted_service:
            continue
        if svc in ancestors:
            anc.append(svc)
        elif svc in descendants:
            desc.append(svc)
        else:
            unrel.append(svc)

    return {
        # PRIMARY blast-radius outcome. Predicted by |ancestors|, NOT by out-degree.
        "ancestor_affected_count": len(anc),
        "descendant_affected_count": len(desc),
        "unrelated_affected_count": len(unrel),
        "ancestor_affected_services": ",".join(sorted(anc)),
        "descendant_affected_services": ",".join(sorted(desc)),
        "unrelated_affected_services": ",".join(sorted(unrel)),
        # Structural reference values, for checking predictor vs outcome.
        "n_ancestors": len(ancestors),
        "n_descendants": len(descendants),
        "in_degree_raw": graph.in_degree(faulted_service),
        "out_degree_raw": graph.out_degree(faulted_service),
    }


def is_gateway(graph: nx.DiGraph, service: str) -> bool:
    """Amendment (a): a gateway is a sole entry point, i.e. in-degree 0 in the SDG.

    The external load generator is not a node in the graph, so a service whose only
    inbound traffic comes from outside has in-degree 0. Such a service cannot have a
    meaningful ancestor-affected count -- it has no ancestors by construction -- so
    including it in a correlation between a downstream-facing structural metric and a
    degradation outcome guarantees a confounded point.

    Gateways stay in the qualitative tables, labelled as excluded.
    """
    return graph.in_degree(service) == 0


def analysis_services(graph: nx.DiGraph) -> list[str]:
    """Services eligible for the quantitative correlation analysis (gateways removed)."""
    return sorted(n for n in graph.nodes() if not is_gateway(graph, n))
