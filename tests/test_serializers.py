"""Tests for serializers."""

from __future__ import annotations

import pytest

from reposcape.models import CodeNode, DetailLevel, NodeType
from reposcape.serializers import CompactSerializer, MarkdownSerializer, TreeSerializer


@pytest.mark.parametrize("serializer_cls", [MarkdownSerializer, CompactSerializer, TreeSerializer])
def test_token_limit_keeps_unscored_parents(serializer_cls):
    """Important nodes must still be reachable through unscored parent directories."""
    func = CodeNode(
        name="important_func",
        node_type=NodeType.FUNCTION,
        path="pkg/mod.py",
        signature="def important_func()",
        importance=1.0,
    )
    file_node = CodeNode(
        name="mod.py",
        node_type=NodeType.FILE,
        path="pkg/mod.py",
        children={"important_func": func},
        importance=1.0,
    )
    pkg = CodeNode(
        name="pkg", node_type=NodeType.DIRECTORY, path="pkg", children={"mod.py": file_node}
    )
    root = CodeNode(name="repo", node_type=NodeType.DIRECTORY, path=".", children={"pkg": pkg})

    result = serializer_cls().serialize(root, detail=DetailLevel.SIGNATURES, token_limit=500)
    assert "important_func" in result
