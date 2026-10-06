"""Unit tests for the structural baseline metrics and the leakage guards.

Fixtures are hand-built graphs with known answers. No random data, no measured data.
"""

from __future__ import annotations

import networkx as nx
import pytest

from centrality.hybrid_weight_optimizer import (
    ancestor_count,
    compute_hybrid,
    descendant_count,
    dominator_subtree_size,
    refuse_quarantined,
)
from centrality.metric_constants import FIXED_WEIGHTS, HybridWeights


@pytest.fixture
def diamond():
    """entry -> a,b ; a,b -> c. No single node except entry dominates c."""
    G = nx.DiGraph()
    G.add_edges_from([("entry", "a"), ("entry", "b"), ("a", "c"), ("b", "c")])
    return G


@pytest.fixture
def chain():
    """entry -> a -> b -> c. Every node dominates everything after it."""
    G = nx.DiGraph()
    G.add_edges_from([("entry", "a"), ("a", "b"), ("b", "c")])
    return G


def test_descendant_count_chain(chain):
    assert descendant_count(chain) == {"entry": 3, "a": 2, "b": 1, "c": 0}


def test_descendant_count_diamond(diamond):
    # a reaches only c; entry reaches a, b and c
    assert descendant_count(diamond) == {"entry": 3, "a": 1, "b": 1, "c": 0}


def test_descendant_count_handles_cycles():
    """A node in a cycle must count each other member once, not loop forever."""
    G = nx.DiGraph()
    G.add_edges_from([("x", "y"), ("y", "x"), ("y", "z")])
    counts = descendant_count(G)
    assert counts["x"] == 2          # y and z
    assert counts["y"] == 2          # x and z
    assert counts["z"] == 0


def test_dominator_subtree_chain(chain):
    assert dominator_subtree_size(chain) == {"entry": 3, "a": 2, "b": 1, "c": 0}


def test_dominator_subtree_diamond_distinguishes_from_descendants(diamond):
    """The point of dominators: a does NOT dominate c, because b routes around it."""
    dom = dominator_subtree_size(diamond)
    assert dom["a"] == 0
    assert dom["b"] == 0
    assert dom["entry"] == 3
    # descendant_count cannot make this distinction
    assert descendant_count(diamond)["a"] == 1


def test_dominator_infers_entry_node(chain):
    # entry is the only node with in-degree 0
    assert dominator_subtree_size(chain, entry="entry") == dominator_subtree_size(chain)


def test_dominator_raises_without_a_source():
    G = nx.DiGraph()
    G.add_edges_from([("a", "b"), ("b", "a")])
    with pytest.raises(ValueError, match="in-degree 0"):
        dominator_subtree_size(G)


def test_dominator_on_real_hotel_shape():
    """The observed HR graph: frontend -> {profile, recommendation, reservation,
    search}, search -> {geo, rate}. A tree, so dominators == descendants."""
    G = nx.DiGraph()
    G.add_edges_from([
        ("frontend", "profile"), ("frontend", "recommendation"),
        ("frontend", "reservation"), ("frontend", "search"),
        ("search", "geo"), ("search", "rate"),
    ])
    dom = dominator_subtree_size(G)
    assert dom["frontend"] == 6
    assert dom["search"] == 2
    assert dom["geo"] == 0
    assert dom == descendant_count(G)      # tree: the two metrics coincide


def test_hybrid_matches_the_documented_formula():
    df = __import__("pandas").DataFrame({
        "service": ["a", "b"],
        "in_degree": [0.1, 0.2],
        "out_degree": [0.8, 0.4],
        "betweenness": [0.5, 0.0],
    })
    out = compute_hybrid(df, HybridWeights(0.4, 0.4, 0.2))
    # a is the max out-degree, so its fan_out_weight is 1.0
    # 0.4*0.1 + 0.4*0.8*1.0 + 0.2*0.5 = 0.04 + 0.32 + 0.10 = 0.46
    assert out.loc[0, "hybrid_criticality"] == pytest.approx(0.46)
    # b: fan_out_weight = 0.4/0.8 = 0.5
    # 0.4*0.2 + 0.4*0.4*0.5 + 0.2*0.0 = 0.08 + 0.08 = 0.16
    assert out.loc[1, "hybrid_criticality"] == pytest.approx(0.16)


def test_weights_must_sum_to_one():
    with pytest.raises(ValueError, match="sum to 1.0"):
        HybridWeights(0.5, 0.5, 0.5).validate()


def test_weights_must_be_non_negative():
    with pytest.raises(ValueError, match="non-negative"):
        HybridWeights(1.2, -0.2, 0.0).validate()


def test_fixed_weights_are_valid():
    FIXED_WEIGHTS.validate()
    assert FIXED_WEIGHTS == (0.4, 0.4, 0.2)


def test_quarantined_paths_are_refused(tmp_path):
    q = tmp_path / "_quarantine" / "measurement" / "experiment_log.csv"
    q.parent.mkdir(parents=True)
    q.write_text("x")
    with pytest.raises(SystemExit, match="quarantined"):
        refuse_quarantined(q)


def test_non_quarantined_paths_are_allowed(tmp_path):
    ok = tmp_path / "data" / "raw" / "batch.csv"
    ok.parent.mkdir(parents=True)
    ok.write_text("x")
    refuse_quarantined(ok)       # must not raise


# ── ancestor_count (primary predictor, added 2026-09-25) ─────────────────────

def test_ancestor_count_is_descendant_count_on_the_reversed_graph():
    """The defining identity: ancestors in G == descendants in G-reversed."""
    G = nx.DiGraph([("a", "b"), ("b", "c"), ("a", "d"), ("d", "c")])
    assert ancestor_count(G) == descendant_count(G.reverse(copy=False))


def test_ancestor_count_matches_networkx_ancestors():
    G = nx.DiGraph([("a", "b"), ("b", "c"), ("a", "d"), ("d", "c"), ("e", "c")])
    got = ancestor_count(G)
    assert got == {n: len(nx.ancestors(G, n)) for n in G.nodes()}
    assert got == {"a": 0, "b": 1, "c": 4, "d": 1, "e": 0}


def test_ancestor_count_excludes_the_node_itself():
    G = nx.DiGraph([("a", "b")])
    assert ancestor_count(G)["a"] == 0


def test_ancestor_count_is_transitive_not_just_in_degree():
    """A chain: the leaf has in-degree 1 but 3 ancestors."""
    G = nx.DiGraph([("a", "b"), ("b", "c"), ("c", "d")])
    assert G.in_degree("d") == 1
    assert ancestor_count(G)["d"] == 3


def test_ancestor_count_counts_each_cycle_member_once():
    G = nx.DiGraph([("a", "b"), ("b", "c"), ("c", "a"), ("c", "d")])
    got = ancestor_count(G)
    assert got["d"] == 3            # a, b, c -- each once
    assert got["a"] == 2            # b, c

def test_ancestor_count_does_not_mutate_the_input_graph():
    G = nx.DiGraph([("a", "b"), ("b", "c")])
    before = (sorted(G.nodes()), sorted(G.edges()))
    ancestor_count(G)
    assert (sorted(G.nodes()), sorted(G.edges())) == before


def test_ancestor_count_on_an_isolated_node_is_zero():
    G = nx.DiGraph()
    G.add_node("lonely")
    assert ancestor_count(G) == {"lonely": 0}
