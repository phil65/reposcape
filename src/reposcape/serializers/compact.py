"""Compact serialization of code structure."""

from __future__ import annotations

from typing import TYPE_CHECKING

from reposcape.models.nodes import NodeType
from reposcape.models.options import DetailLevel
from reposcape.serializers.base import CodeSerializer


if TYPE_CHECKING:
    from reposcape.models.nodes import CodeNode


class CompactSerializer(CodeSerializer):
    """Serialize code structure in a compact format."""

    def serialize(
        self,
        root: CodeNode,
        *,
        detail: DetailLevel,
        max_depth: int | None = None,
        token_limit: int | None = None,
    ) -> str:
        """Convert structure to compact format."""
        lines: list[str] = []
        self._serialize_node(
            root,
            lines,
            prefix="",
            detail=detail,
            max_depth=max_depth,
            remaining_tokens=token_limit,
        )
        return "\n".join(lines)

    def _serialize_node(
        self,
        node: CodeNode,
        lines: list[str],
        *,
        prefix: str,
        detail: DetailLevel,
        max_depth: int | None,
        remaining_tokens: int | None,
    ) -> int:
        """Serialize node in compact format."""
        depth = len(prefix) // 2
        if not self._should_include_node(node, depth, max_depth):
            return 0

        # Format node line
        if node.node_type == NodeType.DIRECTORY:
            line = f"{prefix}{node.name}/"
        elif node.node_type == NodeType.FILE:
            line = f"{prefix}{node.name}"
        # For code elements, show signature in compact form
        elif detail != DetailLevel.STRUCTURE and node.signature:
            sig = node.signature.replace("\n", " ").replace("    ", "")
            line = f"{prefix}{sig}"
        else:
            line = f"{prefix}{node.name}"

        tokens_used = self._estimate_tokens(line)
        if remaining_tokens is not None:
            remaining_tokens -= tokens_used
            if remaining_tokens <= 0:
                return tokens_used

        lines.append(line)

        # Process children
        if node.children:
            new_prefix = prefix + "  "
            for child in sorted(
                node.children.values(), key=lambda n: (-n.importance, n.name)
            ):
                child_tokens = self._serialize_node(
                    child,
                    lines,
                    prefix=new_prefix,
                    detail=detail,
                    max_depth=max_depth,
                    remaining_tokens=remaining_tokens,
                )
                tokens_used += child_tokens
                if remaining_tokens is not None:
                    remaining_tokens -= child_tokens
                    if remaining_tokens <= 0:
                        break

        return tokens_used
