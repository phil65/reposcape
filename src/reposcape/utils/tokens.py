"""Token counting utilities."""

from __future__ import annotations

from functools import lru_cache

import tiktoken


@lru_cache(maxsize=1)
def get_tokenizer(model: str = "gpt-3.5-turbo") -> tiktoken.Encoding:
    """Get cached tokenizer for model."""
    return tiktoken.encoding_for_model(model)


def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """Count tokens in text using the model's tokenizer."""
    return len(get_tokenizer(model).encode(text))
