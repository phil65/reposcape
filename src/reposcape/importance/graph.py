from __future__ import annotations

from typing import Protocol

import rustworkx as rx


class Graph(Protocol):
    """Graph interface that different implementations can satisfy."""

    def add_node(self, node_id: str) -> None:
        """Add a node to the graph."""

    def add_edge(self, from_id: str, to_id: str, weight: float = 1.0) -> None:
        """Add a weighted edge between nodes."""

    def get_nodes(self) -> set[str]:
        """Get all node IDs."""

    def get_edges(self, node_id: str) -> dict[str, float]:
        """Get outgoing edges and their weights for a node."""

    def get_graph(self) -> rx.PyDiGraph:
        """Get underlying rustworkx graph."""

    def get_node_index(self, node_id: str) -> int:
        """Get rustworkx node index for node_id."""


class RustworkxGraph:
    """Default graph implementation using rustworkx."""

    def __init__(self) -> None:
        """Initialize directed graph."""
        self.graph = rx.PyDiGraph()
        self.node_map: dict[str, int] = {}

    def add_node(self, node_id: str) -> None:
        """Add a node to the graph."""
        if node_id not in self.node_map:
            idx = self.graph.add_node(node_id)
            self.node_map[node_id] = idx

    def add_edge(self, from_id: str, to_id: str, weight: float = 1.0) -> None:
        """Add a weighted edge between nodes."""
        self.add_node(from_id)
        self.add_node(to_id)
        self.graph.add_edge(
            self.node_map[from_id],
            self.node_map[to_id],
            weight,
        )

    def get_nodes(self) -> set[str]:
        """Get all node IDs."""
        return set(self.node_map.keys())

    def get_edges(self, node_id: str) -> dict[str, float]:
        """Get outgoing edges and their weights for a node."""
        if node_id not in self.node_map:
            return {}

        idx = self.node_map[node_id]
        edges = {}

        # out_edges returns list of (source, target, weight) tuples
        for _, target, weight in self.graph.out_edges(idx):
            target_id = next(k for k, v in self.node_map.items() if v == target)
            edges[target_id] = weight

        return edges

    def get_graph(self) -> rx.PyDiGraph:
        """Get underlying rustworkx graph."""
        return self.graph

    def get_node_index(self, node_id: str) -> int:
        """Get rustworkx node index for node_id."""
        return self.node_map[node_id]