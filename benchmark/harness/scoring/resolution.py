"""The shared, backend-agnostic resolution rule.

Single source of truth for how a per-selector pass/fail map becomes the
``resolved`` / ``regressed`` facts on a ``ScoreReport``
(``06-scoring-and-statistics.md`` → The test oracle). Both the ``container``
and the ``local`` ``ScoringBackend`` derive their verdict here, so the rule
stays identical across backends (``05-harness-architecture.md`` → Scoring
isolation; the resolution rule is "the same across backends").

Resolution (SWE-bench Pro convention): a candidate **resolves** iff *every*
``failToPass`` test passes AND *every* ``passToPass`` test still holds.
Regression: a ``passToPass`` test that no longer holds.
"""

from __future__ import annotations

from collections.abc import Mapping


def derive_resolved(
    fail_to_pass: Mapping[str, bool], pass_to_pass: Mapping[str, bool]
) -> bool:
    """True iff every ``failToPass`` passes AND every ``passToPass`` holds."""
    return all(fail_to_pass.values()) and all(pass_to_pass.values())


def derive_regressed(pass_to_pass: Mapping[str, bool]) -> bool:
    """True iff any ``passToPass`` test no longer holds (a regression)."""
    return any(not held for held in pass_to_pass.values())
