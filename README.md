# RepoScape

[![PyPI License](https://img.shields.io/pypi/l/reposcape.svg)](https://pypi.org/project/reposcape/)
[![Package status](https://img.shields.io/pypi/status/reposcape.svg)](https://pypi.org/project/reposcape/)
[![Monthly downloads](https://img.shields.io/pypi/dm/reposcape.svg)](https://pypi.org/project/reposcape/)
[![Distribution format](https://img.shields.io/pypi/format/reposcape.svg)](https://pypi.org/project/reposcape/)
[![Wheel availability](https://img.shields.io/pypi/wheel/reposcape.svg)](https://pypi.org/project/reposcape/)
[![Python version](https://img.shields.io/pypi/pyversions/reposcape.svg)](https://pypi.org/project/reposcape/)
[![Implementation](https://img.shields.io/pypi/implementation/reposcape.svg)](https://pypi.org/project/reposcape/)
[![Releases](https://img.shields.io/github/downloads/phil65/reposcape/total.svg)](https://github.com/phil65/reposcape/releases)
[![Github Contributors](https://img.shields.io/github/contributors/phil65/reposcape)](https://github.com/phil65/reposcape/graphs/contributors)
[![Github Forks](https://img.shields.io/github/forks/phil65/reposcape)](https://github.com/phil65/reposcape/forks)
[![Github Issues](https://img.shields.io/github/issues/phil65/reposcape)](https://github.com/phil65/reposcape/issues)
[![Github Issues](https://img.shields.io/github/issues-pr/phil65/reposcape)](https://github.com/phil65/reposcape/pulls)
[![Github Watchers](https://img.shields.io/github/watchers/phil65/reposcape)](https://github.com/phil65/reposcape/watchers)
[![Github Stars](https://img.shields.io/github/stars/phil65/reposcape)](https://github.com/phil65/reposcape/stars)
[![Github Repository size](https://img.shields.io/github/repo-size/phil65/reposcape)](https://github.com/phil65/reposcape)
[![Github last commit](https://img.shields.io/github/last-commit/phil65/reposcape)](https://github.com/phil65/reposcape/commits)
[![Github release date](https://img.shields.io/github/release-date/phil65/reposcape)](https://github.com/phil65/reposcape/releases)
[![Github language count](https://img.shields.io/github/languages/count/phil65/reposcape)](https://github.com/phil65/reposcape)
[![Github commits this month](https://img.shields.io/github/commit-activity/m/phil65/reposcape)](https://github.com/phil65/reposcape)
[![Package status](https://codecov.io/gh/phil65/reposcape/branch/main/graph/badge.svg)](https://codecov.io/gh/phil65/reposcape/)
[![PyUp](https://pyup.io/repos/github/phil65/reposcape/shield.svg)](https://pyup.io/repos/github/phil65/reposcape/)

[Read the documentation!](https://phil65.github.io/reposcape/)

RepoScape builds compact, importance-ranked maps of a code base for use as LLM context.
It parses a repository (or an imported Python package), builds a reference graph between
symbols, scores every element and serializes the most relevant parts as Markdown, a compact
outline or an ASCII tree, optionally within a token budget.

## Installation

```bash
pip install reposcape
```

Requires Python 3.13 or newer. Optional extras: `reposcape[stubgen]` (mypy, for stub
generation), `reposcape[astroid]` and `reposcape[libcst]` (experimental analyzers).

## Quick start

```python
from reposcape import get_focused_view, get_repo_overview

# Overview of a repository as an ASCII tree
print(get_repo_overview("path/to/repo", output_format="tree", detail="structure"))

# Signatures of the most important elements, limited to ~2000 tokens
print(get_repo_overview("path/to/repo", detail="signatures", token_limit=2000))

# Focus on some files and what they reference
print(get_focused_view(["src/core.py"], "path/to/repo", detail="docstrings"))
```

`repo_path` can also be an imported module or package, which is analyzed via its source:

```python
import json

from reposcape import get_repo_overview

print(get_repo_overview(json, output_format="compact"))
```

## Features

- **Analyzers**: `PythonAstAnalyzer` (classes, functions, methods, variables, references,
  signatures, docstrings) and `TextAnalyzer` (`.txt`, `.md`, `.rst`; Markdown sections).
- **Importance scoring**: `ReferenceScorer` (incoming/outgoing references, proximity to
  focused files; default) and `PageRankScorer` (networkx PageRank).
- **Serializers**: `"markdown"`, `"compact"` and `"tree"` output formats.
- **Detail levels**: `structure`, `signatures`, `docstrings`, `full`.
- **Privacy modes**: `"public_only"`, `"all"` or `"smart"` (private members only when documented,
  important or referenced from public code).
- **Aider-style repo map**: `AiderRepoMap` uses tree-sitter tag queries for many languages and
  ranks definitions with PageRank.
- **AST-aware grep**: `grep()` / `grep_simple()` show matches with their enclosing scopes.
- **Stub generation**: `generate_stub_from_source()` and friends wrap mypy's stubgen.
- Paths go through [universal-pathlib](https://github.com/fsspec/universal_pathlib), so
  fsspec file systems work too.

## Using `RepoMapper` directly

```python
from reposcape import DetailLevel, RepoMapper
from reposcape.importance import PageRankScorer

mapper = RepoMapper(scorer=PageRankScorer(), serializer="compact")

overview = mapper.create_overview(
    "path/to/repo",
    detail=DetailLevel.SIGNATURES,
    exclude_patterns=["**/__pycache__/*", "**/tests/*"],
    privacy="public_only",
)

focused = mapper.create_focused_view(
    ["src/core.py", "src/utils.py"],
    "path/to/repo",
    detail=DetailLevel.DOCSTRINGS,
)
```

`analyzers`, `scorer` and `serializer` accept instances, so custom implementations of
`CodeAnalyzer`, `GraphScorer` and `CodeSerializer` can be plugged in:

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from reposcape import CodeAnalyzer, CodeNode, NodeType, RepoMapper
from reposcape.analyzers import PythonAstAnalyzer
from upath import UPath


if TYPE_CHECKING:
    from os import PathLike


class IniAnalyzer(CodeAnalyzer):
    def can_handle(self, path: str | PathLike[str] | UPath) -> bool:
        return str(path).endswith(".ini")

    def analyze_file(
        self, path: str | PathLike[str] | UPath, content: str | None = None
    ) -> list[CodeNode]:
        path = UPath(path)
        text = content if content is not None else path.read_text()
        return [CodeNode(name=path.name, node_type=NodeType.FILE, path=str(path), content=text)]


mapper = RepoMapper(analyzers=[PythonAstAnalyzer(), IniAnalyzer()])
```

## Aider-style repo map

```python
from reposcape import AiderRepoMap
from reposcape.repomap import find_src_files

files = find_src_files("path/to/repo")
repo_map = AiderRepoMap("path/to/repo", max_tokens=1024)
print(repo_map.get_map(files, boost_files={"path/to/repo/src/core.py"}))
```

## AST-aware grep

```python
from reposcape import grep, grep_simple
from reposcape.repomap import find_src_files

files = find_src_files("src")
print(grep_simple(files, r"class \w+Scorer"))

result = grep(files, r"def score", ignore_case=True, margin=2)
print(result.total_matches, result.files_matched)
```

## Stub generation

Requires `reposcape[stubgen]`.

```python
from reposcape import generate_stub_from_source, generate_stubs_from_directory

print(generate_stub_from_source("def f(x: int) -> str:\n    return str(x)\n"))
stubs = generate_stubs_from_directory("src/mypackage")  # {"relative/path.pyi": "..."}
```
