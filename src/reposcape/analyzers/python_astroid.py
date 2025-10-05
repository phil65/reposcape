from __future__ import annotations

from typing import TYPE_CHECKING

import astroid
from astroid import nodes

from reposcape.models.nodes import CodeNode, NodeType, Reference


if TYPE_CHECKING:
    from os import PathLike

from .base import CodeAnalyzer


class SymbolCollector:
    """Collect symbols and their references using astroid."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.symbols: dict[str, CodeNode] = {}
        self.references: list[Reference] = []

    def visit(self, node: nodes.NodeNG) -> None:
        """Visit a node."""
        method = getattr(self, f"visit_{node.__class__.__name__}", None)
        if method:
            method(node)

        # Visit children
        for child in node.get_children():
            self.visit(child)

    def visit_ClassDef(self, node: nodes.ClassDef) -> None:
        """Process class definitions."""
        # Add references from bases
        for base in node.bases:
            self._add_references_from_expr(base)

        class_node = CodeNode(
            name=node.name,
            node_type=NodeType.CLASS,
            path=self.path,
            docstring=node.doc_node.value if node.doc_node else None,
            signature=f"class {node.name}",
            children={},
        )

        # Process class body
        old_symbols = self.symbols
        self.symbols = {}
        for child in node.get_children():
            self.visit(child)

        class_node = CodeNode(
            **{**dataclasses.asdict(class_node), "children": self.symbols}
        )

        self.symbols = old_symbols
        self.symbols[node.name] = class_node

    def visit_FunctionDef(self, node: nodes.FunctionDef) -> None:
        """Process function definitions."""
        # astroid provides direct parent access
        is_method = isinstance(node.parent, nodes.ClassDef)

        self.symbols[node.name] = CodeNode(
            name=node.name,
            node_type=NodeType.METHOD if is_method else NodeType.FUNCTION,
            path=self.path,
            docstring=node.doc_node.value if node.doc_node else None,
            signature=self._get_function_signature(node),
        )

    def visit_Name(self, node: nodes.Name) -> None:
        """Process name references."""
        if node.ctx == "Load":  # Only track usage, not definitions
            self.references.append(
                Reference(
                    name=node.name,
                    path=self.path,
                    line=node.lineno,
                    column=node.col_offset,
                )
            )

    def _add_references_from_expr(self, node: nodes.NodeNG) -> None:
        """Extract references from an expression node."""
        for child_node in node.nodes_of_class(nodes.Name):
            self.references.append(
                Reference(
                    name=child_node.name,
                    path=self.path,
                    line=child_node.lineno,
                    column=child_node.col_offset,
                )
            )

    def _get_function_signature(self, node: nodes.FunctionDef) -> str:
        """Generate function signature."""
        args = []
        for arg in node.args.args:
            arg_str = arg.name
            if arg.annotation:
                arg_str += f": {arg.annotation.as_string()}"
            args.append(arg_str)

        returns = f" -> {node.returns.as_string()}" if node.returns else ""
        return f"def {node.name}({', '.join(args)}){returns}"

class PythonAstroidAnalyzer(CodeAnalyzer):
    """Analyze Python code using astroid."""

    def __init__(self) -> None:
        """Initialize with astroid manager for caching."""
        self.manager = astroid.MANAGER

    def can_handle(self, path: str | PathLike[str]) -> bool:
        """Check if file is a Python file."""
        return str(path).endswith(".py")

    def analyze_file(
        self,
        path: str | PathLike[str],
        content: str | None = None,
    ) -> list[CodeNode]:
        """Analyze a Python file using astroid."""
        path_str = str(path)

        if content is not None:
            # Use provided content
            module = self.manager.ast_from_string(content, path_str)
        else:
            # Let astroid handle file reading (includes caching)
            module = self.manager.ast_from_file(path_str)

        collector = SymbolCollector(path_str)
        collector.visit(module)

        return [CodeNode(
            name=module.name,
            node_type=NodeType.FILE,
            path=path_str,
            content=content or module.file_bytes.decode("utf-8"),
            children=collector.symbols,
            references_to=collector.references,
        )]
