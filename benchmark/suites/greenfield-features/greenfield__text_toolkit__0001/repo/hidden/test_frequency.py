"""Hidden acceptance suite for the ``frequency`` component (failToPass).

Scoring-side ONLY. Depends on tokenizer + normalizer.

Contract:
- ``word_counts`` tokenizes then normalizes ``text`` and returns a mapping of
  surviving term -> occurrence count.
- ``top_terms`` returns the ``limit`` most frequent ``(term, count)`` pairs,
  sorted by count descending and, on ties, by term ascending.
"""

from __future__ import annotations

from text_toolkit.frequency import top_terms, word_counts


def test_word_counts_uses_normalized_terms() -> None:
    assert word_counts("The cat. A CAT and the Dog") == {"cat": 2, "dog": 1}


def test_word_counts_empty_text() -> None:
    assert word_counts("the a of") == {}


def test_top_terms_orders_by_count_then_term() -> None:
    text = "red red red green green blue"
    assert top_terms(text, 2) == [("red", 3), ("green", 2)]


def test_top_terms_breaks_ties_alphabetically() -> None:
    text = "zeta alpha"
    assert top_terms(text, 2) == [("alpha", 1), ("zeta", 1)]


def test_top_terms_respects_limit() -> None:
    text = "a1 a1 b2 c3"
    assert top_terms(text, 1) == [("a1", 2)]
