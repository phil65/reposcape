"""Base interface for importance calculation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from reposcape.importance.graph import Graph


if TYPE_CHECKING:
    from collections.abc import Sequence

    from reposcape.importance.scoring import GraphScorer
    from reposcape.models.nodes import CodeNode


class ImportanceCalculator:
    """Calculate importance of code elements using graph-based scoring."""

    def __init__(self, scorer: GraphScorer):
        """Initialize calculator with a scoring algorithm."""
        self.scorer = scorer

    def calculate(
        self,
        nodes: Sequence[CodeNode],
        focused_paths: set[str] | None = None,
        mentioned_symbols: set[str] | None = None,
    ) -> dict[str, float]:
        """Calculate importance scores for code elements.

        Args:
            nodes: Sequence of code nodes to analyze
            focused_paths: Set of paths that are currently in focus
            mentioned_symbols: Set of symbol names that were mentioned

        Returns:
            Dictionary mapping node paths to importance scores (0.0 to 1.0)
        """
        # Build graph
        graph = self._build_graph(nodes)

        # Get weights for mentioned symbols
        weights = self._get_weights(nodes, focused_paths, mentioned_symbols)

        # Calculate scores using the configured scorer
        return self.scorer.score(
            graph,
            important_nodes=focused_paths,
            weights=weights,
        )

    def _build_graph(self, nodes: Sequence[CodeNode]) -> Graph:
        """Build graph from code nodes."""
        graph = Graph()

        # First pass: add all nodes and collect symbol definitions
        symbol_defs: dict[str, str] = {}
        module_defs: dict[str, str] = {}

        for node in nodes:
            graph.add_node(node.path)

            # Track both local symbols and module names
            module_name = node.path.replace("/", ".")
            if module_name.endswith(".py"):
                module_name = module_name[:-3]
            module_defs[module_name] = node.path

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
                    if ref.module_reference:
                        # Handle module references
                        parts = ref.name.split(".")
                        for i in range(len(parts)):
                            module_path = ".".join(parts[: i + 1])
                            if module_path in module_defs:
                                target = module_defs[module_path]
                                graph.add_edge(node.path, target, weight=0.7)
                                break
                    # Handle local references
                    elif ref.name in symbol_defs:
                        target = symbol_defs[ref.name]
                        graph.add_edge(node.path, target, weight=0.5)

        return graph

    def _get_weights(
        self,
        nodes: Sequence[CodeNode],
        focused_paths: set[str] | None,
        mentioned_symbols: set[str] | None,
    ) -> dict[str, float]:
        """Calculate initial weights for nodes."""
        weights: dict[str, float] = {}

        if focused_paths:
            for path in focused_paths:
                weights[path] = weights.get(path, 1.0) + 1.0

        if mentioned_symbols:
            symbol_defs = {node.name: node.path for node in nodes}
            for symbol in mentioned_symbols:
                if symbol in symbol_defs:
                    path = symbol_defs[symbol]
                    weights[path] = weights.get(path, 1.0) + 0.5

        return weights
