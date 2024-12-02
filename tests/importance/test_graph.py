"""Tests for graph implementation."""

from __future__ import annotations

import pytest

from reposcape.importance.graph import Graph


def test_add_nodes():
    """Test adding nodes to graph."""
    graph = Graph()

    graph.add_node("a")
    graph.add_node("b")
    graph.add_node("c")

    assert graph.get_nodes() == {"a", "b", "c"}


def test_add_edges():
    """Test adding edges to graph."""
    graph = Graph()

    graph.add_edge("a", "b", weight=1.0)
    graph.add_edge("b", "c", weight=0.5)

    # Check edges
    assert graph.get_edges("a") == {"b": 1.0}
    assert graph.get_edges("b") == {"c": 0.5}
    assert graph.get_edges("c") == {}


def test_node_indices():
    """Test node index mapping."""
    graph = Graph()

    graph.add_node("a")
    graph.add_node("b")

    # Indices should be unique
    assert graph.get_node_index("a") != graph.get_node_index("b")

    # Should maintain same index
    idx_a = graph.get_node_index("a")
    graph.add_node("a")  # Add again
    assert graph.get_node_index("a") == idx_a


def test_nonexistent_edges():
    """Test getting edges for nonexistent node."""
    graph = Graph()

    assert graph.get_edges("nonexistent") == {}


def test_graph_node_uniqueness():
    """Test that nodes are unique in graph."""
    graph = Graph()

    # Adding same node multiple times should reuse index
    idx1 = graph.add_node("a")
    idx2 = graph.add_node("a")

    # Should get same index
    assert idx1 == idx2

    # Should only have one node
    assert len(graph.get_nodes()) == 1

    # Index should be valid in underlying graph
    assert graph.graph.get_node_data(idx1) == "a"


def test_graph_multiple_nodes():
    """Test adding multiple nodes."""
    graph = Graph()

    # Different nodes should get different indices
    idx1 = graph.add_node("a")
    idx2 = graph.add_node("b")

    assert idx1 != idx2
    assert graph.get_nodes() == {"a", "b"}


def test_graph_edge_weights():
    """Test edge weight handling."""
    graph = Graph()

    graph.add_edge("a", "b", weight=0.5)
    edges = graph.get_edges("a")
    assert edges["b"] == 0.5  # noqa: PLR2004


def test_node_removal_handling():
    """Test node index handling after removal."""
    graph = Graph()

    graph.add_edge("a", "b", weight=1.0)
    graph.add_edge("b", "c", weight=1.0)

    # Get initial state
    initial_nodes = graph.get_nodes()
    assert "b" in initial_nodes

    # Remove node
    graph.remove_node("b")

    # Check that removed node is not in nodes
    assert "b" not in graph.get_nodes()

    # Check that edges are updated
    assert "b" not in graph.get_edges("a")

    # Check that we can't get index for removed node
    with pytest.raises(KeyError):
        graph.get_node_index("b")


def test_remove_nonexistent_node():
    """Test removing a node that doesn't exist."""
    graph = Graph()

    graph.add_node("a")

    # Should not raise error
    graph.remove_node("nonexistent")

    # Original node should still be there
    assert "a" in graph.get_nodes()
