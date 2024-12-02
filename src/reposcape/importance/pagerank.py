"""PageRank-based importance calculation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import networkx as nx


if TYPE_CHECKING:
    from collections.abc import Sequence

    from reposcape.models.nodes import CodeNode

from reposcape.importance.base import ImportanceCalculator


class PageRankCalculator(ImportanceCalculator):
    """Calculate importance using PageRank on code relationships."""

    def calculate(
        self,
        nodes: Sequence[CodeNode],
        focused_paths: set[str] | None = None,
        mentioned_symbols: set[str] | None = None,
    ) -> dict[str, float]:
        """Calculate importance using PageRank algorithm."""
        focused_paths = focused_paths or set()
        mentioned_symbols = mentioned_symbols or set()

        # Create directed graph
        graph = nx.DiGraph()

        # Map symbols to their defining nodes
        symbol_defs: dict[str, str] = {}

        # First pass: add nodes and collect symbol definitions
        for node in nodes:
            graph.add_node(node.path)
            symbol_defs[node.name] = node.path

            if node.children:
                for child in node.children.values():
                    symbol_defs[child.name] = child.path

        # Second pass: add edges
        for node in nodes:
            # Add parent-child relationships
            if node.children:
                for child in node.children.values():
                    graph.add_edge(node.path, child.path, weight=1.0)

            # Add reference relationships
            if node.references_to:
                for ref in node.references_to:
                    if ref.name in symbol_defs:
                        target = symbol_defs[ref.name]
                        # Add edge from referencing file to referenced symbol
                        graph.add_edge(node.path, target, weight=0.5)

        # Configure PageRank parameters
        personalization = {}

        # Boost focused files
        for path in focused_paths:
            personalization[path] = 2.0

        # Boost files containing mentioned symbols
        for symbol in mentioned_symbols:
            if symbol in symbol_defs:
                path = symbol_defs[symbol]
                personalization[path] = personalization.get(path, 1.0) + 1.0

        # Calculate PageRank
        return nx.pagerank(
            graph,
            alpha=0.85,  # damping parameter
            personalization=personalization if personalization else None,
        )
