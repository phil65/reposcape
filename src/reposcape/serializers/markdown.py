"""Markdown serialization of code structure."""

from __future__ import annotations

from reposcape.models.nodes import CodeNode, NodeType
from reposcape.models.options import DetailLevel
from reposcape.serializers.base import (
    HIGH_IMPORTANCE_THRESHOLD,
    LOW_IMPORTANCE_THRESHOLD,
    CodeSerializer,
)


class MarkdownSerializer(CodeSerializer):
    """Serialize code structure to Markdown format."""

    def serialize(
        self,
        root: CodeNode,
        *,
        detail: DetailLevel,
        max_depth: int | None = None,
        token_limit: int | None = None,
    ) -> str:
        """Convert structure to markdown."""
        lines: list[str] = []
        self._serialize_node(
            root,
            lines,
            depth=0,
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
        depth: int,
        detail: DetailLevel,
        max_depth: int | None,
        remaining_tokens: int | None,
    ) -> int:
        """Serialize a single node and its children."""
        if not self._should_include_node(node, depth, max_depth):
            return 0

        tokens_used = 0

        # Calculate prefix
        prefix = "#" * (depth + 1) + " "

        # Add node header based on type
        match node.node_type:
            case NodeType.DIRECTORY:
                header = f"{prefix}📁 {node.name}/"
            case NodeType.FILE:
                header = f"{prefix}📄 {node.name}"
            case NodeType.CLASS:
                header = f"{prefix}🔷 {node.name}"
            case NodeType.FUNCTION | NodeType.METHOD:
                header = f"{prefix}🔸 {node.name}"
            case NodeType.VARIABLE:
                header = f"{prefix}📎 {node.name}"
            case _:
                header = f"{prefix}{node.name}"

        lines.append(header)
        tokens_used += self._estimate_tokens(header)

        # Process node children
        if node.node_type == NodeType.DIRECTORY:
            # For directories, just process child nodes
            if node.children:
                for child in sorted(
                    node.children.values(), key=lambda n: (-n.importance, n.name)
                ):
                    child_tokens = self._serialize_node(
                        child,
                        lines,
                        depth=depth + 1,
                        detail=detail,
                        max_depth=max_depth,
                        remaining_tokens=remaining_tokens,
                    )
                    tokens_used += child_tokens
                    if remaining_tokens is not None:
                        remaining_tokens -= child_tokens
                        if remaining_tokens <= 0:
                            break
        # For files and other nodes, show content based on detail level
        elif detail != DetailLevel.STRUCTURE:
            details = []

            # For files, process their children (functions, classes)
            if node.node_type == NodeType.FILE and node.children:
                for child in sorted(
                    node.children.values(), key=lambda n: (-n.importance, n.name)
                ):
                    child_header = f"{prefix}# {child.name}"
                    lines.append(child_header)
                    tokens_used += self._estimate_tokens(child_header)

                    if child.signature:
                        child_content = f"```python\n{child.signature}\n```"
                        lines.append(child_content)
                        tokens_used += self._estimate_tokens(child_content)

            # Add own signature/content
            if node.signature:
                details.append(f"```python\n{node.signature}\n```")

            if detail == DetailLevel.DOCSTRINGS and node.docstring:
                details.append(f"```python\n{node.docstring}\n```")

            if detail == DetailLevel.FULL_CODE and node.content:
                details.append(f"```python\n{node.content}\n```")

            if details:
                detail_text = "\n".join(details)
                if remaining_tokens is None or remaining_tokens >= self._estimate_tokens(
                    detail_text
                ):
                    lines.append(detail_text)
                    tokens_used += self._estimate_tokens(detail_text)

        return tokens_used

    def _should_include_node(
        self,
        node: CodeNode,
        current_depth: int,
        max_depth: int | None,
    ) -> bool:
        """Check if node should be included based on depth and importance."""
        if max_depth is not None and current_depth > max_depth:
            return False

        # Always include directories and files
        if node.node_type in (NodeType.DIRECTORY, NodeType.FILE):
            return True

        # Always include high importance nodes
        if node.importance > HIGH_IMPORTANCE_THRESHOLD:
            return True

        # Skip low importance nodes at deeper levels
        return not (current_depth > 2 and node.importance < LOW_IMPORTANCE_THRESHOLD)  # noqa: PLR2004
