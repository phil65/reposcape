"""Tests for Python AST analyzer."""

from __future__ import annotations

import pytest

from reposcape.analyzers import PythonAstAnalyzer
from reposcape.models import NodeType


def test_analyzer_can_handle_python_files():
    """Test file type detection."""
    analyzer = PythonAstAnalyzer()
    assert analyzer.can_handle("test.py")
    assert analyzer.can_handle("path/to/file.py")
    assert not analyzer.can_handle("test.js")
    assert not analyzer.can_handle("file.txt")


def test_analyze_simple_file(simple_python_file: str):
    """Test analysis of a simple Python file."""
    analyzer = PythonAstAnalyzer()
    nodes = analyzer.analyze_file("test.py", content=simple_python_file)

    assert len(nodes) == 1
    root = nodes[0]

    # Check file node
    assert root.node_type == NodeType.FILE
    assert root.name == "test.py"

    # Check children
    assert root.children is not None
    # SimpleClass, top_level_func, CONSTANT
    assert len(root.children) == 3  # noqa: PLR2004

    # Check class
    class_node = root.children["SimpleClass"]
    assert class_node.node_type == NodeType.CLASS
    assert class_node.docstring == """A simple class."""
    assert class_node.children is not None
    assert "method" in class_node.children

    # Check method
    method = class_node.children["method"]
    assert method.node_type == NodeType.METHOD
    assert method.docstring == """Do something."""
    assert method.signature is not None
    assert "arg: int" in method.signature
    assert "-> str" in method.signature

    # Check function
    func = root.children["top_level_func"]
    assert func.node_type == NodeType.FUNCTION
    assert func.docstring == """A top level function."""
    assert func.signature is not None
    assert "x: Any" in func.signature
    assert "-> bool" in func.signature


def test_analyze_async_functions():
    """Test analysis of async functions and methods."""
    content = '''
async def top_level_async():
    """Async function."""
    return 42

class AsyncClass:
    """Class with async method."""

    async def async_method(self):
        """Async method."""
        await top_level_async()
'''
    analyzer = PythonAstAnalyzer()
    nodes = analyzer.analyze_file("test.py", content=content)

    root = nodes[0]
    assert root.children is not None
    assert "top_level_async" in root.children
    assert root.children is not None
    assert root.children["top_level_async"].signature is not None
    assert root.children["top_level_async"].signature.startswith("async def")

    class_node = root.children["AsyncClass"]
    assert class_node.children is not None
    assert "async_method" in class_node.children
    assert class_node.children is not None
    assert class_node.children["async_method"].signature
    assert class_node.children["async_method"].signature.startswith("async def")


def test_reference_tracking(complex_python_file: str):
    """Test that references between symbols are tracked correctly."""
    analyzer = PythonAstAnalyzer()
    nodes = analyzer.analyze_file("test.py", content=complex_python_file)

    root = nodes[0]

    # Get references
    refs = root.references_to
    assert refs is not None

    # Convert to set of referenced names for easier testing
    ref_names = {ref.name for ref in refs}

    # Check that all expected references are found
    expected_refs = {
        "ABC",  # from base class
        "abstractmethod",
        "dataclass",
        "Generic",
        "TypeVar",
        "Config",  # used in Handler
        "BaseHandler",  # inherited by Handler
        "OtherClass",  # instantiated in Handler.handle
    }
    assert ref_names.issuperset(expected_refs)


def test_inheritance_handling(complex_python_file: str):
    """Test that class inheritance is correctly analyzed."""
    analyzer = PythonAstAnalyzer()
    nodes = analyzer.analyze_file("test.py", content=complex_python_file)

    root = nodes[0]
    assert root.children is not None
    handler = root.children["Handler"]
    assert handler.signature is not None
    assert "BaseHandler" in handler.signature
    assert "Generic[T]" in handler.signature


@pytest.mark.parametrize(
    "invalid_content",
    [
        "invalid python code",
        "def missing_parentheses:",
        "class MissingSyntax",
    ],
)
def test_invalid_python_handling(invalid_content: str):
    """Test analyzer's handling of invalid Python code."""
    analyzer = PythonAstAnalyzer()
    with pytest.raises(SyntaxError):
        analyzer.analyze_file("test.py", content=invalid_content)
