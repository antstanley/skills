"""Backends: pluggable RunBackend / ScoringBackend (container + local).

Defined by ``changes/2026-05-27-local_backends.md``; the driver, scorer rule,
and statistics are agnostic to how a Trial is run and scored.
"""

from __future__ import annotations

from benchmark.harness.backends.interfaces import (
    HIDDEN_TEST_FIELDS,
    ArmOrSolver,
    CandidatePatch,
    RunBackend,
    ScoringBackend,
)

__all__ = [
    "HIDDEN_TEST_FIELDS",
    "ArmOrSolver",
    "CandidatePatch",
    "RunBackend",
    "ScoringBackend",
]
