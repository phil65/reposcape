"""Scoring algorithms for importance calculation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import networkx as nx


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
            return dict.fromkeys(scores, 0.0)
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
        focus_boost: float = 5.0,
    ):
        """Initialize scorer with weights.

        Args:
            ref_weight: Weight for incoming references
            outref_weight: Weight for outgoing references
            important_ref_boost: Boost when referenced by important nodes
            distance_decay: How quickly importance decreases with distance
            focus_boost: Multiplier for focused nodes
        """
        self.ref_weight = ref_weight
        self.outref_weight = outref_weight
        self.important_ref_boost = important_ref_boost
        self.distance_decay = distance_decay
        self.focus_boost = focus_boost

    def score(
        self,
        graph: Graph,
        important_nodes: set[str] | None = None,
        weights: dict[str, float] | None = None,
    ) -> dict[str, float]:
        """Calculate reference-based scores."""
        important_nodes = {n for n in (important_nodes or set()) if n in graph.get_nodes()}
        weights = {k: v for k, v in (weights or {}).items() if k in graph.get_nodes()}

        # Initialize scores
        scores: dict[str, float] = dict.fromkeys(graph.get_nodes(), 0.0)

        # Add base scores from references
        for node_id in graph.get_nodes():
            # Incoming references score
            in_edges = list(graph.in_edges(node_id))
            scores[node_id] += len(in_edges) * self.ref_weight

            # Outgoing references score
            out_edges = list(graph.out_edges(node_id))
            scores[node_id] += len(out_edges) * self.outref_weight

        # Apply focus boost to important nodes
        for node_id in important_nodes:
            scores[node_id] *= self.focus_boost

        # Apply additional weights
        for node_id, weight in weights.items():
            scores[node_id] *= weight

        return self._normalize_scores(scores)

    def _calculate_distance_scores(
        self,
        graph: Graph,
        important_nodes: set[str],
    ) -> dict[str, float]:
        """Calculate scores based on distance from important nodes."""
        nx_graph = graph.get_graph()
        scores: dict[str, float] = dict.fromkeys(graph.get_nodes(), 0.0)

        # For each important node
        for start_id in important_nodes:
            # Calculate shortest paths to all other nodes
            try:
                paths = nx.single_source_shortest_path_length(nx_graph, start_id)
            except nx.NetworkXError:
                continue

            # Convert path lengths to scores
            for node_id, distance in paths.items():
                # Score decreases with distance
                scores[node_id] += self.distance_decay**distance

        return scores


class PageRankScorer(GraphScorer):
    """PageRank-based scoring using networkx."""

    def score(
        self,
        graph: Graph,
        important_nodes: set[str] | None = None,
        weights: dict[str, float] | None = None,
    ) -> dict[str, float]:
        """Calculate PageRank scores."""
        g = graph.get_graph()

        if g.number_of_nodes() == 0:
            return {}

        # Create personalization dict if needed
        personalization = None
        if important_nodes and weights:
            personalization = {node: weights.get(node, 1.0) for node in important_nodes}

        try:
            scores = nx.pagerank(g, personalization=personalization, dangling=personalization)
        except nx.PowerIterationFailedConvergence:
            # Fall back to unweighted pagerank
            scores = nx.pagerank(g)

        return dict(scores)
