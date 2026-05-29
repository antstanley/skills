"""Hidden acceptance suite for the ``tokenizer`` component (failToPass).

Scoring-side ONLY. Injected at the checkout root next to ``text_toolkit/``;
never present in the run-visible ``base/`` tree.

Contract: ``tokenize`` splits on any run of non-alphanumeric characters,
preserving original case, dropping empty tokens.
"""

from __future__ import annotations

from text_toolkit.tokenizer import tokenize


def test_splits_on_whitespace() -> None:
    assert tokenize("the quick brown fox") == ["the", "quick", "brown", "fox"]


def test_splits_on_punctuation_and_drops_empties() -> None:
    assert tokenize("Hello, world!  Bye...") == ["Hello", "world", "Bye"]


def test_preserves_case_and_digits() -> None:
    assert tokenize("Foo2 BAR baz") == ["Foo2", "BAR", "baz"]


def test_empty_text_yields_no_tokens() -> None:
    assert tokenize("   ...  ") == []
