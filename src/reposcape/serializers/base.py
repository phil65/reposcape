"""Base serialization interface and utilities."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from reposcape.utils.tokens import count_tokens


if TYPE_CHECKING:
    from reposcape.models.nodes import CodeNode
    from reposcape.models.options import DetailLevel


LOW_IMPORTANCE_THRESHOLD = 0.3
HIGH_IMPORTANCE_THRESHOLD = 0.7


class CodeSerializer(ABC):
    """Base class for code structure serializers."""

    @abstractmethod
    def serialize(
        self,
        root: CodeNode,
        *,
        detail: DetailLevel,
        max_depth: int | None = None,
        token_limit: int | None = None,
    ) -> str:
        """Serialize code structure to string.

        Args:
            root: Root node of the structure
            detail: Level of detail to include
            max_depth: Maximum depth to traverse
            token_limit: Maximum number of tokens in output

        Returns:
            Serialized representation as string
        """

    def _should_include_node(
        self,
        node: CodeNode,
        current_depth: int,
        max_depth: int | None,
    ) -> bool:
        """Check if node should be included based on depth and importance."""
        if max_depth is not None and current_depth > max_depth:
            return False

        # Always include high importance nodes
        if node.importance > HIGH_IMPORTANCE_THRESHOLD:
            return True

        # Skip low importance nodes at deeper levels
        return not (current_depth > 2 and node.importance < LOW_IMPORTANCE_THRESHOLD)  # noqa: PLR2004

    def _estimate_tokens(self, text: str) -> int:
        """Accurate token count using tiktoken."""
        return count_tokens(text)
