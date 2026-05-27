"""The rubric-driven spec-conformance judge (Bucket 3).

Resolution is necessary but not sufficient: code can pass the hidden tests while
diverging from the spec (``06-scoring-and-statistics.md`` §The conformance judge;
``04-metrics.md`` §Bucket 3). This package scores how well an arm's FINAL code
satisfies the spec it was meant to implement, on a ``[0, 1]`` scale written to
``ScoreReport.conformanceScore``.

Two public surfaces:

- :mod:`benchmark.harness.scoring.conformance.judge` — the judge itself. A single
  HOST-SIDE, bounded ``claude -p`` call applies a structured conformance rubric to
  ``(spec_text, final_code)`` and returns a parsed, CLAMPED score plus a rationale
  (:func:`~benchmark.harness.scoring.conformance.judge.score_conformance`). The LLM
  backend is INJECTABLE so tests pass a deterministic mock; the live ``claude -p``
  call is the default. ``score_arm_conformance`` populates a
  :class:`~benchmark.harness.domain.ScoreReport` for one arm, applying the
  null-on-no-spec rule (only the ``greenfield`` suite supplies a spec).
- :mod:`benchmark.harness.scoring.conformance.calibration` — the calibration
  harness: a small hand-authored human-labelled sample plus an agreement
  computation (exact-bucket agreement + Cohen's kappa) used to report the judge's
  agreement figure against human labels.
"""

from __future__ import annotations

from benchmark.harness.scoring.conformance.calibration import (
    CALIBRATION_SAMPLE,
    MIN_CALIBRATION_AGREEMENT,
    MIN_CALIBRATION_SAMPLE_SIZE,
    AgreementReport,
    CalibrationItem,
    bucket_of,
    cohens_kappa,
    compute_agreement,
    run_calibration,
)
from benchmark.harness.scoring.conformance.judge import (
    CONFORMANCE_MAX_BUDGET_USD,
    CONFORMANCE_MODEL,
    CONFORMANCE_RUBRIC,
    JUDGE_TIMEOUT_SECONDS,
    SCORE_MAX,
    SCORE_MIN,
    ConformanceJudgeError,
    ConformanceResult,
    JudgeCallable,
    build_rubric_prompt,
    clamp_score,
    cli_judge,
    parse_judge_response,
    score_arm_conformance,
    score_conformance,
    suite_supplies_spec,
)

__all__ = [
    "CALIBRATION_SAMPLE",
    "CONFORMANCE_MAX_BUDGET_USD",
    "CONFORMANCE_MODEL",
    "CONFORMANCE_RUBRIC",
    "JUDGE_TIMEOUT_SECONDS",
    "MIN_CALIBRATION_AGREEMENT",
    "MIN_CALIBRATION_SAMPLE_SIZE",
    "SCORE_MAX",
    "SCORE_MIN",
    "AgreementReport",
    "CalibrationItem",
    "ConformanceJudgeError",
    "ConformanceResult",
    "JudgeCallable",
    "bucket_of",
    "build_rubric_prompt",
    "clamp_score",
    "cli_judge",
    "cohens_kappa",
    "compute_agreement",
    "parse_judge_response",
    "run_calibration",
    "score_arm_conformance",
    "score_conformance",
    "suite_supplies_spec",
]
