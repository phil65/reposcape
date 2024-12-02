"""Compact serialization of code structure."""

from __future__ import annotations

from typing import TYPE_CHECKING

from reposcape.models.nodes import NodeType
from reposcape.models.options import DetailLevel, PrivacyMode
from reposcape.serializers.base import CodeSerializer


if TYPE_CHECKING:
    from reposcape.models.nodes import CodeNode


class CompactSerializer(CodeSerializer):
    """Serialize code structure in a compact format."""

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
            prefix="",
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
            prefix="",
            detail=detail,
            included=included,
        )
        return "\n".join(lines)

    def _serialize_node_with_children(
        self,
        node: CodeNode,
        lines: list[str],
        *,
        prefix: str,
        detail: DetailLevel,
        privacy: PrivacyMode = "smart",
        included: set[str] | None = None,
    ) -> None:
        """Serialize node in compact format."""
        if not self._should_include_node(node, included, privacy):
            return

        # Format node line
        privacy_indicator = "🔒" if node.is_private else ""

        match node.node_type:
            case NodeType.DIRECTORY:
                line = f"{prefix}{node.name}/"
            case NodeType.FILE:
                line = f"{prefix}{node.name}"
            case _:
                # For code elements, show signature in compact form
                if detail != DetailLevel.STRUCTURE and node.signature:
                    sig = node.signature.replace("\n", " ").replace("    ", "")
                    line = f"{prefix}{privacy_indicator}{sig}"
                else:
                    line = f"{prefix}{privacy_indicator}{node.name}"

        lines.append(line)

        # Process children
        if node.children:
            new_prefix = prefix + "  "
            for child in sorted(
                node.children.values(),
                key=lambda n: (-n.importance, n.name),
            ):
                self._serialize_node_with_children(
                    child,
                    lines,
                    prefix=new_prefix,
                    detail=detail,
                    privacy=privacy,
                    included=included,
                )
