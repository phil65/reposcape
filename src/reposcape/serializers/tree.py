"""Tree-style serialization of code structure."""

from __future__ import annotations

from typing import TYPE_CHECKING

from reposcape.models.nodes import NodeType
from reposcape.models.options import DetailLevel, PrivacyMode
from reposcape.serializers.base import CodeSerializer


if TYPE_CHECKING:
    from reposcape.models.nodes import CodeNode


class TreeSerializer(CodeSerializer):
    """Serialize code structure in a tree-like format."""

    def _serialize_node(
        self,
        node: CodeNode,
        *,
        detail: DetailLevel,
        privacy: PrivacyMode,
    ) -> str:
        lines: list[str] = []
        self._serialize_node_with_children(
            node,
            lines,
            is_last=[True],
            detail=detail,
            privacy=privacy,
        )
        return "\n".join(lines)

    def _serialize_filtered(
        self,
        root: CodeNode,
        included: set[str],
        detail: DetailLevel,
    ) -> str:
        lines: list[str] = []
        self._serialize_node_with_children(
            root,
            lines,
            is_last=[True],
            detail=detail,
            included=included,
        )
        return "\n".join(lines)

    def _serialize_node_with_children(
        self,
        node: CodeNode,
        lines: list[str],
        *,
        is_last: list[bool],
        detail: DetailLevel,
        privacy: PrivacyMode = "smart",
        included: set[str] | None = None,
    ) -> None:
        """Serialize node in tree format."""
        if not self._should_include_node(node, included, privacy):
            return

        # Create the prefix with tree structure
        if len(is_last) == 1:
            prefix = ""
        else:
            prefix = "".join("    " if last else "│   " for last in is_last[1:-1])
            prefix += "└── " if is_last[-1] else "├── "

        # Format node with privacy indicator
        privacy_indicator = "🔒" if node.is_private else ""

        match node.node_type:
            case NodeType.DIRECTORY:
                line = f"{prefix}{node.name}/"
            case NodeType.FILE:
                line = f"{prefix}{node.name}"
            case _:
                if detail != DetailLevel.STRUCTURE and node.signature:
                    sig = node.signature.replace("\n", " ").replace("    ", "")
                    line = f"{prefix}{privacy_indicator}{sig}"
                else:
                    line = f"{prefix}{privacy_indicator}{node.name}"

        lines.append(line)

        # Process children
        if node.children:
            children = sorted(
                node.children.values(),
                key=lambda n: (-n.importance, n.name),
            )
            for i, child in enumerate(children):
                is_last_child = i == len(children) - 1
                self._serialize_node_with_children(
                    child,
                    lines,
                    is_last=[*is_last, is_last_child],
                    detail=detail,
                    privacy=privacy,
                    included=included,
                )
