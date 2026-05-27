"""``text_toolkit`` — a tiny multi-component text-processing library (skeleton).

This is the SKELETON the arms start from. Every public function below is a
stub that raises :class:`NotImplementedError`; the prose specification
(``problemStatement``) tells the arm what each component must do and how the
components depend on one another. The withheld acceptance suite (the hidden
``failToPass`` tests) decides resolution.

Components and their dependency graph (width + depth):

    tokenizer  ──►  normalizer  ──►  frequency  ──►  pipeline
        └───────────────────────────────────────────►  (pipeline also
                                                          calls tokenizer)

``pipeline`` orchestrates the other three, so it sits at the bottom of the
graph; ``frequency`` depends on both ``tokenizer`` and ``normalizer``.
"""

from __future__ import annotations

from text_toolkit.frequency import top_terms, word_counts
from text_toolkit.normalizer import normalize
from text_toolkit.pipeline import summarize
from text_toolkit.tokenizer import tokenize

__all__ = [
    "normalize",
    "summarize",
    "tokenize",
    "top_terms",
    "word_counts",
]
