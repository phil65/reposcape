"""Tests for graph implementation."""

from __future__ import annotations

from reposcape.importance.graph import RustworkxGraph


def test_add_nodes():
    """Test adding nodes to graph."""
    graph = RustworkxGraph()

    graph.add_node("a")
    graph.add_node("b")
    graph.add_node("c")

    assert graph.get_nodes() == {"a", "b", "c"}


def test_add_edges():
    """Test adding edges to graph."""
    graph = RustworkxGraph()

    graph.add_edge("a", "b", weight=1.0)
    graph.add_edge("b", "c", weight=0.5)

    # Check edges
    assert graph.get_edges("a") == {"b": 1.0}
    assert graph.get_edges("b") == {"c": 0.5}
    assert graph.get_edges("c") == {}


def test_node_indices():
    """Test node index mapping."""
    graph = RustworkxGraph()

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
    graph = RustworkxGraph()

    assert graph.get_edges("nonexistent") == {}
