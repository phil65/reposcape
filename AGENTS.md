# AGENTS.md

## Overview

RepoScape builds compact "repository maps" for LLM context: it parses a repository (or an
imported Python package), builds a reference graph between symbols, scores elements by
importance and serializes the most relevant ones within a token budget. It also ships an
Aider-style tree-sitter repo map (`AiderRepoMap`), AST-aware grep and mypy-based stub generation.
Pure Python library, no CLI entry point (only a `__main__` block in `mapper.py`).

## Architecture

Pipeline used by `RepoMapper` (`src/reposcape/mapper.py`):

1. **Analyze**: `CodeAnalyzer` subclasses (`analyzers/base.py`) turn files into `CodeNode` trees.
   - `analyzers/python_ast.py`: `PythonAstAnalyzer` + `SymbolCollector` (stdlib `ast`; also
     `analyze_module()` for imported modules). Default.
   - `analyzers/text.py`: `TextAnalyzer` for `.txt/.md/.rst`. Default.
   - `analyzers/python_astroid.py`, `analyzers/python_cst.py`: experimental, not exported,
     written against outdated astroid/libcst APIs and currently broken. Excluded from ty.
2. **Model**: `models/nodes.py` (`CodeNode`, `Reference`, `NodeType`; frozen dataclasses,
   mutated in places via `object.__setattr__`), `models/options.py` (`DetailLevel`,
   `FormatType`, `PrivacyMode`).
3. **Score**: `importance/base.py` `ImportanceCalculator` builds a `Graph`
   (`importance/graph.py`, networkx `DiGraph` keyed by node path) and delegates to a
   `GraphScorer` (`importance/scoring.py`: `ReferenceScorer` default, `PageRankScorer`).
   `importance/pagerank.py` / `frequency.py` are older calculator variants.
4. **Serialize**: `serializers/base.py` `CodeSerializer` (priority + token-limit handling via
   `utils/tokens.py` / tiktoken); `markdown.py`, `compact.py`, `tree.py`.

Other entry points:
- `functions.py`: `get_repo_overview()` / `get_focused_view()`, string-based wrappers that
  resolve analyzer/scorer names via registries in `constants.py`.
- `repomap.py`: `AiderRepoMap` (tree-sitter tags via grep-ast, PageRank ranking, diskcache tag
  cache in `.reposcape.tags.cache.v*`). Uses `.scm` query files in `src/reposcape/queries/`.
- `grep.py`: `grep()` / `grep_simple()` with grep-ast `TreeContext`, threaded.
- `stubgen.py`: `generate_stub_*` helpers on top of `mypy.stubgen` (mypy imported lazily).

## Where to look

| Task | Location |
|---|---|
| Public API / exports | `src/reposcape/__init__.py` |
| Add a file-type analyzer | `src/reposcape/analyzers/`, register in `constants.py` |
| Change importance scoring | `src/reposcape/importance/scoring.py` |
| Output format / token budgeting | `src/reposcape/serializers/` |
| Tree-sitter repo map, language queries | `src/reposcape/repomap.py`, `src/reposcape/queries/` |
| Stub generation | `src/reposcape/stubgen.py` |
| Tests | `tests/` (`tests/analyzers/`, `tests/importance/`, fixtures in `tests/conftest.py`) |

## Commands

```bash
uv sync --all-extras                 # setup (uv.lock is gitignored)
uv run pytest                        # tests (config in [tool.pytest])
uvx ruff check . && uvx ruff format --check .
uv run ty check                      # type check (src only); warnings fail CI
uv run deptry src                    # dependency check
uv run mkdocs-mknodes build          # docs (README + auto-generated API pages)
uv run duty lint | lint_check | test | build | serve   # tasks in duties.py
```

CI (`.github/workflows/build.yml`): ruff, ty, pytest on 3.13/3.14 x Linux/macOS/Windows
(3.14 is `continue-on-error`). Docs: `.github/workflows/documentation.yml` deploys to Pages.

## Conventions

- Python >= 3.13, `from __future__ import annotations`, type-only imports under `TYPE_CHECKING`.
- Ruff with a broad rule set and preview formatting, line length 100, Google docstrings.
- Paths go through `upath.UPath` / `upathtools.to_upath` so fsspec filesystems work.
- Use `# ty: ignore[rule]` (not mypy-style `# type: ignore[code]`) for checker limitations.
- Tests are plain pytest functions; test-only deps belong in the `dev` group.

## Pitfalls

- Copier-managed (template `copier-phil65`): `pyproject.toml` tool sections, workflows,
  `duties.py`, `.pre-commit-config.yaml`, `mkdocs.yml`. Don't hand-edit template-owned parts;
  add dependencies below the `# Only add below (Copier)` markers.
- Optional extras: `stubgen` (mypy), `astroid`, `libcst`, `repomap`. Keep their imports lazy or
  confined to their modules so `import reposcape` works without them.
- The docs build imports every module, so all optional deps must be installed for it.
- Pre-commit runs ruff, tombi, ty and pytest on commit.
