"""Tests for the functional interface."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from upath import UPath

from reposcape import get_focused_view, get_repo_overview


if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def sample_repo(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary repository with sample files."""
    # Create a simple Python package
    pkg_dir = tmp_path / "mypackage"
    pkg_dir.mkdir()

    # Create __init__.py
    init_content = '''"""Sample package."""

def greet(name: str) -> str:
    """Return a greeting."""
    return f"Hello {name}!"
'''
    (pkg_dir / "__init__.py").write_text(init_content)

    # Create utils.py
    utils_content = '''"""Utility functions."""

class Helper:
    """Helper class."""

    def __init__(self, prefix: str = ""):
        """Initialize with prefix."""
        self.prefix = prefix

    def format(self, text: str) -> str:
        """Format text with prefix."""
        return f"{self.prefix}{text}"
'''
    (pkg_dir / "utils.py").write_text(utils_content)

    # Change to the tmp directory for consistent paths
    cwd = Path.cwd()
    os.chdir(tmp_path)
    yield pkg_dir
    os.chdir(cwd)


def test_get_repo_overview(sample_repo: Path) -> None:
    """Test getting repository overview."""
    result = get_repo_overview(
        sample_repo.parent,  # Use parent dir containing mypackage/
        output_format="compact",
        detail="signatures",
    )

    # Check basic structure is present
    assert result.strip().split("\n") == [
        sample_repo.parent.name + "/",
        "  mypackage/",
        "    __init__.py",
        "      def greet(name: str) -> str",
        "    utils.py",
        "      class Helper",
        "        def __init__(self, prefix: str)",
        "        def format(self, text: str) -> str",
    ]


def test_get_focused_view(sample_repo: Path) -> None:
    """Test getting focused view of specific files."""
    repo_root = UPath(sample_repo.parent)
    target_file = repo_root / "mypackage" / "utils.py"

    result = get_focused_view(
        files=[target_file],
        repo_path=repo_root,
        output_format="compact",
        detail="signatures",
    )

    lines = result.strip().split("\n")

    # Verify structure and content
    assert lines[0] == f"{sample_repo.parent.name}/"  # Root
    assert "  mypackage/" in lines
    assert "utils.py" in result
    assert "class Helper" in result
    assert "def __init__(self, prefix: str)" in result
    assert "def format(self, text: str) -> str" in result

    # TODO: Currently we show all files in the package.
    # In the future, we might want to filter out unrelated files.
    # assert "__init__.py" not in result
    # assert "def greet" not in result


def test_get_focused_view_with_dependencies(sample_repo: Path) -> None:
    """Test focused view with dependencies."""
    # Add a file that depends on utils.py
    app_content = '''"""Main application."""
from .utils import Helper

def main():
    """Run the app."""
    helper = Helper(">>")
    return helper.format("Hello")
'''
    (sample_repo / "app.py").write_text(app_content)

    repo_root = UPath(sample_repo.parent)
    target_file = repo_root / "mypackage" / "app.py"

    result = get_focused_view(
        files=[target_file],
        repo_path=repo_root,
        output_format="compact",
        detail="signatures",
    )

    # Should include both app.py and its dependency utils.py
    assert "app.py" in result
    assert "def main()" in result
    assert "utils.py" in result
    assert "class Helper" in result


if __name__ == "__main__":
    pytest.main(["-vv", __file__])
