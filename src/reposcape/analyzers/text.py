"""Basic analyzer for text and markdown files."""

from __future__ import annotations

from typing import TYPE_CHECKING

from upath import UPath

from reposcape.analyzers.base import CodeAnalyzer
from reposcape.models.nodes import CodeNode, NodeType


if TYPE_CHECKING:
    from os import PathLike


class TextAnalyzer(CodeAnalyzer):
    """Basic analyzer for text files."""

    def can_handle(self, path: str | PathLike[str]) -> bool:
        """Check if file is a text file."""
        path = str(path).lower()
        return path.endswith((".txt", ".md", ".rst"))

    def analyze_file(
        self,
        path: str | PathLike[str],
        content: str | None = None,
    ) -> list[CodeNode]:
        """Analyze a text file."""
        path_obj = UPath(path)

        if content is None:
            content = path_obj.read_text(encoding="utf-8")

        # For markdown files, try to extract sections
        if path_obj.suffix.lower() == ".md":
            return self._analyze_markdown(path_obj, content)

        # For other text files, just return the content
        return [
            CodeNode(
                name=path_obj.name,
                node_type=NodeType.FILE,
                path=str(path),
                content=content,
                docstring=self._get_first_paragraph(content),
            )
        ]

    def _analyze_markdown(self, path: UPath, content: str) -> list[CodeNode]:
        """Extract structure from markdown file."""
        sections: dict[str, CodeNode] = {}
        current_section = None
        current_content = []

        for line in content.splitlines():
            # Check for headers
            if line.startswith("#"):
                # Store previous section if it exists
                if current_section:
                    sections[current_section] = CodeNode(
                        name=current_section,
                        node_type=NodeType.FUNCTION,  # Use FUNCTION for sections
                        path=f"{path}#{current_section}",
                        content="\n".join(current_content),
                        signature=current_section,
                    )

                # Start new section
                current_section = line.lstrip("#").strip()
                current_content = [line]
            else:
                current_content.append(line)

        # Add last section
        if current_section:
            sections[current_section] = CodeNode(
                name=current_section,
                node_type=NodeType.FUNCTION,
                path=f"{path}#{current_section}",
                content="\n".join(current_content),
                signature=current_section,
            )

        # Create file node with sections as children
        return [
            CodeNode(
                name=path.name,
                node_type=NodeType.FILE,
                path=str(path),
                content=content,
                docstring=self._get_first_paragraph(content),
                children=sections,
            )
        ]

    def _get_first_paragraph(self, content: str) -> str:
        """Extract first non-empty paragraph from text."""
        lines: list[str] = []
        for line in content.splitlines():
            line = line.strip()
            if not line and lines:
                break
            if line:
                lines.append(line)
        return " ".join(lines) if lines else ""
