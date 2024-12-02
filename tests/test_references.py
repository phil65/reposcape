"""Tests for reference handling."""

from reposcape.models import Reference


def test_reference_creation():
    """Test reference object creation."""
    ref = Reference(
        name="helper",
        path="utils.py",
        line=10,
        column=5,
    )

    assert ref.name == "helper"
    assert ref.path == "utils.py"
    assert ref.line == 10  # noqa: PLR2004
    assert ref.column == 5  # noqa: PLR2004


def test_reference_equality():
    """Test reference equality comparison."""
    ref1 = Reference("helper", "utils.py", 10, 5)
    ref2 = Reference("helper", "utils.py", 10, 5)
    ref3 = Reference("helper", "other.py", 10, 5)

    assert ref1 == ref2
    assert ref1 != ref3
