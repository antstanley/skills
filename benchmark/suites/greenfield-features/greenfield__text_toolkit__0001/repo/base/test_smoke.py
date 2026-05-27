"""Skeleton smoke test (passToPass): the package and its components import.

This test ships in the run-visible ``base/`` tree and PASSES on the skeleton as
delivered — it only asserts that every component module is importable and
exposes its public callables. It must KEEP passing after the arm implements the
library, so it doubles as the ``passToPass`` selector for this instance.
"""

from __future__ import annotations

import text_toolkit


def test_public_api_is_exposed() -> None:
    for name in ("tokenize", "normalize", "word_counts", "top_terms", "summarize"):
        assert callable(getattr(text_toolkit, name))


def test_component_modules_import() -> None:
    import text_toolkit.frequency  # noqa: F401
    import text_toolkit.normalizer  # noqa: F401
    import text_toolkit.pipeline  # noqa: F401
    import text_toolkit.tokenizer  # noqa: F401
