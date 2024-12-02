"""Tests for importance calculation."""

from __future__ import annotations

import pytest

from reposcape.importance import ImportanceCalculator, ReferenceScorer
from reposcape.importance.graph import Graph
from reposcape.models import CodeNode, NodeType, Reference


@pytest.fixture
def simple_nodes() -> list[CodeNode]:
    """Create simple test nodes with references."""
    main = CodeNode(
        name="main.py",
        node_type=NodeType.FILE,
        path="main.py",
        references_to=[
            Reference(
                name="helper",
                path="utils.py",
                line=2,
                column=0,
            ),
        ],
    )

    utils = CodeNode(
        name="utils.py",
        node_type=NodeType.FILE,
        path="utils.py",
        # Add helper function as child
        children={
            "helper": CodeNode(
                name="helper",
                node_type=NodeType.FUNCTION,
                path="utils.py",
                signature="def helper(): ...",
            )
        },
    )

    return [main, utils]


def test_calculate_basic(simple_nodes: list[CodeNode]):
    """Test basic importance calculation."""
    calculator = ImportanceCalculator(ReferenceScorer())
    scores = calculator.calculate(simple_nodes)

    assert "main.py" in scores
    assert "utils.py" in scores
    assert all(0.0 <= score <= 1.0 for score in scores.values())

    # utils.py should have higher score due to being referenced
    assert scores["utils.py"] > scores["main.py"]


def test_calculate_with_focused_paths(simple_nodes: list[CodeNode]):
    """Test importance calculation with focused paths."""
    calculator = ImportanceCalculator(ReferenceScorer())
    scores = calculator.calculate(
        simple_nodes,
        focused_paths={"main.py"},
        mentioned_symbols=set(),
    )

    # Main.py is focused, should have significantly higher score
    assert scores["main.py"] > 0.8  # noqa: PLR2004
    assert scores["main.py"] > scores["utils.py"]


def test_calculate_with_mentioned_symbols(simple_nodes: list[CodeNode]):
    """Test importance calculation with mentioned symbols."""
    calculator = ImportanceCalculator(ReferenceScorer())
    scores = calculator.calculate(
        simple_nodes,
        focused_paths=set(),  # Explicitly set no focused paths
        mentioned_symbols={"helper"},
    )

    # utils.py contains mentioned symbol, should have higher score
    assert scores["utils.py"] > scores["main.py"]
    # Score should be significant but not necessarily maximum
    assert scores["utils.py"] > 0.5  # noqa: PLR2004


def test_calculate_with_empty_input():
    """Test importance calculation with empty input."""
    calculator = ImportanceCalculator(ReferenceScorer())
    scores = calculator.calculate([])
    assert scores == {}


def test_calculate_combined_factors(simple_nodes: list[CodeNode]):
    """Test importance calculation with both focus and mentioned symbols."""
    calculator = ImportanceCalculator(ReferenceScorer())
    scores = calculator.calculate(
        simple_nodes,
        focused_paths={"main.py"},
        mentioned_symbols={"helper"},
    )

    # Both files should have non-zero scores
    assert scores["main.py"] > 0.5  # Focused file  # noqa: PLR2004
    assert scores["utils.py"] > 0.0  # Contains mentioned symbol
    # Focused file should have higher score
    assert scores["main.py"] > scores["utils.py"]


def test_reference_scorer_weights():
    """Test that ReferenceScorer weights affect scores appropriately."""
    scorer = ReferenceScorer(
        ref_weight=1.0,
        outref_weight=0.5,
        important_ref_boost=2.0,
        focus_boost=5.0,
    )

    graph = Graph()
    graph.add_edge("a", "b", weight=1.0)

    # Test with focus
    scores = scorer.score(graph, important_nodes={"a"})
    assert scores["a"] > 0.8  # Focused node should have high score  # noqa: PLR2004
    assert scores["b"] < scores["a"]  # Non-focused node should have lower score
