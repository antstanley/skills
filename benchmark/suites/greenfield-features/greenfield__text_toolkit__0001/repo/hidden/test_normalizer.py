"""Hidden acceptance suite for the ``normalizer`` component (failToPass).

Scoring-side ONLY. Depends on the tokenizer contract.

Contract: ``normalize`` lowercases each token and removes a small set of stop
words (``a``, ``an``, ``the``, ``of``, ``and``, ``to``, ``in``), preserving the
order of the surviving tokens.
"""

from __future__ import annotations

from text_toolkit.normalizer import normalize


def test_lowercases_tokens() -> None:
    assert normalize(["The", "QUICK", "Fox"]) == ["quick", "fox"]


def test_drops_stop_words() -> None:
    assert normalize(["a", "cat", "and", "the", "dog"]) == ["cat", "dog"]


def test_preserves_order_of_survivors() -> None:
    assert normalize(["Beta", "of", "Alpha"]) == ["beta", "alpha"]


def test_empty_input_yields_empty() -> None:
    assert normalize([]) == []
