# RepoScape

[![PyPI License](https://img.shields.io/pypi/l/reposcape.svg)](https://pypi.org/project/reposcape/)
[![Package status](https://img.shields.io/pypi/status/reposcape.svg)](https://pypi.org/project/reposcape/)
[![Daily downloads](https://img.shields.io/pypi/dd/reposcape.svg)](https://pypi.org/project/reposcape/)
[![Weekly downloads](https://img.shields.io/pypi/dw/reposcape.svg)](https://pypi.org/project/reposcape/)
[![Monthly downloads](https://img.shields.io/pypi/dm/reposcape.svg)](https://pypi.org/project/reposcape/)
[![Distribution format](https://img.shields.io/pypi/format/reposcape.svg)](https://pypi.org/project/reposcape/)
[![Wheel availability](https://img.shields.io/pypi/wheel/reposcape.svg)](https://pypi.org/project/reposcape/)
[![Python version](https://img.shields.io/pypi/pyversions/reposcape.svg)](https://pypi.org/project/reposcape/)
[![Implementation](https://img.shields.io/pypi/implementation/reposcape.svg)](https://pypi.org/project/reposcape/)
[![Releases](https://img.shields.io/github/downloads/phil65/reposcape/total.svg)](https://github.com/phil65/reposcape/releases)
[![Github Contributors](https://img.shields.io/github/contributors/phil65/reposcape)](https://github.com/phil65/reposcape/graphs/contributors)
[![Github Discussions](https://img.shields.io/github/discussions/phil65/reposcape)](https://github.com/phil65/reposcape/discussions)
[![Github Forks](https://img.shields.io/github/forks/phil65/reposcape)](https://github.com/phil65/reposcape/forks)
[![Github Issues](https://img.shields.io/github/issues/phil65/reposcape)](https://github.com/phil65/reposcape/issues)
[![Github Issues](https://img.shields.io/github/issues-pr/phil65/reposcape)](https://github.com/phil65/reposcape/pulls)
[![Github Watchers](https://img.shields.io/github/watchers/phil65/reposcape)](https://github.com/phil65/reposcape/watchers)
[![Github Stars](https://img.shields.io/github/stars/phil65/reposcape)](https://github.com/phil65/reposcape/stars)
[![Github Repository size](https://img.shields.io/github/repo-size/phil65/reposcape)](https://github.com/phil65/reposcape)
[![Github last commit](https://img.shields.io/github/last-commit/phil65/reposcape)](https://github.com/phil65/reposcape/commits)
[![Github release date](https://img.shields.io/github/release-date/phil65/reposcape)](https://github.com/phil65/reposcape/releases)
[![Github language count](https://img.shields.io/github/languages/count/phil65/reposcape)](https://github.com/phil65/reposcape)
[![Github commits this week](https://img.shields.io/github/commit-activity/w/phil65/reposcape)](https://github.com/phil65/reposcape)
[![Github commits this month](https://img.shields.io/github/commit-activity/m/phil65/reposcape)](https://github.com/phil65/reposcape)
[![Github commits this year](https://img.shields.io/github/commit-activity/y/phil65/reposcape)](https://github.com/phil65/reposcape)
[![Package status](https://codecov.io/gh/phil65/reposcape/branch/main/graph/badge.svg)](https://codecov.io/gh/phil65/reposcape/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PyUp](https://pyup.io/repos/github/phil65/reposcape/shield.svg)](https://pyup.io/repos/github/phil65/reposcape/)

[Read the documentation!](https://phil65.github.io/reposcape/)

# RepoScape

RepoScape is a Python library for mapping and analyzing repository structures with a focus on understanding code dependencies and importance. It parses code files, builds a graph representation, and helps identify important components through various scoring algorithms.

## Installation

```bash
pip install reposcape
```

Requires Python 3.12 or higher.

## Quick Start

```python
from reposcape import RepoMapper, DetailLevel

# Create mapper with default settings
mapper = RepoMapper()

# Generate overview of entire repository
overview = mapper.create_overview(
    repo_path="path/to/repo",
    detail=DetailLevel.SIGNATURES,
    token_limit=2000  # Optional token limit for output
)

# Generate focused view of specific files
focused = mapper.create_focused_view(
    files=["main.py", "utils.py"],
    repo_path="path/to/repo",
    detail=DetailLevel.DOCSTRINGS
)
```

## Core Components

### RepoMapper

The main entry point for repository analysis. Configurable with custom analyzers, scorers, and serializers.

```python
class RepoMapper:
    def __init__(
        self,
        *,
        analyzers: Sequence[CodeAnalyzer] | None = None,
        scorer: GraphScorer | None = None,
        serializer: CodeSerializer | None = None,
    ): ...

    def create_overview(
        self,
        repo_path: str | PathLike[str],
        *,
        token_limit: int | None = None,
        detail: DetailLevel = DetailLevel.SIGNATURES,
        exclude_patterns: list[str] | None = None,
    ) -> str: ...

    def create_focused_view(
        self,
        files: Sequence[str | PathLike[str]],
        repo_path: str | PathLike[str],
        *,
        token_limit: int | None = None,
        detail: DetailLevel = DetailLevel.SIGNATURES,
        exclude_patterns: list[str] | None = None,
    ) -> str: ...
```

### Detail Levels

Control how much information is included in the output:

```python
class DetailLevel(Enum):
    STRUCTURE   # Just names and hierarchy
    SIGNATURES  # Include function/class signatures
    DOCSTRINGS  # Include signatures + docstrings
    FULL_CODE   # Include complete implementations
```

## Code Analysis

RepoScape includes analyzers for different file types:

### PythonAstAnalyzer

Analyzes Python files using AST parsing:
- Extracts classes, functions, methods, variables
- Tracks references between symbols
- Collects docstrings and signatures

```python
analyzer = PythonAstAnalyzer()
nodes = analyzer.analyze_file("main.py")
```

### TextAnalyzer

Basic analyzer for text files:
- Handles .txt, .md, .rst files
- Extracts sections from markdown files
- Preserves file content and first paragraph as docstring

## Importance Scoring

RepoScape offers different algorithms for calculating code importance:

### ReferenceScorer

Simple reference-based scoring that considers:
- Number of incoming references (highest weight)
- Number of outgoing references (medium weight)
- Being referenced by important files (high boost)
- Distance from important files (decreasing boost)

```python
from reposcape.importance import ReferenceScorer

scorer = ReferenceScorer(
    ref_weight=1.0,
    outref_weight=0.5,
    important_ref_boost=2.0,
    distance_decay=0.5,
)
```

### PageRankScorer

Uses the PageRank algorithm to score nodes based on the graph structure:
- Considers connection patterns
- Handles cycles in dependencies
- Supports personalization for focused analysis

```python
from reposcape.importance import PageRankScorer

scorer = PageRankScorer()
```

## Output Serialization

Multiple serializers are available for different output formats:

### MarkdownSerializer

Generates detailed markdown with:
- Hierarchical structure using headers
- Code blocks for signatures/implementations
- Emojis for different node types
- Optional details based on importance scores

### CompactSerializer

Produces a compact, indented format:
- Single line per node
- Indentation shows hierarchy
- Abbreviated signatures
- Good for quick overviews

### TreeSerializer

ASCII tree-style output:
- Uses box-drawing characters
- Shows clear parent-child relationships
- Similar to `tree` command output

Example usage:

```python
from reposcape.serializers import MarkdownSerializer, CompactSerializer, TreeSerializer

# Create mapper with specific serializer
mapper = RepoMapper(serializer=TreeSerializer())
```

## Advanced Usage

### Custom Analyzers

Implement `CodeAnalyzer` for custom file analysis:

```python
class CustomAnalyzer(CodeAnalyzer):
    def can_handle(self, path: str | PathLike[str]) -> bool:
        return path.endswith(".custom")

    def analyze_file(
        self,
        path: str | PathLike[str],
        content: str | None = None
    ) -> list[CodeNode]: ...
```

### Focused Analysis

Analyze specific files and their relationships:

```python
mapper = RepoMapper()

# Focus on specific files
focused_view = mapper.create_focused_view(
    files=["src/core.py", "src/utils.py"],
    repo_path=".",
    detail=DetailLevel.DOCSTRINGS,
    exclude_patterns=["**/test_*.py", "**/__pycache__/*"]
)
```

### Token Limits

Control output size for large repositories:

```python
# Limit output to approximately 2000 tokens
overview = mapper.create_overview(
    repo_path=".",
    token_limit=2000,
    detail=DetailLevel.SIGNATURES
)
```

## Models

### CodeNode

Immutable representation of code elements:

```python
@dataclass(frozen=True)
class CodeNode:
    name: str
    node_type: NodeType
    path: str
    content: str | None = None
    docstring: str | None = None
    signature: str | None = None
    children: Mapping[str, CodeNode] | None = None
    references_to: Sequence[Reference] | None = None
    referenced_by: Sequence[Reference] | None = None
    importance: float = 0.0
```

### NodeType

Available node types:
- DIRECTORY
- FILE
- CLASS
- FUNCTION
- METHOD
- VARIABLE

### Reference

Tracks symbol references:

```python
@dataclass(frozen=True)
class Reference:
    name: str
    path: str
    line: int
    column: int
```
