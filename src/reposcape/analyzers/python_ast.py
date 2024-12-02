"""Python AST-based code analyzer."""

from __future__ import annotations

import ast
import dataclasses
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from upath import UPath

from reposcape.analyzers.base import CodeAnalyzer
from reposcape.models.nodes import CodeNode, NodeType, Reference


if TYPE_CHECKING:
    from os import PathLike


@dataclass
class SymbolCollector(ast.NodeVisitor):
    """Collect symbols and their references from Python AST."""

    path: str
    symbols: dict[str, CodeNode]
    references: list[Reference]

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:  # noqa: N802
        """Process class definitions."""
        # Add references from bases
        for base in node.bases:
            self._add_references_from_expr(base)

        # Add references from decorators
        for decorator in node.decorator_list:
            self._add_references_from_expr(decorator)

        # Create class node
        class_node = CodeNode(
            name=node.name,
            node_type=NodeType.CLASS,
            path=self.path,
            docstring=ast.get_docstring(node),
            signature=self._get_class_signature(node),
            children={},
        )

        # Process class body
        old_symbols = self.symbols
        self.symbols = {}
        self.generic_visit(node)

        # Add methods to class
        class_dict = dataclasses.asdict(class_node)
        class_dict["children"] = self.symbols
        class_node = CodeNode(**class_dict)

        self.symbols = old_symbols
        self.symbols[node.name] = class_node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:  # noqa: N802
        """Process function definitions."""
        # Add references from decorators
        for decorator in node.decorator_list:
            self._add_references_from_expr(decorator)

        # Add references from return annotation
        if node.returns:
            self._add_references_from_expr(node.returns)

        # Add references from argument annotations
        for arg in node.args.args:
            if arg.annotation:
                self._add_references_from_expr(arg.annotation)

        self.symbols[node.name] = CodeNode(
            name=node.name,
            node_type=NodeType.METHOD
            if isinstance(node.parent, ast.ClassDef)  # type: ignore[attr-defined]
            else NodeType.FUNCTION,
            path=self.path,
            docstring=ast.get_docstring(node),
            signature=self._get_function_signature(node),
        )
        self.generic_visit(node)

    def _add_references_from_expr(self, node: ast.expr) -> None:
        """Extract references from an expression node."""
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                self.references.append(
                    Reference(
                        name=child.id,
                        path=self.path,
                        line=child.lineno,
                        column=child.col_offset,
                    )
                )
            elif isinstance(child, ast.Attribute):
                self.references.append(
                    Reference(
                        name=child.attr,
                        path=self.path,
                        line=child.lineno,
                        column=child.col_offset,
                    )
                )

    def visit_Call(self, node: ast.Call) -> Any:  # noqa: N802
        """Process function/class calls."""
        self._add_references_from_expr(node.func)
        for arg in node.args:
            self._add_references_from_expr(arg)
        for kw in node.keywords:
            self._add_references_from_expr(kw.value)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:  # noqa: N802
        """Process from-imports to track references."""
        for alias in node.names:
            self.references.append(
                Reference(
                    name=alias.name,
                    path=self.path,
                    line=node.lineno,
                    column=node.col_offset,
                )
            )

    def visit_Import(self, node: ast.Import) -> Any:  # noqa: N802
        """Process imports to track references."""
        for alias in node.names:
            self.references.append(
                Reference(
                    name=alias.name,
                    path=self.path,
                    line=node.lineno,
                    column=node.col_offset,
                )
            )

    def visit_Assign(self, node: ast.Assign) -> Any:  # noqa: N802
        """Process assignments."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.symbols[target.id] = CodeNode(
                    name=target.id,
                    node_type=NodeType.VARIABLE,
                    path=self.path,
                    signature=f"{target.id} = {ast.unparse(node.value)}",
                )
        self._add_references_from_expr(node.value)
        self.generic_visit(node)

    def _get_function_signature(self, node: ast.FunctionDef) -> str:
        """Generate function signature."""
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {ast.unparse(arg.annotation)}"
            args.append(arg_str)

        returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
        return f"def {node.name}({', '.join(args)}){returns}"

    def _get_class_signature(self, node: ast.ClassDef) -> str:
        """Generate class signature."""
        bases = [ast.unparse(base) for base in node.bases]
        if bases:
            return f"class {node.name}({', '.join(bases)})"
        return f"class {node.name}"


class PythonAstAnalyzer(CodeAnalyzer):
    """Analyze Python code using the built-in ast module."""

    def can_handle(self, path: str | PathLike[str]) -> bool:
        """Check if file is a Python file."""
        return str(path).endswith(".py")

    def analyze_file(
        self,
        path: str | PathLike[str],
        content: str | None = None,
    ) -> list[CodeNode]:
        """Analyze a Python file."""
        path_obj = UPath(path)
        if content is None:
            content = path_obj.read_text(encoding="utf-8")
        # Parse the AST
        tree = ast.parse(content)
        ast.fix_missing_locations(tree)
        # Add parent links to AST nodes
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                child.parent = parent  # type: ignore[attr-defined]

        # Collect symbols
        collector = SymbolCollector(
            path=str(path),
            symbols={},
            references=[],
        )
        collector.visit(tree)
        # Create file node
        node = CodeNode(
            name=path_obj.name,
            node_type=NodeType.FILE,
            path=str(path),
            content=content,
            children=collector.symbols,
            references_to=collector.references,
        )
        return [node]