"""Tests for importance scoring algorithms."""

from __future__ import annotations

import pytest

from reposcape.importance.graph import Graph
from reposcape.importance.scoring import PageRankScorer, ReferenceScorer


@pytest.fixture
def simple_graph() -> Graph:
    """Create a simple example graph for testing."""
    graph = Graph()

    # Create a simple reference chain: a -> b -> c
    graph.add_edge("a", "b", weight=1.0)
    graph.add_edge("b", "c", weight=1.0)

    return graph


@pytest.fixture
def complex_graph() -> Graph:
    """Create a more complex graph for testing."""
    graph = Graph()

    # Create a hub-and-spoke structure with weighted edges
    graph.add_edge("hub", "spoke1", weight=0.5)
    graph.add_edge("hub", "spoke2", weight=1.0)
    graph.add_edge("hub", "spoke3", weight=0.7)
    graph.add_edge("spoke1", "leaf1", weight=0.3)
    graph.add_edge("spoke2", "leaf2", weight=0.4)
    graph.add_edge("spoke3", "hub", weight=0.2)  # Cycle back

    return graph


def test_reference_scorer_with_important_nodes(complex_graph: Graph):
    """Test ReferenceScorer with specified important nodes."""
    scorer = ReferenceScorer()
    scores = scorer.score(
        complex_graph,
        important_nodes={"spoke1", "spoke2"},
        weights={"spoke1": 2.0, "spoke2": 1.5},
    )

    # Important nodes should have higher scores than unweighted nodes
    assert scores["spoke1"] > scores["spoke3"]
    assert scores["spoke2"] > scores["spoke3"]

    # Node with higher weight should have higher score
    assert scores["spoke1"] > scores["spoke2"]


def test_pagerank_scorer_with_cycle(complex_graph: Graph):
    """Test PageRankScorer on graph containing cycles."""
    scorer = PageRankScorer()
    scores = scorer.score(complex_graph)

    # In PageRank:
    # 1. All scores should be positive
    # 2. Scores should sum to approximately 1.0
    # 3. Nodes with no outgoing edges (dangling nodes) get special handling
    # 4. Nodes in the same strongly connected component should have similar scores

    # Check that all scores are positive
    assert all(score > 0 for score in scores.values())

    # Sum of scores should be close to 1.0 (standard PageRank normalization)
    assert abs(sum(scores.values()) - 1.0) < 1e-6  # noqa: PLR2004

    # Nodes in cycle should have similar scores
    cycle_nodes = {"hub", "spoke3"}
    cycle_scores = [scores[node] for node in cycle_nodes]
    # Similar within 0.1
    assert max(cycle_scores) - min(cycle_scores) < 0.1  # noqa: PLR2004

    # Leaf nodes (no outgoing edges) should have similar scores
    leaf_nodes = {"leaf1", "leaf2"}
    leaf_scores = [scores[node] for node in leaf_nodes]
    assert max(leaf_scores) - min(leaf_scores) < 0.1  # noqa: PLR2004


def test_invalid_graph_handling():
    """Test scorers' handling of invalid/empty graphs."""
    empty_graph = Graph()

    ref_scorer = ReferenceScorer()
    page_scorer = PageRankScorer()

    # Should return empty dict for empty graph
    assert ref_scorer.score(empty_graph) == {}
    assert page_scorer.score(empty_graph) == {}

    # Important nodes that don't exist should be ignored
    graph = Graph()
    graph.add_edge("a", "b", weight=1.0)

    # Should not raise error with non-existent nodes
    scores = ref_scorer.score(
        graph,
        important_nodes={"nonexistent", "a"},
        weights={"nonexistent": 1.0, "a": 1.0},
    )

    # Only existing nodes should be scored
    assert set(scores.keys()) == {"a", "b"}
