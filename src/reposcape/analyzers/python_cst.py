"""Python code analyzer using LibCST."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import libcst as cst
from libcst.metadata import ParentNodeProvider, PositionProvider

from reposcape.models.nodes import CodeNode, NodeType, Reference


if TYPE_CHECKING:
    from os import PathLike

from .base import CodeAnalyzer


@dataclass
class SymbolCollector(cst.CSTVisitor):
    """Collect symbols and their references using LibCST."""

    path: str
    symbols: dict[str, CodeNode]
    references: list[Reference]

    def __init__(self, path: str) -> None:
        super().__init__()
        self.path = path
        self.symbols = {}
        self.references = []

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        """Process class definitions."""
        # Get position info
        pos = self.get_metadata(PositionProvider, node)

        # Create class node
        class_node = CodeNode(
            name=node.name.value,
            node_type=NodeType.CLASS,
            path=self.path,
            docstring=self._get_docstring(node),
            signature=self._get_class_signature(node),
            children={},
        )

        # Store current symbols to process class body
        old_symbols = self.symbols
        self.symbols = {}

        # Process class body
        self.generic_visit(node)

        # Update class with its methods
        class_node = CodeNode(**{
            **dataclasses.asdict(class_node),
            "children": self.symbols,
        })

        # Restore old symbols and add class
        self.symbols = old_symbols
        self.symbols[node.name.value] = class_node

        return False  # Don't process children again

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        """Process function definitions."""
        pos = self.get_metadata(PositionProvider, node)

        # Determine if this is a method
        is_method = any(
            isinstance(ancestor, cst.ClassDef)
            for ancestor in self.get_metadata(ParentNodeProvider, node)
        )

        self.symbols[node.name.value] = CodeNode(
            name=node.name.value,
            node_type=NodeType.METHOD if is_method else NodeType.FUNCTION,
            path=self.path,
            docstring=self._get_docstring(node),
            signature=self._get_function_signature(node),
        )

        return True  # Process function body for references

    def visit_Name(self, node: cst.Name) -> bool:
        """Process name references."""
        pos = self.get_metadata(PositionProvider, node)

        # Only add reference if name is being used, not defined
        if isinstance(node.parent, (cst.FunctionDef, cst.ClassDef)):
            return True

        self.references.append(
            Reference(
                name=node.value,
                path=self.path,
                line=pos.start.line,
                column=pos.start.column,
            )
        )
        return True

    def _get_docstring(self, node: cst.CSTNode) -> str | None:
        """Extract docstring from node."""
        for child in node.body.body:
            if isinstance(child, cst.SimpleStatementLine):
                if isinstance(child.body[0], cst.Expr):
                    if isinstance(child.body[0].value, cst.SimpleString):
                        return child.body[0].value.evaluated_value
        return None

    def _get_function_signature(self, node: cst.FunctionDef) -> str:
        """Generate function signature."""
        return node.code

    def _get_class_signature(self, node: cst.ClassDef) -> str:
        """Generate class signature."""
        return f"class {node.name.value}"


class PythonCSTAnalyzer(CodeAnalyzer):
    """Analyze Python code using LibCST."""

    def can_handle(self, path: str | PathLike[str]) -> bool:
        """Check if file is a Python file."""
        return str(path).endswith(".py")

    def analyze_file(
        self,
        path: str | PathLike[str],
        content: str | None = None,
    ) -> list[CodeNode]:
        """Analyze a Python file using LibCST."""
        if content is None:
            content = UPath(path).read_text(encoding="utf-8")

        # Parse the code
        module = cst.parse_module(content)

        # Create wrapper with required metadata
        wrapper = cst.metadata.MetadataWrapper(
            module, cache={}, providers={PositionProvider, ParentNodeProvider}
        )

        # Collect symbols
        collector = SymbolCollector(str(path))
        wrapper.visit(collector)

        # Create file node
        return [
            CodeNode(
                name=UPath(path).name,
                node_type=NodeType.FILE,
                path=str(path),
                content=content,
                children=collector.symbols,
                references_to=collector.references,
            )
        ]
