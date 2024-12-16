"""Constants and registries for reposcape."""

from __future__ import annotations

from reposcape.analyzers import PythonAstAnalyzer, TextAnalyzer
from reposcape.importance import PageRankScorer, ReferenceScorer


AVAILABLE_ANALYZERS = {
    "python": PythonAstAnalyzer,
    "text": TextAnalyzer,
}

AVAILABLE_SCORERS = {
    "reference": ReferenceScorer,
    "pagerank": PageRankScorer,
}

DEFAULT_ANALYZERS = ["python", "text"]
DEFAULT_SCORER = "reference"
