"""Base interfaces for code analysis."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from os import PathLike

    from reposcape.models import CodeNode


class CodeAnalyzer(ABC):
    """Abstract base class for code analysis."""

    def _is_private(self, name: str) -> bool:
        """Check if a name represents a private element."""
        return name.startswith("_") and not name.endswith("_")

    @abstractmethod
    def can_handle(self, path: str | PathLike[str]) -> bool:
        """Check if this analyzer can handle the given file."""

    @abstractmethod
    def analyze_file(
        self, path: str | PathLike[str], content: str | None = None
    ) -> list[CodeNode]:
        """Analyze a single file and return its nodes.

        Args:
            path: Path to the file
            content: File content if already loaded, otherwise read from path

        Returns:
            List of CodeNode objects representing the file structure
        """
