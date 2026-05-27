"""Scoring: the oracle runner and the shared resolution rule.

See ``06-scoring-and-statistics.md``. The resolution rule
(:mod:`benchmark.harness.scoring.resolution`) is backend-agnostic; the
``local`` ScoringBackend (:mod:`benchmark.harness.scoring.local`) runs the
hidden suite via a temp checkout + local ``pytest``, with no Docker.
"""

from __future__ import annotations

from benchmark.harness.scoring.local import (
    PYTEST_TIMEOUT_SECONDS,
    REPO_BASE_SUBDIR,
    REPO_HIDDEN_SUBDIR,
    SCORING_DIR_PREFIX,
    SCORING_TEMP_BASE,
    LocalScoringBackend,
    LocalScoringError,
)
from benchmark.harness.scoring.resolution import (
    derive_regressed,
    derive_resolved,
)

__all__ = [
    "PYTEST_TIMEOUT_SECONDS",
    "REPO_BASE_SUBDIR",
    "REPO_HIDDEN_SUBDIR",
    "SCORING_DIR_PREFIX",
    "SCORING_TEMP_BASE",
    "LocalScoringBackend",
    "LocalScoringError",
    "derive_regressed",
    "derive_resolved",
]
