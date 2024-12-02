"""Tests for handling different node types."""

import dataclasses

import pytest

from reposcape.models import CodeNode, NodeType


def test_directory_node():
    """Test directory node creation and validation."""
    node = CodeNode(
        name="src",
        node_type=NodeType.DIRECTORY,
        path="src",
        children={},
    )
    assert node.node_type == NodeType.DIRECTORY
    assert not node.references_to
    assert not node.referenced_by


def test_node_initialization():
    """Test node initialization with defaults."""
    node = CodeNode(
        name="test",
        node_type=NodeType.FILE,
        path="test.py",
    )

    assert node.children == {}
    assert node.references_to == []
    assert node.referenced_by == []
    assert node.importance == 0.0


def test_node_immutability():
    """Test that nodes are immutable."""
    node = CodeNode(
        name="test",
        node_type=NodeType.FILE,
        path="test.py",
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        node.name = "changed"  # type: ignore
