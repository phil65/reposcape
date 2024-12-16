"""Main repository mapping functionality."""

from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType
from typing import TYPE_CHECKING, overload
import warnings

from upath import UPath

from reposcape.analyzers import PythonAstAnalyzer, TextAnalyzer
from reposcape.importance import ImportanceCalculator, ReferenceScorer
from reposcape.models import CodeNode, DetailLevel, NodeType
from reposcape.serializers import (
    CodeSerializer,
    CompactSerializer,
    MarkdownSerializer,
    TreeSerializer,
)


if TYPE_CHECKING:
    from collections.abc import Sequence
    from os import PathLike

    from reposcape.analyzers import CodeAnalyzer
    from reposcape.importance import GraphScorer
    from reposcape.models.options import FormatType, PrivacyMode


class RepoMapper:
    """Maps repository structure with focus on important elements."""

    def __init__(
        self,
        *,
        analyzers: Sequence[CodeAnalyzer] | None = None,
        scorer: GraphScorer | None = None,
        serializer: FormatType | CodeSerializer = "markdown",
    ):
        """Initialize RepoMapper.

        Args:
            analyzers: Code analyzers to use, defaults to [PythonAstAnalyzer]
            scorer: Graph scorer for importance calculation
            serializer: Serializer for output generation
        """
        self.analyzers = (
            list(analyzers) if analyzers else [PythonAstAnalyzer(), TextAnalyzer()]
        )
        self.importance_calculator = ImportanceCalculator(scorer or ReferenceScorer())

        # Handle serializer string or instance
        if isinstance(serializer, str):
            self.serializer = {
                "markdown": MarkdownSerializer(),
                "compact": CompactSerializer(),
                "tree": TreeSerializer(),
            }[serializer]
        else:
            self.serializer = serializer

    @overload
    def create_overview(
        self,
        repo_path: str | PathLike[str],
        *,
        token_limit: int | None = None,
        detail: DetailLevel = DetailLevel.SIGNATURES,
        exclude_patterns: list[str] | None = None,
        root_package: None = None,
        privacy: PrivacyMode = "smart",
    ) -> str: ...

    @overload
    def create_overview(
        self,
        repo_path: ModuleType,
        *,
        token_limit: int | None = None,
        detail: DetailLevel = DetailLevel.SIGNATURES,
        exclude_patterns: None = None,
        root_package: ModuleType | None = None,
        privacy: PrivacyMode = "smart",
    ) -> str: ...

    def create_overview(
        self,
        repo_path: str | PathLike[str] | ModuleType,
        *,
        token_limit: int | None = None,
        detail: DetailLevel = DetailLevel.SIGNATURES,
        exclude_patterns: list[str] | None = None,
        root_package: ModuleType | None = None,
        privacy: PrivacyMode = "smart",
    ) -> str:
        """Create a high-level overview.

        Args:
            repo_path: Path to repository root or Python module to analyze
            root_package: Optional parent package to consider for references
                When analyzing a module, references to other modules within
                root_package will be included in the analysis.
            token_limit: Maximum tokens in output
            detail: Level of detail to include
            exclude_patterns: Glob patterns for paths to exclude
            privacy: Whether to include private functions / classes
        """
        if isinstance(repo_path, ModuleType):
            # If no root_package specified, only analyze repo_path's tree
            pkg_name = (root_package or repo_path).__name__
            root_node = self._analyze_module(repo_path, pkg_name)
        else:
            root_node = self._analyze_repository(
                UPath(repo_path),
                exclude_patterns=exclude_patterns,
            )
        self._calculate_importance(root_node)
        return self.serializer.serialize(
            root_node,
            detail=detail,
            token_limit=token_limit,
            privacy=privacy,
        )

    def _analyze_module(self, module: ModuleType, package_name: str) -> CodeNode:
        """Analyze a Python module and its submodules.

        Only analyzes modules that are part of the specified package.

        Args:
            module: Module to analyze
            package_name: Package namespace to analyze
        """
        try:
            # Check if module is part of our package
            if not module.__name__.startswith(package_name):
                msg = f"Module {module.__name__} is not part of package {package_name}"
                raise ValueError(msg)  # noqa: TRY301

            analyzer = next(
                (a for a in self.analyzers if isinstance(a, PythonAstAnalyzer)),
                None,
            )
            if not analyzer:
                msg = "No suitable analyzer found for Python module"
                raise ValueError(msg)  # noqa: TRY301

            # Analyze main module
            nodes = analyzer.analyze_module(module)
            if not nodes:
                msg = f"No nodes generated for module {module.__name__}"
                raise ValueError(msg)  # noqa: TRY301
            root_node = nodes[0]

            # Handle submodules if this is a package
            if hasattr(module, "__path__"):
                children = root_node.children or {}

                # Iterate through all submodules
                for module_info in pkgutil.iter_modules(module.__path__):
                    if not module_info.ispkg:  # Skip recursive packages for now
                        # Import submodule
                        submodule_name = f"{module.__name__}.{module_info.name}"
                        if submodule_name.startswith(package_name):
                            try:
                                submodule = importlib.import_module(submodule_name)
                                # Recursively analyze submodule
                                sub_node = self._analyze_module(submodule, package_name)
                                children[module_info.name] = sub_node  # type: ignore
                            except Exception as e:  # noqa: BLE001
                                warnings.warn(
                                    f"Failed to analyze submodule {submodule_name}: {e}",
                                    RuntimeWarning,
                                    stacklevel=1,
                                )

                # Update root node with submodule children
                object.__setattr__(root_node, "children", children)
        except Exception as e:  # noqa: BLE001
            msg = f"Error analyzing module {module.__name__}: {e}"
            warnings.warn(msg, RuntimeWarning, stacklevel=1)
            return CodeNode(
                name=module.__name__,
                node_type=NodeType.FILE,
                path=module.__file__ or module.__name__,
                docstring=module.__doc__,
            )
        else:
            return root_node

    @overload
    def create_focused_view(
        self,
        files: Sequence[str | PathLike[str]],
        repo_path: str | PathLike[str],
        *,
        token_limit: int | None = None,
        detail: DetailLevel = DetailLevel.SIGNATURES,
        exclude_patterns: list[str] | None = None,
        root_package: None = None,
        privacy: PrivacyMode = "smart",
    ) -> str: ...

    @overload
    def create_focused_view(
        self,
        files: Sequence[str | PathLike[str]],
        repo_path: ModuleType,
        *,
        token_limit: int | None = None,
        detail: DetailLevel = DetailLevel.SIGNATURES,
        exclude_patterns: None = None,
        root_package: ModuleType | None = None,
        privacy: PrivacyMode = "smart",
    ) -> str: ...

    def create_focused_view(
        self,
        files: Sequence[str | PathLike[str]],
        repo_path: str | PathLike[str] | ModuleType,
        *,
        token_limit: int | None = None,
        detail: DetailLevel = DetailLevel.SIGNATURES,
        exclude_patterns: list[str] | None = None,
        root_package: ModuleType | None = None,
        privacy: PrivacyMode = "smart",
    ) -> str:
        """Create a view focused on specific files and their relationships.

        Args:
            files: Files to focus on
            repo_path: Repository root path
            token_limit: Maximum tokens in output
            detail: Level of detail to include
            exclude_patterns: Glob patterns for paths to exclude
            root_package: Optional parent package to consider for references
                When analyzing a module, references to other modules within
                root_package will be included in the analysis.
            privacy: Whether to include private functions / classes

        Returns:
            Structured view focused on specified files
        """
        if isinstance(repo_path, ModuleType):
            # If no root_package specified, use repo_path as root
            pkg_name = (root_package or repo_path).__name__
            root_node = self._analyze_module(repo_path, pkg_name)
            # Convert file paths to module paths relative to package
            focused_paths = {f"{pkg_name}.{str(f).replace('/', '.')}" for f in files}
        else:
            repo_path = UPath(repo_path)
            focused_paths = {str(UPath(f).relative_to(repo_path)) for f in files}
            root_node = self._analyze_repository(
                repo_path,
                exclude_patterns=exclude_patterns,
            )

        # Calculate importance scores with focus
        self._calculate_importance(
            root_node,
            focused_paths=focused_paths,
        )

        # Generate output
        return self.serializer.serialize(
            root_node, detail=detail, token_limit=token_limit, privacy=privacy
        )

    def _analyze_repository(
        self,
        repo_path: UPath,
        *,
        exclude_patterns: list[str] | None = None,
    ) -> CodeNode:
        """Analyze repository and build CodeNode tree."""
        exclude_patterns = exclude_patterns or []

        # Create root node
        root = CodeNode(
            name=repo_path.name,
            node_type=NodeType.DIRECTORY,
            path=".",
            children={},
        )

        # Build directory structure
        for path in repo_path.glob("**/*"):
            # Skip excluded paths
            if any(path.match(pattern) for pattern in exclude_patterns):
                continue

            # Skip directories, we'll create them as needed
            if path.is_dir():
                continue

            rel_path = path.relative_to(repo_path)

            try:
                # Find suitable analyzer
                analyzer = None
                for a in self.analyzers:
                    if a.can_handle(path):
                        analyzer = a
                        break

                if analyzer:
                    # Analyze file with specific analyzer
                    nodes = analyzer.analyze_file(path)
                    # Ensure correct paths in nodes
                    for node in nodes:
                        object.__setattr__(node, "path", str(rel_path))
                else:
                    # Create basic file node for unanalyzed files
                    nodes = [
                        CodeNode(
                            name=path.name,
                            node_type=NodeType.FILE,
                            path=str(rel_path),
                            content=path.read_text(encoding="utf-8"),
                        )
                    ]

                # Add to tree
                self._add_to_tree(root, rel_path, nodes)

            except Exception as e:  # noqa: BLE001
                msg = f"Error analyzing {path}: {e}"
                warnings.warn(msg, RuntimeWarning, stacklevel=1)

        return root

    def _add_to_tree(
        self, root: CodeNode, rel_path: UPath, nodes: list[CodeNode]
    ) -> None:
        """Add analyzed nodes to the tree structure."""
        current = root
        for part in rel_path.parent.parts:
            assert current.children is not None
            if part not in current.children:
                new_node = CodeNode(
                    name=part,
                    node_type=NodeType.DIRECTORY,
                    path=str(UPath(current.path) / part),
                    children={},
                    parent=current,  # Set parent reference
                )
                current.children[part] = new_node  # type: ignore
            current = current.children[part]

        # Add file and its nodes
        if nodes:
            node = nodes[0]
            object.__setattr__(node, "parent", current)  # Set parent reference
            current.children[rel_path.name] = node  # type: ignore

    def _calculate_importance(
        self,
        root: CodeNode,
        *,
        focused_paths: set[str] | None = None,
    ) -> None:
        """Calculate importance scores for all nodes."""
        # Collect all nodes
        all_nodes: list[CodeNode] = []

        def collect_nodes(node: CodeNode) -> None:
            all_nodes.append(node)
            if node.children:
                for child in node.children.values():
                    collect_nodes(child)

        collect_nodes(root)

        # Calculate scores
        scores = self.importance_calculator.calculate(
            all_nodes,
            focused_paths=focused_paths,
        )

        # Apply scores
        for node in all_nodes:
            score = scores.get(node.path, 0.0)
            object.__setattr__(node, "importance", score)


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Generate repository structure maps")
    parser.add_argument(
        "repo_path",
        type=Path,
        help="Path to repository root",
        nargs="?",
        default=".",
    )
    parser.add_argument(
        "--files",
        type=Path,
        nargs="+",
        help="Files to focus on (for focused view)",
    )
    parser.add_argument(
        "--tokens",
        type=int,
        default=2000,
        help="Maximum tokens in output",
    )
    parser.add_argument(
        "--detail",
        choices=["structure", "signatures", "docstrings", "full"],
        default="signatures",
        help="Detail level in output",
    )

    args = parser.parse_args()

    # Create mapper
    mapper = RepoMapper()

    # Convert detail level string to enum
    detail = DetailLevel[args.detail.upper()]

    # Generate map
    if args.files:
        result = mapper.create_focused_view(
            files=args.files,
            repo_path=args.repo_path,
            token_limit=args.tokens,
            detail=detail,
        )
    else:
        result = mapper.create_overview(
            repo_path=args.repo_path,
            token_limit=args.tokens,
            detail=detail,
        )

    print(result)
