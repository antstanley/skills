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

from benchmark.harness.stats.ablation_report import (
    ABLATION_ARMS,
    APPLICABILITY,
    COST_MATCHED_DELTA_METRIC_PREFIX,
    HOLM_BONFERRONI_ALPHA,
    METRIC_COLUMNS,
    NA_RENDER_TOKEN,
    OUTCOME_AND_ARTIFACT_METRIC_NAMES,
    PAIRWISE_DELTAS,
    PLAN_PRODUCING_ARMS,
    AblationReport,
    ArmRow,
    CostMatchedDeltaRow,
    DeltaRow,
    ablation_metric_results,
    apply_holm_bonferroni,
    apply_holm_bonferroni_per_family,
    build_ablation_report,
    build_arm_row,
    cost_matched_delta_metric_result,
    holm_bonferroni_adjusted_pvalues,
    metric_applies,
    render_ablation_report,
)
from benchmark.harness.stats.artifact_metrics import (
    DagValidity,
    PlanCoverage,
    dag_validity,
    implemented_section_keys,
    in_scope_spec_sections,
    plan_coverage,
)
from benchmark.harness.stats.cost_robustness import (
    COST_ROBUSTNESS_METRIC_NAMES,
    DEFAULT_COST_BASIS,
    GATE_VERDICT_UNVERIFIED,
    METRIC_COST_MATCHED_RESOLVED,
    METRIC_GATE_RETRY_DEPTH,
    METRIC_MANUAL_PAUSE_RATE,
    METRIC_MERGE_CONFLICT_RATE,
    METRIC_PARALLEL_SPEEDUP,
    METRIC_REGRESSION_RATE,
    CostBasis,
    CostMatchedResolved,
    GateRetryDepth,
    ParallelSpeedup,
    cost_matched_resolved_for_arm,
    cost_robustness_metric_results,
    equal_budget_for_arms,
    gate_retry_depth_for_arm,
    manual_pause_rate,
    merge_conflict_rate,
    parallel_speedup_for_arm,
    regression_rate_for_arm,
)
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
    "ABLATION_ARMS",
    "APPLICABILITY",
    "CONFIDENCE_LEVEL",
    "COST_MATCHED_DELTA_METRIC_PREFIX",
    "COST_ROBUSTNESS_METRIC_NAMES",
    "DEFAULT_COST_BASIS",
    "GATE_VERDICT_UNVERIFIED",
    "HOLM_BONFERRONI_ALPHA",
    "MCNEMAR_EXACT_MAX_DISCORDANT",
    "METRIC_COLUMNS",
    "METRIC_COST_MATCHED_RESOLVED",
    "METRIC_GATE_RETRY_DEPTH",
    "METRIC_MANUAL_PAUSE_RATE",
    "METRIC_MERGE_CONFLICT_RATE",
    "METRIC_PARALLEL_SPEEDUP",
    "METRIC_REGRESSION_RATE",
    "NA_RENDER_TOKEN",
    "OUTCOME_AND_ARTIFACT_METRIC_NAMES",
    "PAIRWISE_DELTAS",
    "PLAN_PRODUCING_ARMS",
    "WILSON_Z_95",
    "AblationReport",
    "AblationTable",
    "ArmOutcome",
    "ArmRow",
    "ConfidenceInterval",
    "CostBasis",
    "CostMatchedDeltaRow",
    "CostMatchedResolved",
    "DagValidity",
    "DeltaRow",
    "GateRetryDepth",
    "McNemarResult",
    "ParallelSpeedup",
    "PlanCoverage",
    "ablation_metric_results",
    "ablation_table",
    "apply_holm_bonferroni",
    "apply_holm_bonferroni_per_family",
    "arm_outcome",
    "build_ablation_report",
    "build_arm_row",
    "cost_matched_delta_metric_result",
    "cost_matched_resolved_for_arm",
    "cost_robustness_metric_results",
    "dag_validity",
    "equal_budget_for_arms",
    "gate_retry_depth_for_arm",
    "group_resolved_by_instance",
    "holm_bonferroni_adjusted_pvalues",
    "implemented_section_keys",
    "in_scope_spec_sections",
    "manual_pause_rate",
    "mcnemar_delta",
    "merge_conflict_rate",
    "metric_applies",
    "parallel_speedup_for_arm",
    "pass_at_1",
    "pass_at_k",
    "plan_coverage",
    "regression_rate",
    "regression_rate_for_arm",
    "render_ablation_report",
    "render_ablation_table",
    "wilson_interval",
]
