from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, NamedTuple

from reposcape.models.options import DetailLevel, PrivacyMode


if TYPE_CHECKING:
    from reposcape.models.nodes import CodeNode


class NodePriority(NamedTuple):
    """Priority information for a node."""

    node: CodeNode
    tokens_needed: int
    base_score: float  # From importance calculation
    adjusted_score: float  # After applying all factors


class CodeSerializer(ABC):
    """Base class for code structure serializers."""

    HIGH_IMPORTANCE_THRESHOLD = 0.8
    SMART_IMPORTANCE_THRESHOLD = 0.5

    def serialize(
        self,
        root: CodeNode,
        *,
        detail: DetailLevel,
        token_limit: int | None = None,
        privacy: PrivacyMode = "smart",
    ) -> str:
        """Serialize code structure to string.

        Args:
            root: Root node of the structure
            detail: Level of detail to include
            token_limit: Maximum number of tokens in output
            privacy: Privacy mode for filtering private nodes
        """
        # Get priorities for all nodes
        priorities = self._collect_priorities(root, detail, privacy)

        if token_limit:
            # Select nodes to include within token budget
            included = self._select_nodes(priorities, token_limit)
            return self._serialize_filtered(root, included, detail)

        # No limit - serialize based on privacy mode
        return self._serialize_node(root, detail=detail, privacy=privacy)

    def _estimate_tokens(self, text: str) -> int:
        """Estimate tokens in text."""
        from reposcape.utils.tokens import count_tokens

        return count_tokens(text)

    def _estimate_node_tokens(
        self,
        node: CodeNode,
        detail: DetailLevel,
    ) -> int:
        """Estimate tokens needed for a node."""
        tokens = self._estimate_tokens(node.name)

        if detail != DetailLevel.STRUCTURE:
            if node.signature:
                tokens += self._estimate_tokens(node.signature)
            if detail == DetailLevel.DOCSTRINGS and node.docstring:
                tokens += self._estimate_tokens(node.docstring)
            if detail == DetailLevel.FULL_CODE and node.content:
                tokens += self._estimate_tokens(node.content)

        return tokens + 10  # Buffer for formatting

    def _should_include_node(
        self,
        node: CodeNode,
        included: set[str] | None,
        privacy: PrivacyMode,
    ) -> bool:
        """Check if node should be included in output."""
        if included is not None:
            return node.path in included

        if node.is_private:
            match privacy:
                case "public_only":
                    return False
                case "all":
                    return True
                case "smart":
                    return (
                        node.importance > self.SMART_IMPORTANCE_THRESHOLD
                        or bool(node.docstring)
                        or any(
                            ref.source and not ref.source.is_private
                            for ref in (node.referenced_by or [])
                        )
                    )
        return True

    def _calculate_priority(
        self,
        node: CodeNode,
        detail: DetailLevel,
        privacy: PrivacyMode,
    ) -> NodePriority:
        """Calculate priority score for a node."""
        base_score = node.importance
        tokens = self._estimate_node_tokens(node, detail)

        if not node.is_private:
            return NodePriority(node, tokens, base_score, base_score)

        # Handle private nodes
        match privacy:
            case "public_only":
                adjusted = 0.0
            case "all":
                adjusted = base_score
            case "smart":
                adjusted = base_score
                # Boost score if node is important
                if node.docstring:
                    adjusted *= 1.2
                if node.referenced_by:
                    public_refs = sum(
                        1
                        for ref in node.referenced_by
                        if (ref.source and not ref.source.is_private)
                    )
                    adjusted *= 1 + (public_refs * 0.2)
                if node.children:
                    adjusted *= 1.1

        return NodePriority(node, tokens, base_score, adjusted)

    def _collect_priorities(
        self,
        root: CodeNode,
        detail: DetailLevel,
        privacy: PrivacyMode,
    ) -> list[NodePriority]:
        """Collect priorities for all nodes."""
        priorities: list[NodePriority] = []
        required_paths: set[str] = set()

        def process_node(node: CodeNode) -> None:
            priority = self._calculate_priority(node, detail, privacy)
            priorities.append(priority)

            # Mark parents of important nodes as required
            if priority.adjusted_score > self.HIGH_IMPORTANCE_THRESHOLD:
                current = node
                while hasattr(current, "parent") and current.parent:
                    required_paths.add(current.parent.path)
                    current = current.parent

            if node.children:
                for child in node.children.values():
                    process_node(child)

        process_node(root)

        # Boost required nodes
        return [
            NodePriority(
                p.node,
                p.tokens_needed,
                p.base_score,
                p.adjusted_score * 1.5
                if p.node.path in required_paths
                else p.adjusted_score,
            )
            for p in priorities
        ]

    def _select_nodes(
        self,
        priorities: list[NodePriority],
        token_limit: int,
    ) -> set[str]:
        """Select nodes to include within token limit."""
        # Sort by adjusted score
        sorted_priorities = sorted(
            priorities,
            key=lambda p: p.adjusted_score,
            reverse=True,
        )

        included: set[str] = set()
        tokens_used = 0

        for priority in sorted_priorities:
            if (
                tokens_used + priority.tokens_needed <= token_limit
                and priority.adjusted_score > 0
            ):
                included.add(priority.node.path)
                tokens_used += priority.tokens_needed

        return included

    @abstractmethod
    def _serialize_node(
        self,
        node: CodeNode,
        *,
        detail: DetailLevel,
        privacy: PrivacyMode,
    ) -> str:
        """Serialize a single node."""

    @abstractmethod
    def _serialize_filtered(
        self,
        root: CodeNode,
        included: set[str],
        detail: DetailLevel,
    ) -> str:
        """Serialize with filtered node set."""
