"""Stats: Pass@k, pairwise deltas, and confidence intervals over score reports.

This module turns the per-Trial ``ScoreReport``s of a ``CampaignRun`` into the
per-arm outcome statistics and the A1-vs-A0 ablation table defined in
``docs/benchmark/specs/06-scoring-and-statistics.md`` (§Repetition and Pass@k,
§Confidence intervals and pairwise tests, §Reporting) and
``docs/benchmark/specs/04-metrics.md`` (§Bucket 1 — Outcome).

The quantities, with their authority:

- **Pass@1** (``04-metrics.md`` §Bucket 1, ``06`` §Repetition and Pass@k): mean
  ``resolved`` over an arm's single scored trials — the headline outcome.
- **Pass@k** (same sections): fraction of *instances* for which at least one of
  the arm's ``k`` trials on that instance resolved.
- **Regression rate** (``04`` §Bucket 1): fraction of scored trials whose
  ``regressed`` is true.
- **95% binomial CI** (``06`` §Confidence intervals and pairwise tests): the
  Wilson score interval — closed-form, robust at small ``n`` and near 0/1.
- **A1−A0 paired delta** (``06`` §Confidence intervals): McNemar's test on the
  discordant pairs over the instances both arms ran.
- **Ablation table** (``06`` §Reporting): a per-arm table with the metric
  columns plus the A1−A0 delta row carrying the McNemar result.

Only ``scored`` trials enter the statistics; ``failed`` (infra) trials are
excluded (``06`` §Repetition and Pass@k). No scipy/numpy — stdlib ``math`` only.
"""

from __future__ import annotations

from benchmark.harness.stats.outcome import (
    CONFIDENCE_LEVEL,
    MCNEMAR_EXACT_MAX_DISCORDANT,
    WILSON_Z_95,
    AblationTable,
    ArmOutcome,
    ConfidenceInterval,
    McNemarResult,
    ablation_table,
    arm_outcome,
    group_resolved_by_instance,
    mcnemar_delta,
    pass_at_1,
    pass_at_k,
    regression_rate,
    render_ablation_table,
    wilson_interval,
)

__all__ = [
    "CONFIDENCE_LEVEL",
    "MCNEMAR_EXACT_MAX_DISCORDANT",
    "WILSON_Z_95",
    "AblationTable",
    "ArmOutcome",
    "ConfidenceInterval",
    "McNemarResult",
    "ablation_table",
    "arm_outcome",
    "group_resolved_by_instance",
    "mcnemar_delta",
    "pass_at_1",
    "pass_at_k",
    "regression_rate",
    "render_ablation_table",
    "wilson_interval",
]
