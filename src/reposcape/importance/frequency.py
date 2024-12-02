"""Frequency-based importance calculation."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from reposcape.importance.base import ImportanceCalculator


if TYPE_CHECKING:
    from collections.abc import Sequence

    from reposcape.models.nodes import CodeNode


class FrequencyCalculator(ImportanceCalculator):
    """Calculate importance based on symbol usage frequency and file references."""

    def calculate(
        self,
        nodes: Sequence[CodeNode],
        focused_paths: set[str] | None = None,
        mentioned_symbols: set[str] | None = None,
    ) -> dict[str, float]:
        """Calculate importance scores based on frequency of references."""
        focused_paths = focused_paths or set()
        mentioned_symbols = mentioned_symbols or set()

        # Build symbol definition map
        symbol_defs: dict[str, str] = {}  # symbol name -> defining file path
        for node in nodes:
            # Map all symbols in this file
            if node.children:
                for child in node.children.values():
                    symbol_defs[child.name] = node.path

        # Count references between files
        reference_counts: Counter[str] = Counter()
        for node in nodes:
            if node.references_to:
                # Count each unique reference once per file
                seen = set()
                for ref in node.references_to:
                    if ref.name in symbol_defs:
                        target_path = symbol_defs[ref.name]
                        if target_path != node.path:  # Don't count self-references
                            reference_counts[target_path] += 1
                            seen.add(target_path)

                    # If this is a focused file, boost its references
                    if node.path in focused_paths:
                        for target in seen:
                            reference_counts[target] += (
                                2  # Extra weight for focused file references
                            )

        # Calculate scores
        scores: dict[str, float] = {}

        for node in nodes:
            path = node.path
            score = 0.0

            # Base score from being referenced
            if path in reference_counts:
                score += 0.4 * reference_counts[path]

            # Score from having symbols that are referenced
            if node.children:
                score += 0.2 * len(node.children)

            # Direct focus boost
            if path in focused_paths:
                score += 0.8

            # Reference relationship to focused files
            if focused_paths and any(
                symbol_defs.get(ref.name) in focused_paths
                for ref in (node.references_to or [])
            ):
                score += 0.4

            # Store score
            scores[path] = score

        # Normalize scores
        if scores:
            max_score = max(scores.values())
            if max_score > 0:
                scores = {k: v / max_score for k, v in scores.items()}

        return scores
