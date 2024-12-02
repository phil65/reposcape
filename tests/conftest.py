"""Common test fixtures and configuration."""

from __future__ import annotations

import pytest


@pytest.fixture
def simple_python_file() -> str:
    """Return a simple Python file content for testing."""
    return '''"""Module docstring."""
from typing import Any

class SimpleClass:
    """A simple class."""

    def method(self, arg: int) -> str:
        """Do something."""
        return str(arg)

def top_level_func(x: Any) -> bool:
    """A top level function."""
    return isinstance(x, SimpleClass)

CONSTANT = 42
'''


@pytest.fixture
def complex_python_file() -> str:
    """Return a more complex Python file with inheritance and references."""
    return '''"""Complex module with various Python features."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")

@dataclass
class Config:
    """Configuration class."""
    name: str
    value: int

class BaseHandler(ABC):
    """Abstract base handler."""

    @abstractmethod
    def handle(self) -> None:
        """Handle something."""
        pass

class Handler(BaseHandler, Generic[T]):
    """Concrete handler implementation."""

    def __init__(self, config: Config) -> None:
        self.config = config

    def handle(self) -> None:
        """Implementation of handle method."""
        other = OtherClass()
        other.do_something(self.config.value)

class OtherClass:
    """Another class that gets referenced."""

    def do_something(self, value: int) -> None:
        """Do something with value."""
        print(f"Doing {value}")
'''
