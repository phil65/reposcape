"""Base interface for importance calculation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Sequence

    from reposcape.models.nodes import CodeNode


class ImportanceCalculator(ABC):
    """Abstract base class for calculating importance of code elements."""

    @abstractmethod
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
