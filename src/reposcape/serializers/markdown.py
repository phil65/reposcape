"""Markdown serialization of code structure."""

from __future__ import annotations

from reposcape.models.nodes import CodeNode, NodeType
from reposcape.models.options import DetailLevel, PrivacyMode
from reposcape.serializers.base import CodeSerializer


class MarkdownSerializer(CodeSerializer):
    """Serialize code structure to Markdown format."""

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
            depth=0,
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
            depth=0,
            detail=detail,
            included=included,
        )
        return "\n".join(lines)

    def _serialize_node_with_children(
        self,
        node: CodeNode,
        lines: list[str],
        *,
        depth: int,
        detail: DetailLevel,
        privacy: PrivacyMode = "smart",
        included: set[str] | None = None,
    ) -> None:
        """Serialize a node and its children."""
        if not self._should_include_node(node, included, privacy):
            return

        # Add node header
        prefix = "#" * (depth + 1) + " "
        privacy_indicator = "🔒 " if node.is_private else ""

        match node.node_type:
            case NodeType.DIRECTORY:
                lines.append(f"{prefix}📁 {node.name}/")
            case NodeType.FILE:
                lines.append(f"{prefix}📄 {node.name}")
            case NodeType.CLASS:
                lines.append(f"{prefix}🔷 {privacy_indicator}{node.name}")
            case NodeType.FUNCTION | NodeType.METHOD:
                lines.append(f"{prefix}🔸 {privacy_indicator}{node.name}")
            case NodeType.VARIABLE:
                lines.append(f"{prefix}📎 {privacy_indicator}{node.name}")

        # Add details based on detail level
        if detail != DetailLevel.STRUCTURE:
            if node.signature:
                lines.append(f"```python\n{node.signature}\n```")

            if detail == DetailLevel.DOCSTRINGS and node.docstring:
                lines.append(f"```python\n{node.docstring}\n```")

            if detail == DetailLevel.FULL_CODE and node.content:
                lines.append(f"```python\n{node.content}\n```")

        # Process children
        if node.children:
            for child in sorted(
                node.children.values(),
                key=lambda n: (-n.importance, n.name),
            ):
                self._serialize_node_with_children(
                    child,
                    lines,
                    depth=depth + 1,
                    detail=detail,
                    privacy=privacy,
                    included=included,
                )
