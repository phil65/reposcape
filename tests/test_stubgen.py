"""Tests for stub generation."""

from __future__ import annotations

import pytest

from reposcape import generate_stub_from_source


pytest.importorskip("mypy")


def test_generate_stub_from_source():
    source = 'def f(x: int) -> str:\n    """Convert."""\n    return str(x)\n'
    stub = generate_stub_from_source(source)
    assert "def f(x: int) -> str:" in stub
    assert "return str(x)" not in stub
