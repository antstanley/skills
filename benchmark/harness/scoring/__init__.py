"""Scoring: the oracle runner and the shared resolution rule.

See ``06-scoring-and-statistics.md``. The resolution rule
(:mod:`benchmark.harness.scoring.resolution`) is backend-agnostic; the
``local`` ScoringBackend (:mod:`benchmark.harness.scoring.local`) runs the
hidden suite via a temp checkout + local ``pytest``, with no Docker; the
``container`` ScoringBackend (:mod:`benchmark.harness.scoring.container`) runs
the same hidden suite in a fresh container built from the greenfield SCORING
image (the ``greenfield-hidden-tests`` convention). Both single-source their
``resolved`` / ``regressed`` verdict through the shared resolution rule.

Alongside the test oracle, the ``conformance`` subpackage
(:mod:`benchmark.harness.scoring.conformance`) supplies the rubric-driven LLM
conformance judge (``06-scoring-and-statistics.md`` §The conformance judge):
resolution is necessary but not sufficient, so the judge scores how well an arm's
final code satisfies the spec onto ``ScoreReport.conformanceScore`` in ``[0, 1]``,
calibrated against a small human-labelled sample.
"""

from __future__ import annotations

from benchmark.harness.scoring.conformance import (
    CONFORMANCE_MAX_BUDGET_USD,
    CONFORMANCE_RUBRIC,
    MIN_CALIBRATION_AGREEMENT,
    MIN_CALIBRATION_SAMPLE_SIZE,
    AgreementReport,
    ConformanceJudgeError,
    ConformanceResult,
    compute_agreement,
    run_calibration,
    score_arm_conformance,
    score_conformance,
    suite_supplies_spec,
)
from benchmark.harness.scoring.container import (
    SCORE_CONTAINER_TIMEOUT_SECONDS,
    ContainerScoringBackend,
    ContainerScoringError,
)
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
    "CONFORMANCE_MAX_BUDGET_USD",
    "CONFORMANCE_RUBRIC",
    "MIN_CALIBRATION_AGREEMENT",
    "MIN_CALIBRATION_SAMPLE_SIZE",
    "PYTEST_TIMEOUT_SECONDS",
    "REPO_BASE_SUBDIR",
    "REPO_HIDDEN_SUBDIR",
    "SCORE_CONTAINER_TIMEOUT_SECONDS",
    "SCORING_DIR_PREFIX",
    "SCORING_TEMP_BASE",
    "AgreementReport",
    "ConformanceJudgeError",
    "ConformanceResult",
    "ContainerScoringBackend",
    "ContainerScoringError",
    "LocalScoringBackend",
    "LocalScoringError",
    "compute_agreement",
    "derive_regressed",
    "derive_resolved",
    "run_calibration",
    "score_arm_conformance",
    "score_conformance",
    "suite_supplies_spec",
]
