"""Hidden acceptance suite for the ``pipeline`` component (failToPass).

Scoring-side ONLY. Exercises the orchestration of all three lower components.

Contract: ``summarize(text, limit)`` returns a dict with keys:
- ``"tokens"``: total number of raw tokens (from ``tokenize``);
- ``"terms"``: number of distinct normalized terms;
- ``"top"``: the ``top_terms(text, limit)`` list.
"""

from __future__ import annotations

from text_toolkit.pipeline import summarize


def test_summarize_reports_token_and_term_counts() -> None:
    result = summarize("The cat and the cat sat", 2)
    assert result["tokens"] == 6
    assert result["terms"] == 2
    assert result["top"] == [("cat", 2), ("sat", 1)]


def test_summarize_empty_text() -> None:
    result = summarize("the and of", 3)
    assert result["tokens"] == 3
    assert result["terms"] == 0
    assert result["top"] == []
