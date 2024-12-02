"""Node models representing code structure elements."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


class NodeType(Enum):
    """Type of node in the repository structure."""

    DIRECTORY = auto()
    FILE = auto()
    CLASS = auto()
    FUNCTION = auto()
    ASYNC_FUNCTION = auto()
    METHOD = auto()
    VARIABLE = auto()
    ASYNC_METHOD = auto()


@dataclass(frozen=True)
class Reference:
    """Represents a reference to a symbol."""

    name: str
    path: str  # Path to the file containing the reference
    line: int
    column: int
    module_reference: bool = False
    source: CodeNode | None = None


@dataclass(frozen=True)
class CodeNode:
    """Immutable representation of a code element."""

    name: str
    node_type: NodeType
    path: str  # Relative to repo root
    content: str | None = None
    docstring: str | None = None
    signature: str | None = None
    children: Mapping[str, CodeNode] | None = None
    # New fields for importance calculation
    references_to: Sequence[Reference] | None = None  # Symbols this node references
    referenced_by: Sequence[Reference] | None = None  # References to this node
    importance: float = 0.0
    is_private: bool = False
    parent: CodeNode | None = None

    def __post_init__(self):
        """Initialize empty collections if None."""
        if self.children is None:
            object.__setattr__(self, "children", {})
        if self.references_to is None:
            object.__setattr__(self, "references_to", [])
        if self.referenced_by is None:
            object.__setattr__(self, "referenced_by", [])
