"""Component 3: ``frequency`` — count and rank normalized terms.

Depends on :mod:`text_toolkit.tokenizer` and :mod:`text_toolkit.normalizer`.
Skeleton stub.
"""

from __future__ import annotations


def word_counts(text: str) -> dict[str, int]:
    """Return a mapping of normalized term -> occurrence count. (TODO.)"""
    raise NotImplementedError("word_counts is not implemented yet")


def top_terms(text: str, limit: int) -> list[tuple[str, int]]:
    """Return the ``limit`` most frequent ``(term, count)`` pairs. (TODO.)"""
    raise NotImplementedError("top_terms is not implemented yet")
