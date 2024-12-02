"""Scoring algorithms for importance calculation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import rustworkx as rx


if TYPE_CHECKING:
    from .graph import Graph


class GraphScorer(ABC):
    """Abstract interface for graph scoring algorithms."""

    @abstractmethod
    def score(
        self,
        graph: Graph,
        important_nodes: set[str] | None = None,
        weights: dict[str, float] | None = None,
    ) -> dict[str, float]:
        """Calculate importance scores for nodes."""

    def _normalize_scores(self, scores: dict[str, float]) -> dict[str, float]:
        """Normalize scores to 0.0-1.0 range."""
        if not scores:
            return {}
        max_score = max(scores.values())
        if max_score <= 0:
            return {k: 0.0 for k in scores}
        return {k: v / max_score for k, v in scores.items()}


class ReferenceScorer(GraphScorer):
    """Simple reference-based scoring.

    Scores are based on:
    - Number of incoming references (highest weight)
    - Number of outgoing references (medium weight)
    - Being referenced by important files (high boost)
    - Distance from important files (decreasing boost)
    """

    def __init__(
        self,
        *,
        ref_weight: float = 1.0,
        outref_weight: float = 0.5,
        important_ref_boost: float = 2.0,
        distance_decay: float = 0.5,
    ):
        """Initialize scorer with weights.

        Args:
            ref_weight: Weight for incoming references
            outref_weight: Weight for outgoing references
            important_ref_boost: Boost when referenced by important nodes
            distance_decay: How quickly importance decreases with distance
        """
        self.ref_weight = ref_weight
        self.outref_weight = outref_weight
        self.important_ref_boost = important_ref_boost
        self.distance_decay = distance_decay

    def score(
        self,
        graph: Graph,
        important_nodes: set[str] | None = None,
        weights: dict[str, float] | None = None,
    ) -> dict[str, float]:
        """Calculate reference-based scores."""
        important_nodes = {
            n for n in (important_nodes or set()) if n in graph.get_nodes()
        }
        weights = {k: v for k, v in (weights or {}).items() if k in graph.get_nodes()}

        # Get rustworkx graph for efficient operations
        rx_graph = graph.get_graph()

        # Initialize base scores
        scores: dict[str, float] = {node: 0.0 for node in graph.get_nodes()}

        # Add scores from reference counts
        for node_id in graph.get_nodes():
            idx = graph.get_node_index(node_id)

            # Incoming references score
            in_edges = rx_graph.in_edges(idx)
            scores[node_id] += len(in_edges) * self.ref_weight

            # Extra score for references from important nodes
            if important_nodes:
                important_refs = sum(
                    1
                    for source, _, _ in in_edges
                    if self._get_node_id(graph, source) in important_nodes
                )
                scores[node_id] += important_refs * self.important_ref_boost

            # Outgoing references score
            out_edges = rx_graph.out_edges(idx)
            scores[node_id] += len(out_edges) * self.outref_weight

        # Add pre-defined weights
        for node_id, weight in weights.items():
            scores[node_id] *= weight

        # Add distance-based scores if there are important nodes
        if important_nodes:
            try:
                distance_scores = self._calculate_distance_scores(graph, important_nodes)
                for node_id, distance_score in distance_scores.items():
                    scores[node_id] += distance_score
            except KeyError:
                # Ignore distance scoring if any node is missing
                pass

        return self._normalize_scores(scores)

    def _calculate_distance_scores(
        self,
        graph: Graph,
        important_nodes: set[str],
    ) -> dict[str, float]:
        """Calculate scores based on distance from important nodes."""
        rx_graph = graph.get_graph()
        scores: dict[str, float] = {node: 0.0 for node in graph.get_nodes()}

        # For each important node
        for start_id in important_nodes:
            start_idx = graph.get_node_index(start_id)

            # Calculate shortest paths to all other nodes
            # Returns dict[target_idx, list[node_indices]]
            paths = rx.dijkstra_shortest_paths(
                rx_graph,
                start_idx,
                weight_fn=float,
            )

            # Convert path lengths to scores
            for node_id in graph.get_nodes():
                idx = graph.get_node_index(node_id)
                if idx in paths:
                    # Use path length (number of nodes - 1) as distance
                    path = paths[idx]
                    distance = len(path) - 1
                    # Score decreases with distance
                    scores[node_id] += self.distance_decay**distance

        return scores

    def _get_node_id(self, graph: Graph, index: int) -> str:
        """Get node ID from rustworkx index."""
        return next(
            node_id
            for node_id in graph.get_nodes()
            if graph.get_node_index(node_id) == index
        )


class PageRankScorer(GraphScorer):
    """PageRank-based scoring using rustworkx."""

    def score(
        self,
        graph: Graph,
        important_nodes: set[str] | None = None,
        weights: dict[str, float] | None = None,
    ) -> dict[str, float]:
        """Calculate PageRank scores."""
        # Create personalization dict if needed
        personalization = None
        if important_nodes and weights:
            personalization = {
                graph.get_node_index(node): weights.get(node, 1.0)
                for node in important_nodes
            }

        # Calculate PageRank using rustworkx
        scores = rx.pagerank(
            graph.get_graph(),
            personalization=personalization,
        )

        # Map scores back to node IDs
        return {
            node_id: scores[graph.get_node_index(node_id)]
            for node_id in graph.get_nodes()
        }
