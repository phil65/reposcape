"""Functional interface for repository analysis."""

from __future__ import annotations

import importlib
from types import ModuleType
from typing import TYPE_CHECKING, Literal

from reposcape.constants import (
    AVAILABLE_ANALYZERS,
    AVAILABLE_SCORERS,
    DEFAULT_ANALYZERS,
    DEFAULT_SCORER,
)
from reposcape.mapper import RepoMapper
from reposcape.models import DetailLevel


if TYPE_CHECKING:
    from collections.abc import Sequence
    from os import PathLike

    from reposcape.analyzers import CodeAnalyzer
    from reposcape.importance import GraphScorer
    from reposcape.models.options import FormatType, PrivacyMode

    AnalyzerSpec = str | type[CodeAnalyzer] | CodeAnalyzer
    ScorerSpec = str | type[GraphScorer] | GraphScorer
    PackageSpec = str | ModuleType


def _resolve_analyzers(
    analyzers: Sequence[AnalyzerSpec] | None,
) -> list[CodeAnalyzer]:
    """Resolve analyzer specifications to analyzer instances."""
    if analyzers is None:
        analyzers = DEFAULT_ANALYZERS

    result: list[CodeAnalyzer] = []
    for spec in analyzers:
        if isinstance(spec, str):
            analyzer_cls = AVAILABLE_ANALYZERS[spec]
            result.append(analyzer_cls())
        elif isinstance(spec, type):
            result.append(spec())
        else:
            result.append(spec)
    return result


def _resolve_scorer(scorer: ScorerSpec | None) -> GraphScorer:
    """Resolve scorer specification to scorer instance."""
    if scorer is None:
        scorer = DEFAULT_SCORER

    if isinstance(scorer, str):
        scorer_cls = AVAILABLE_SCORERS[scorer]
        return scorer_cls()
    if isinstance(scorer, type):
        return scorer()
    return scorer


def _resolve_package(package: PackageSpec | None) -> ModuleType | None:
    """Resolve package specification to module."""
    if package is None:
        return None
    if isinstance(package, str):
        return importlib.import_module(package)
    return package


def get_repo_overview(
    repo_path: str | PathLike[str] | ModuleType,
    *,
    root_package: PackageSpec | None = None,
    output_format: FormatType = "markdown",
    detail: Literal["structure", "signatures", "docstrings", "full"] = "signatures",
    token_limit: int | None = None,
    exclude_patterns: list[str] | None = None,
    privacy: PrivacyMode = "smart",
    analyzers: Sequence[AnalyzerSpec] | None = None,
    scorer: ScorerSpec | None = None,
) -> str:
    """Get a structural overview of a repository or module.

    Args:
        repo_path: Path to repository or Python module to analyze
        root_package: Optional parent package (as import path or module)
            When analyzing a module, references to other modules within
            root_package will be included in the analysis.
        output_format: Output format ("markdown", "compact", or "tree")
        detail: Level of detail to include
        token_limit: Maximum tokens in output (for LLM context limits)
        exclude_patterns: Glob patterns for paths to exclude
        privacy: How to handle private elements ("public_only", "all", "smart")
        analyzers: Custom analyzers or analyzer names. Defaults to ["python", "text"]
            Available analyzers: "python", "text"
        scorer: Custom scorer or scorer name. Defaults to "reference"
            Available scorers: "reference", "pagerank"

    Returns:
        Structured overview of the codebase in requested format

    Example:
        >>> # Using default analyzers
        >>> print(get_repo_overview(".", format="tree"))

        >>> # Using specific analyzers
        >>> print(get_repo_overview(".", analyzers=["python"]))

        >>> # Using custom analyzer
        >>> print(get_repo_overview(".", analyzers=[MyAnalyzer()]))

        >>> # Analyzing a package
        >>> print(get_repo_overview("requests", root_package="requests"))
    """
    mapper = RepoMapper(
        analyzers=_resolve_analyzers(analyzers),
        scorer=_resolve_scorer(scorer),
        serializer=output_format,
    )

    detail_level = DetailLevel[detail.upper()]
    root_mod = _resolve_package(root_package)

    if isinstance(repo_path, ModuleType):
        # For module paths, ignore exclude_patterns
        return mapper.create_overview(
            repo_path=repo_path,
            root_package=root_mod,
            token_limit=token_limit,
            detail=detail_level,
            exclude_patterns=None,
            privacy=privacy,
        )
    # For filesystem paths
    return mapper.create_overview(
        repo_path=repo_path,
        root_package=None,
        token_limit=token_limit,
        detail=detail_level,
        exclude_patterns=exclude_patterns,
        privacy=privacy,
    )


def get_focused_view(
    files: Sequence[str | PathLike[str]],
    repo_path: str | PathLike[str] | ModuleType,
    *,
    root_package: PackageSpec | None = None,
    output_format: FormatType = "markdown",
    detail: Literal["structure", "signatures", "docstrings", "full"] = "signatures",
    token_limit: int | None = None,
    exclude_patterns: list[str] | None = None,
    privacy: PrivacyMode = "smart",
    analyzers: Sequence[AnalyzerSpec] | None = None,
    scorer: ScorerSpec | None = None,
) -> str:
    """Get a focused view of specific files and their relationships.

    Args:
        files: Files to focus on
        repo_path: Repository root or Python module
        root_package: Optional parent package (as import path or module)
        output_format: Output format ("markdown", "compact", or "tree")
        detail: Level of detail to include
        token_limit: Maximum tokens in output (for LLM context limits)
        exclude_patterns: Glob patterns for paths to exclude
        privacy: How to handle private elements ("public_only", "all", "smart")
        analyzers: Custom analyzers or analyzer names. Defaults to ["python", "text"]
            Available analyzers: "python", "text"
        scorer: Custom scorer or scorer name. Defaults to "reference"
            Available scorers: "reference", "pagerank"

    Returns:
        Focused view of the specified files in requested format

    Example:
        >>> files = ["myproject/main.py"]
        >>> # Using default analyzers
        >>> print(get_focused_view(files, "."))

        >>> # Using specific scorer
        >>> print(get_focused_view(files, ".", scorer="pagerank"))

        >>> # Analyzing module files
        >>> print(get_focused_view(["client.py"], "requests",
        ...       root_package="requests"))
    """
    mapper = RepoMapper(
        analyzers=_resolve_analyzers(analyzers),
        scorer=_resolve_scorer(scorer),
        serializer=output_format,
    )

    detail_level = DetailLevel[detail.upper()]
    root_mod = _resolve_package(root_package)

    if isinstance(repo_path, ModuleType):
        # For module paths, ignore exclude_patterns
        return mapper.create_focused_view(
            files=files,
            repo_path=repo_path,
            root_package=root_mod,
            token_limit=token_limit,
            detail=detail_level,
            exclude_patterns=None,
            privacy=privacy,
        )
    # For filesystem paths
    return mapper.create_focused_view(
        files=files,
        repo_path=repo_path,
        root_package=None,
        token_limit=token_limit,
        detail=detail_level,
        exclude_patterns=exclude_patterns,
        privacy=privacy,
    )
