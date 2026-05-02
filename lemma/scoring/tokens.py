"""Token counting for Pareto efficiency."""

from __future__ import annotations

import tiktoken


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Approximate token count (cl100k_base fallback)."""
    if not text:
        return 0
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))
