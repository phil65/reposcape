"""Tests for RepoMapper functionality."""

from __future__ import annotations

from pathlib import Path

import pytest

from reposcape.mapper import RepoMapper
from reposcape.models import DetailLevel


# Test repository content
MAIN_PY = """\"\"\"Main module.\"\"\"
from .utils import helper

def main() -> None:
    \"\"\"Main function.\"\"\"
    result = helper()
    print(result)

if __name__ == "__main__":
    main()
"""

UTILS_PY = """\"\"\"Utility functions.\"\"\"

def helper() -> str:
    \"\"\"Help with something.\"\"\"
    return "Hello!"
"""

TEST_MAIN_PY = """\"\"\"Tests for main module.\"\"\"
from project.main import main

def test_main() -> None:
    \"\"\"Test main function.\"\"\"
    main()  # Should print Hello!
"""

SETUP_PY = """from setuptools import setup

setup(
    name="project",
    version="0.1.0",
)
"""

README_MD = """# Project

A test project.
"""

INVALID_PY = "this is not valid python"


@pytest.fixture
def temp_repo(tmp_path: Path) -> Path:
    """Create a temporary repository structure for testing."""
    repo = Path(tmp_path)

    # Create directory structure first
    src = repo / "src" / "project"
    tests = repo / "tests"
    src.mkdir(parents=True)
    tests.mkdir(exist_ok=True)

    # Create files with explicit encoding and debug output
    def write_file(path: Path, content: str) -> None:
        path.write_text(content.strip(), encoding="utf-8")

    # Create all files
    write_file(src / "__init__.py", "")
    write_file(src / "main.py", MAIN_PY)
    write_file(src / "utils.py", UTILS_PY)
    write_file(tests / "test_main.py", TEST_MAIN_PY)
    write_file(repo / "setup.py", SETUP_PY)
    write_file(repo / "README.md", README_MD)

    # Verify files exist
    for path in [
        src / "main.py",
        src / "utils.py",
        tests / "test_main.py",
        repo / "README.md",
        repo / "setup.py",
    ]:
        assert path.exists(), f"File not created: {path}"

    return repo


def test_create_overview(temp_repo: Path):
    """Test creating repository overview."""
    mapper = RepoMapper()
    result = mapper.create_overview(temp_repo, detail=DetailLevel.SIGNATURES)

    # Basic structure checks
    assert "📁 src" in result
    assert "main.py" in result
    assert "def main()" in result


def test_create_focused_view(temp_repo: Path):
    """Test creating focused view of specific files."""
    mapper = RepoMapper()

    # Focus on main.py
    result = mapper.create_focused_view(
        files=[temp_repo / "src" / "project" / "main.py"],
        repo_path=temp_repo,
        detail=DetailLevel.SIGNATURES,
    )

    # Should prioritize main.py and related files
    assert "main.py" in result
    assert "utils.py" in result  # Referenced by main.py
    assert "test_main.py" in result  # References main.py

    # Check importance ranking
    # Main file should appear before tests
    main_pos = result.find("main.py")
    test_pos = result.find("test_main.py")
    assert main_pos < test_pos


def test_exclude_patterns(temp_repo: Path):
    """Test excluding files using patterns."""
    mapper = RepoMapper()
    result = mapper.create_overview(
        temp_repo,
        exclude_patterns=["**/test_*.py", "setup.py"],
    )

    assert "test_main.py" not in result
    assert "setup.py" not in result
    assert "main.py" in result


def test_token_limit(temp_repo: Path):
    """Test respecting token limit."""
    mapper = RepoMapper()

    # Request extremely low token limit to force minimal output
    result = mapper.create_overview(
        temp_repo,
        token_limit=50,  # Even more restrictive
        detail=DetailLevel.STRUCTURE,  # Only show structure to minimize tokens
    )
    lines = result.splitlines()
    # Should only show top-level structure
    assert len(lines) < 10  # noqa: PLR2004


def test_detail_levels(temp_repo: Path):
    """Test different detail levels."""
    mapper = RepoMapper()

    # Structure only
    structure = mapper.create_overview(
        temp_repo,
        detail=DetailLevel.STRUCTURE,
    )
    assert "def main()" not in structure

    # Signatures
    signatures = mapper.create_overview(
        temp_repo,
        detail=DetailLevel.SIGNATURES,
    )
    assert "def main()" in signatures
    assert "print(result)" not in signatures

    # Full code
    full = mapper.create_overview(
        temp_repo,
        detail=DetailLevel.FULL_CODE,
    )
    assert "def main()" in full
    assert "print(result)" in full


def test_error_handling(temp_repo: Path):
    """Test handling of invalid files."""
    # Create an invalid Python file
    (temp_repo / "invalid.py").write_text(INVALID_PY)

    mapper = RepoMapper()
    with pytest.warns(RuntimeWarning):
        result = mapper.create_overview(temp_repo)

    # Should skip invalid file but include valid ones
    assert "invalid.py" not in result
    assert "main.py" in result
