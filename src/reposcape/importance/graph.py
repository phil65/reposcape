from __future__ import annotations

from typing import TYPE_CHECKING

import networkx as nx


if TYPE_CHECKING:
    from collections.abc import Iterator


class Graph:
    """Default graph implementation using networkx."""

    def __init__(self) -> None:
        """Initialize directed graph."""
        self.graph: nx.DiGraph = nx.DiGraph()

    def add_node(self, node_id: str) -> str:
        """Add a node to the graph.

        Args:
            node_id: Unique identifier for the node

        Returns:
            The node_id
        """
        if node_id not in self.graph:
            self.graph.add_node(node_id)
        return node_id

    def remove_node(self, node_id: str) -> None:
        """Remove a node and its edges from the graph."""
        if node_id in self.graph:
            self.graph.remove_node(node_id)

    def add_edge(self, from_id: str, to_id: str, weight: float = 1.0) -> None:
        """Add a weighted edge between nodes."""
        self.add_node(from_id)
        self.add_node(to_id)
        self.graph.add_edge(from_id, to_id, weight=weight)

    def get_nodes(self) -> set[str]:
        """Get all node IDs."""
        return set(self.graph.nodes())

    def get_edges(self, node_id: str) -> dict[str, float]:
        """Get outgoing edges and their weights for a node."""
        if node_id not in self.graph:
            return {}

        return {target: data.get("weight", 1.0) for target, data in self.graph[node_id].items()}

    def in_edges(self, node_id: str) -> Iterator[tuple[str, str, float]]:
        """Get incoming edges for a node as (source, target, weight) tuples."""
        if node_id not in self.graph:
            return
        for source, target, data in self.graph.in_edges(node_id, data=True):
            yield source, target, data.get("weight", 1.0)

    def out_edges(self, node_id: str) -> Iterator[tuple[str, str, float]]:
        """Get outgoing edges for a node as (source, target, weight) tuples."""
        if node_id not in self.graph:
            return
        for source, target, data in self.graph.out_edges(node_id, data=True):
            yield source, target, data.get("weight", 1.0)

    def get_graph(self) -> nx.DiGraph:
        """Get underlying networkx graph."""
        return self.graph
