"""Options and enums for output configuration."""

from __future__ import annotations

from enum import Enum, auto
from typing import Literal


class DetailLevel(Enum):
    """How much detail to include in output."""

    STRUCTURE = auto()  # Just names and hierarchy
    SIGNATURES = auto()  # Include function/class signatures
    DOCSTRINGS = auto()  # Include signatures + docstrings
    FULL_CODE = auto()  # Include complete implementations


# Format type and privacy mode as literals
FormatType = Literal["markdown", "compact", "tree"]
PrivacyMode = Literal["public_only", "all", "smart"]
