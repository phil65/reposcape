"""Tree-style serialization of code structure."""

from __future__ import annotations

from typing import TYPE_CHECKING

from reposcape.models.nodes import NodeType
from reposcape.models.options import DetailLevel
from reposcape.serializers.base import CodeSerializer


if TYPE_CHECKING:
    from reposcape.models.nodes import CodeNode


class TreeSerializer(CodeSerializer):
    """Serialize code structure in a tree-like format."""

    def serialize(
        self,
        root: CodeNode,
        *,
        detail: DetailLevel,
        max_depth: int | None = None,
        token_limit: int | None = None,
    ) -> str:
        """Convert structure to tree format."""
        lines: list[str] = []
        self._serialize_node(
            root,
            lines,
            is_last=[True],
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
        is_last: list[bool],
        detail: DetailLevel,
        max_depth: int | None,
        remaining_tokens: int | None,
    ) -> int:
        """Serialize node in tree format."""
        depth = len(is_last) - 1
        if not self._should_include_node(node, depth, max_depth):
            return 0

        # Create the prefix
        if len(is_last) == 1:
            prefix = ""
        else:
            prefix = "".join("    " if last else "│   " for last in is_last[1:-1])
            prefix += "└── " if is_last[-1] else "├── "

        # Format node
        match node.node_type:
            case NodeType.DIRECTORY:
                line = f"{prefix}{node.name}/"
            case NodeType.FILE:
                line = f"{prefix}{node.name}"
            case _:
                if detail != DetailLevel.STRUCTURE and node.signature:
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
            children = sorted(
                node.children.values(), key=lambda n: (-n.importance, n.name)
            )
            for i, child in enumerate(children):
                is_last_child = i == len(children) - 1
                child_tokens = self._serialize_node(
                    child,
                    lines,
                    is_last=[*is_last, is_last_child],
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
