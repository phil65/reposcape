"""RepoScape: Repository maps for LLMs"""

from __future__ import annotations

from importlib.metadata import version

__version__ = version("reposcape")
__title__ = "RepoScape"
__description__ = "Repository maps for LLMs"
__author__ = "Philipp Temminghoff"
__author_email__ = "philipptemminghoff@googlemail.com"
__copyright__ = "Copyright (c) 2024 Philipp Temminghoff"
__license__ = "MIT"
__url__ = "https://github.com/phil65/reposcape"

from reposcape.mapper import RepoMapper
from reposcape.models import CodeNode, DetailLevel, NodeType
from reposcape.analyzers import CodeAnalyzer
from reposcape.functions import get_repo_overview, get_focused_view
from reposcape.importance import (
    GraphScorer,
    ImportanceCalculator,
    PageRankScorer,
    ReferenceScorer,
)
from reposcape.serializers import CodeSerializer


__all__ = [
    "CodeAnalyzer",
    "CodeNode",
    "CodeSerializer",
    "DetailLevel",
    "GraphScorer",
    "ImportanceCalculator",
    "NodeType",
    "PageRankScorer",
    "ReferenceScorer",
    "RepoMapper",
    "__version__",
    "get_focused_view",
    "get_repo_overview",
]
