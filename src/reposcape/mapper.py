"""Main repository mapping functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING
import warnings

from upath import UPath

from reposcape.analyzers import PythonAstAnalyzer, TextAnalyzer
from reposcape.importance import ImportanceCalculator, ReferenceScorer
from reposcape.models import CodeNode, DetailLevel, NodeType
from reposcape.serializers import MarkdownSerializer


if TYPE_CHECKING:
    from collections.abc import Sequence
    from os import PathLike

    from reposcape.analyzers import CodeAnalyzer
    from reposcape.importance import GraphScorer
    from reposcape.serializers import CodeSerializer


class RepoMapper:
    """Maps repository structure with focus on important elements."""

    def __init__(
        self,
        *,
        analyzers: Sequence[CodeAnalyzer] | None = None,
        scorer: GraphScorer | None = None,
        serializer: CodeSerializer | None = None,
    ):
        """Initialize RepoMapper.

        Args:
            analyzers: Code analyzers to use, defaults to [PythonAstAnalyzer]
            scorer: Graph scorer for importance calculation
            serializer: Serializer for output generation
        """
        self.analyzers = (
            list(analyzers)
            if analyzers
            else [
                PythonAstAnalyzer(),
                TextAnalyzer(),
            ]
        )
        # Create ImportanceCalculator with provided or default scorer
        self.importance_calculator = ImportanceCalculator(scorer or ReferenceScorer())
        self.serializer = serializer or MarkdownSerializer()

    def create_overview(
        self,
        repo_path: str | PathLike[str],
        *,
        token_limit: int | None = None,
        detail: DetailLevel = DetailLevel.SIGNATURES,
        exclude_patterns: list[str] | None = None,
    ) -> str:
        """Create a high-level overview of the entire repository.

        Args:
            repo_path: Path to repository root
            token_limit: Maximum tokens in output
            detail: Level of detail to include
            exclude_patterns: Glob patterns for paths to exclude

        Returns:
            Structured overview of the repository
        """
        repo_path = UPath(repo_path)

        # Analyze repository structure
        root_node = self._analyze_repository(
            repo_path,
            exclude_patterns=exclude_patterns,
        )

        # Calculate importance scores
        self._calculate_importance(root_node)

        # Generate output
        return self.serializer.serialize(
            root_node,
            detail=detail,
            token_limit=token_limit,
        )

    def create_focused_view(
        self,
        files: Sequence[str | PathLike[str]],
        repo_path: str | PathLike[str],
        *,
        token_limit: int | None = None,
        detail: DetailLevel = DetailLevel.SIGNATURES,
        exclude_patterns: list[str] | None = None,
    ) -> str:
        """Create a view focused on specific files and their relationships.

        Args:
            files: Files to focus on
            repo_path: Repository root path
            token_limit: Maximum tokens in output
            detail: Level of detail to include
            exclude_patterns: Glob patterns for paths to exclude

        Returns:
            Structured view focused on specified files
        """
        repo_path = UPath(repo_path)
        focused_paths = {str(UPath(f).relative_to(repo_path)) for f in files}

        # Analyze repository structure
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
            root_node,
            detail=detail,
            token_limit=token_limit,
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
        self,
        root: CodeNode,
        rel_path: UPath,
        nodes: list[CodeNode],
    ) -> None:
        """Add analyzed nodes to the tree structure."""
        # Ensure parent directories exist
        current = root
        for part in rel_path.parent.parts:
            assert current.children is not None
            if part not in current.children:
                current.children[part] = CodeNode(  # type: ignore
                    name=part,
                    node_type=NodeType.DIRECTORY,
                    path=str(UPath(current.path) / part),
                    children={},
                )
            current = current.children[part]

        # Add file and its nodes
        if nodes:
            current.children[rel_path.name] = nodes[0]  # type: ignore

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
