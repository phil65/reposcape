"""Repository structure mapping and analysis."""

from __future__ import annotations

from reposcape.mapper import RepoMapper
from reposcape.models import CodeNode, DetailLevel, NodeType
from reposcape.analyzers import CodeAnalyzer
from reposcape.importance import ImportanceCalculator
from reposcape.serializers import CodeSerializer

__version__ = "0.0.1"

__all__ = [
    "CodeAnalyzer",
    "CodeNode",
    "CodeSerializer",
    "DetailLevel",
    "ImportanceCalculator",
    "NodeType",
    "RepoMapper",
]
