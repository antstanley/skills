"""The full five-arm ablation table (the M4 capstone).

Implements ``docs/benchmark/specs/06-scoring-and-statistics.md`` §Reporting and
``docs/benchmark/specs/02-arms.md`` §The pairwise deltas. The output is the
campaign-level **ablation table**:

* one row per arm (A0..A4), one column per metric (Pass@1, Pass@k, cost-matched
  Pass@1, regression rate, conformance, plan coverage, DAG validity, gate catch
  rate, false-``Done`` escape rate, cost/efficiency means, robustness columns),
  each cell a value with its 95% interval where applicable;
* four pairwise-delta rows — **A1−A0, A1−A2, A2−A3, A1−A4** — each carrying the
  paired-McNemar Δ%Resolved, the McNemar statistic + p-value, the discordant
  (b, c), and a Holm-Bonferroni-adjusted p-value flagged against α = 0.05.

Cells for metrics that **do not apply** to an arm (gate catch/escape on A0/A4
which run no gates; plan coverage / DAG validity on A0/A4 which produce no
plan) are encoded as ``None`` in the dataclass and rendered as ``N/A`` — never
as ``0.0``. The applicability of every (metric, arm) pair is a named table
below (:data:`APPLICABILITY`).

Multiple-comparison correction (PINNED)
---------------------------------------
With four planned deltas per campaign, omitting a multiple-comparison
correction is not honest — at α = 0.05 the family-wise error rate over four
independent tests is roughly ``1 - 0.95^4 ≈ 0.185``. We apply the
**Holm-Bonferroni step-down procedure** (Holm 1979, "A Simple Sequentially
Rejective Multiple Test Procedure", *Scandinavian Journal of Statistics*) at
α = 0.05 (:data:`HOLM_BONFERRONI_ALPHA`).

Why Holm-Bonferroni: it is *uniformly more powerful* than plain Bonferroni at
the same family-wise error rate (FWER), is parameter-free, makes no assumption
about dependence between the comparisons (so it remains valid even though the
four deltas share arms), and is the textbook default for a small fixed family
of planned comparisons. It produces an adjusted p-value and a binary
significant-at-α flag per delta — both attached to every delta row.

The procedure, on a family of ``m`` p-values:

1. Sort the p-values ascending: ``p_(1) ≤ p_(2) ≤ ... ≤ p_(m)``.
2. Each ``p_(i)`` is compared to ``α / (m - i + 1)``: ``α/m`` for the smallest,
   ``α/(m-1)`` for the next, ..., ``α/1`` for the largest.
3. Reject ``H_(i)`` iff ``p_(j) ≤ α / (m - j + 1)`` for *every* ``j ≤ i``
   (step-down stop-at-first-failure rule).
4. The adjusted p-value of the i-th smallest is
   ``min(1, max_{j ≤ i} (m - j + 1) · p_(j))`` — monotone non-decreasing in
   ``i`` so the rejection threshold is consistent with the step-down rule.

This module is PURE computation: given a CampaignRun and the optional per-arm
auxiliary inputs, it deterministically assembles the table and renders it.
No I/O, no API calls.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from benchmark.harness.domain import (
    ARM_SLUGS,
    METRIC_RESULT_ID_PREFIX,
    MetricResult,
    new_record_id,
)
from benchmark.harness.stats.artifact_metrics import (
    DagValidity,
    PlanCoverage,
    dag_validity,
    plan_coverage,
)
from benchmark.harness.stats.cost_robustness import (
    DEFAULT_COST_BASIS,
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
)
from benchmark.harness.stats.outcome import (
    CONFIDENCE_LEVEL,
    ArmOutcome,
    ConfidenceInterval,
    McNemarResult,
    arm_outcome,
    mcnemar_delta,
)
from benchmark.harness.stats.outcome import (
    _arm_instance_resolved as _arm_instance_resolved_outcome,
)
from benchmark.harness.stats.outcome import (
    _scored_reports_for_arm as _scored_reports_for_arm_outcome,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from benchmark.harness.domain import ScoreReport
    from benchmark.harness.driver import CampaignRun, TrialResult


# --- named limits / constants ----------------------------------------------

#: The set of arm slugs the ablation table reports on, in column order: the
#: A0–A4 PAIRWISE-DELTA arms (``02-arms.md`` §The pairwise deltas). This is the
#: closed delta set, NOT every ``domain.ARM_SLUGS`` member: A5 is a lighter
#: pre-canned variant added for gate-emission verification / a cheaper cost point
#: and sits OUTSIDE the pairwise-delta chain (``02-arms.md`` §Decisions → *Six
#: arms*), so it is excluded from the ablation table's delta rows. Derived from
#: ``ARM_SLUGS`` (minus the non-delta arms) so the two stay in lockstep on the
#: shared members.
_NON_DELTA_ARMS: frozenset[str] = frozenset({"A5"})
ABLATION_ARMS: tuple[str, ...] = tuple(
    slug for slug in ARM_SLUGS if slug not in _NON_DELTA_ARMS
)

#: The four planned pairwise comparisons (``02-arms.md`` §The pairwise deltas).
#: Each entry is ``(treatment, baseline, label, isolates)``. The label is the
#: row title; ``isolates`` is the one-line reading from the spec table.
PAIRWISE_DELTAS: tuple[tuple[str, str, str, str], ...] = (
    (
        "A1",
        "A0",
        "A1−A0",
        "The whole workflow vs a plain agent (headline)",
    ),
    (
        "A1",
        "A2",
        "A1−A2",
        "Spec authoring",
    ),
    (
        "A2",
        "A3",
        "A2−A3",
        "The two gates",
    ),
    (
        "A1",
        "A4",
        "A1−A4",
        "Structured workflow vs equal-budget raw parallelism",
    ),
)

#: The plan-producing arms — they produce a plan + per-task files, so plan
#: coverage and DAG validity apply (``04-metrics.md`` §Bucket 3, ``02-arms.md``
#: §The arms). A0 runs a single agent, A4 a naive split: neither produces a plan.
PLAN_PRODUCING_ARMS: tuple[str, ...] = ("A1", "A2", "A3")

#: The gated arms — gates are on, so catch rate and escape rate apply
#: (``benchmark.harness.scoring.probes.GATED_ARMS`` is the same set). A3 turns
#: gates off, A0/A4 have none.
GATED_ARMS: tuple[str, ...] = ("A1", "A2")

#: The family-wise error rate the Holm-Bonferroni step-down procedure targets.
#: 0.05 is the conventional default; named so the choice is explicit at every
#: call site (Holm 1979).
HOLM_BONFERRONI_ALPHA: float = 0.05

#: Token for a cell that does not apply to its arm. Encoded as ``None`` in the
#: dataclass; the renderer emits this string in its place. Distinguished from
#: an actual 0.0 — a metric an arm WOULD report but happens to be zero.
NA_RENDER_TOKEN: str = "N/A"

#: Header note: the cost-matching basis the table reports against. Stated at the
#: top of every rendered table so a reader does not have to guess (the basis is
#: PINNED to dollars in :mod:`benchmark.harness.stats.cost_robustness`).
_COST_BASIS_HEADER_PREFIX = "Cost-matching basis"


# --- applicability table ----------------------------------------------------

#: Metric-column identifiers (machine-readable, stable names).
METRIC_PASS_AT_1 = "pass_at_1"
METRIC_PASS_AT_K = "pass_at_k"
METRIC_REGRESSION_RATE = "regression_rate"
METRIC_COST_MATCHED_RESOLVED = "cost_matched_resolved"
METRIC_MEAN_TOKENS = "mean_tokens"
METRIC_MEAN_COST_USD = "mean_cost_usd"
METRIC_MEAN_WALL_CLOCK = "mean_wall_clock_seconds"
METRIC_PARALLEL_SPEEDUP = "parallel_speedup"
METRIC_CONFORMANCE = "conformance"
METRIC_PLAN_COVERAGE = "plan_coverage"
METRIC_DAG_VALIDITY = "dag_validity"
METRIC_GATE_CATCH_RATE = "gate_catch_rate"
METRIC_GATE_ESCAPE_RATE = "gate_escape_rate"
METRIC_MERGE_CONFLICT_RATE = "merge_conflict_rate"
METRIC_MANUAL_PAUSE_RATE = "manual_pause_rate"
METRIC_GATE_RETRY_DEPTH = "gate_retry_depth"

#: Every metric column in the table, in render order.
METRIC_COLUMNS: tuple[str, ...] = (
    METRIC_PASS_AT_1,
    METRIC_PASS_AT_K,
    METRIC_REGRESSION_RATE,
    METRIC_COST_MATCHED_RESOLVED,
    METRIC_MEAN_TOKENS,
    METRIC_MEAN_COST_USD,
    METRIC_MEAN_WALL_CLOCK,
    METRIC_PARALLEL_SPEEDUP,
    METRIC_CONFORMANCE,
    METRIC_PLAN_COVERAGE,
    METRIC_DAG_VALIDITY,
    METRIC_GATE_CATCH_RATE,
    METRIC_GATE_ESCAPE_RATE,
    METRIC_MERGE_CONFLICT_RATE,
    METRIC_MANUAL_PAUSE_RATE,
    METRIC_GATE_RETRY_DEPTH,
)

#: The ten metric names that :func:`ablation_metric_results` emits IN ADDITION
#: to the six emitted by :func:`cost_robustness_metric_results` — the outcome
#: columns (Pass@1, Pass@k), the cost/efficiency means, conformance, and the
#: plan + gate artifact metrics. The universe of ablation-table metrics is
#: exactly
#: ``COST_ROBUSTNESS_METRIC_NAMES + OUTCOME_AND_ARTIFACT_METRIC_NAMES``,
#: which equals (as a set) :data:`METRIC_COLUMNS` — asserted in tests so the
#: two paths cannot drift. The split mirrors the file layout: the
#: cost-robustness metrics live in :mod:`benchmark.harness.stats.cost_robustness`
#: and the rest are derived here from the :class:`ArmRow` the renderer reads.
OUTCOME_AND_ARTIFACT_METRIC_NAMES: tuple[str, ...] = (
    METRIC_PASS_AT_1,
    METRIC_PASS_AT_K,
    METRIC_MEAN_TOKENS,
    METRIC_MEAN_COST_USD,
    METRIC_MEAN_WALL_CLOCK,
    METRIC_CONFORMANCE,
    METRIC_PLAN_COVERAGE,
    METRIC_DAG_VALIDITY,
    METRIC_GATE_CATCH_RATE,
    METRIC_GATE_ESCAPE_RATE,
)


def _arms_set(arms: tuple[str, ...]) -> frozenset[str]:
    return frozenset(arms)


#: The applicability table: per (metric, arm) → does this metric apply?
#:
#: A metric is APPLICABLE when the arm could in principle produce it. Plan
#: coverage and DAG validity require a plan to exist (A1/A2/A3 only). Gate
#: catch and gate escape require gates to run (A1/A2 only — A3 turns them off,
#: A0/A4 have none). Every other metric applies to every arm.
#:
#: Stored as ``metric → frozenset of arms where it applies`` so look-ups are
#: O(1) and the table is small and readable. Every entry exhaustively covers
#: :data:`METRIC_COLUMNS`; the renderer asserts on lookup.
APPLICABILITY: dict[str, frozenset[str]] = {
    METRIC_PASS_AT_1: _arms_set(ABLATION_ARMS),
    METRIC_PASS_AT_K: _arms_set(ABLATION_ARMS),
    METRIC_REGRESSION_RATE: _arms_set(ABLATION_ARMS),
    METRIC_COST_MATCHED_RESOLVED: _arms_set(ABLATION_ARMS),
    METRIC_MEAN_TOKENS: _arms_set(ABLATION_ARMS),
    METRIC_MEAN_COST_USD: _arms_set(ABLATION_ARMS),
    METRIC_MEAN_WALL_CLOCK: _arms_set(ABLATION_ARMS),
    METRIC_PARALLEL_SPEEDUP: _arms_set(ABLATION_ARMS),
    METRIC_CONFORMANCE: _arms_set(ABLATION_ARMS),
    METRIC_PLAN_COVERAGE: _arms_set(PLAN_PRODUCING_ARMS),
    METRIC_DAG_VALIDITY: _arms_set(PLAN_PRODUCING_ARMS),
    METRIC_GATE_CATCH_RATE: _arms_set(GATED_ARMS),
    METRIC_GATE_ESCAPE_RATE: _arms_set(GATED_ARMS),
    METRIC_MERGE_CONFLICT_RATE: _arms_set(ABLATION_ARMS),
    METRIC_MANUAL_PAUSE_RATE: _arms_set(ABLATION_ARMS),
    METRIC_GATE_RETRY_DEPTH: _arms_set(ABLATION_ARMS),
}


def metric_applies(metric: str, arm: str) -> bool:
    """Whether ``metric`` applies to ``arm`` per the applicability table.

    A metric that does NOT apply renders as ``N/A``, NOT ``0.0`` — a metric an
    arm cannot produce is distinct from a metric the arm produces with a zero
    value (e.g. zero conflicts vs no gates to even produce catches).
    """
    if metric not in APPLICABILITY:
        raise KeyError(f"unknown metric column: {metric!r}")
    return arm in APPLICABILITY[metric]


# --- result records ---------------------------------------------------------


@dataclass(frozen=True)
class ArmRow:
    """One arm's row in the ablation table.

    Per-metric fields are either a populated record (with a point estimate and
    a CI when applicable) or ``None`` when the metric does not apply to this
    arm — encoded distinctly from a zero value. The dataclass is the structured
    API; the renderer turns it into Markdown.
    """

    arm: str
    n_trials: int
    n_instances: int
    pass_at_1: ConfidenceInterval | None
    pass_at_k: float | None
    regression_rate: ConfidenceInterval | None
    cost_matched_resolved: CostMatchedResolved | None
    mean_input_output_tokens: float | None
    mean_cost_usd: float | None
    mean_wall_clock_seconds: float | None
    parallel_speedup: ParallelSpeedup | None
    conformance: ConfidenceInterval | None
    plan_coverage: PlanCoverage | None
    dag_validity: DagValidity | None
    gate_catch_rate: ConfidenceInterval | None
    gate_escape_rate: ConfidenceInterval | None
    merge_conflict_rate: ConfidenceInterval | None
    manual_pause_rate: ConfidenceInterval | None
    gate_retry_depth: GateRetryDepth | None


@dataclass(frozen=True)
class DeltaRow:
    """One pairwise-delta row, with the Holm-Bonferroni adjustment attached.

    ``adjusted_p`` is the Holm-Bonferroni adjusted p-value (monotone over the
    four deltas); ``significant_at_alpha`` is the binary decision against
    :data:`HOLM_BONFERRONI_ALPHA`. Both are populated by
    :func:`apply_holm_bonferroni` over the four deltas of a campaign.
    """

    label: str
    treatment: str
    baseline: str
    isolates: str
    mcnemar: McNemarResult
    adjusted_p: float
    significant_at_alpha: bool
    alpha: float = HOLM_BONFERRONI_ALPHA
    confidence_level: float = CONFIDENCE_LEVEL


@dataclass(frozen=True)
class CostMatchedDeltaRow:
    """One pairwise cost-matched delta row.

    Same shape as :class:`DeltaRow` (label / arm pair / McNemar result + Holm-
    Bonferroni adjustment) PLUS the per-comparison equal-budget cap ``budget``
    on ``basis`` that defined "within budget" for both arms' instance bools.

    Cost-matched deltas are adjusted as a SEPARATE Holm-Bonferroni family from
    the raw deltas — see :func:`apply_holm_bonferroni_per_family` for the why.
    """

    label: str
    treatment: str
    baseline: str
    isolates: str
    mcnemar: McNemarResult
    adjusted_p: float
    significant_at_alpha: bool
    budget: float
    basis: CostBasis
    alpha: float = HOLM_BONFERRONI_ALPHA
    confidence_level: float = CONFIDENCE_LEVEL


@dataclass(frozen=True)
class AblationReport:
    """The full five-arm ablation table.

    ``arms`` carries one :class:`ArmRow` per arm in :data:`ABLATION_ARMS` order;
    ``deltas`` carries the four :class:`DeltaRow` rows in :data:`PAIRWISE_DELTAS`
    order with their Holm-Bonferroni-adjusted p-values;
    ``cost_matched_deltas`` carries the four :class:`CostMatchedDeltaRow` rows
    in the same order, each with its per-comparison equal budget;
    ``cost_basis`` is the basis the cost-matched %Resolved is computed against
    (DOLLARS by default). ``budget`` is the equal-budget cap derived from
    *all five arms*' costs — distinct from the per-comparison budgets on
    each :class:`CostMatchedDeltaRow` (which are derived from the two arms in
    that comparison only, per the spec's "equalising the budget across the two
    arms" reading).
    """

    arms: tuple[ArmRow, ...]
    deltas: tuple[DeltaRow, ...]
    cost_basis: CostBasis
    budget: float
    cost_matched_deltas: tuple[CostMatchedDeltaRow, ...] = ()
    alpha: float = HOLM_BONFERRONI_ALPHA
    metric_columns: tuple[str, ...] = field(default=METRIC_COLUMNS)


# --- Holm-Bonferroni correction ---------------------------------------------


def holm_bonferroni_adjusted_pvalues(
    p_values: Sequence[float],
) -> tuple[float, ...]:
    """Holm-Bonferroni adjusted p-values for a fixed family of ``m`` tests.

    The procedure on the family ``p_1, ..., p_m`` (in the input order):

    1. Sort the p-values ascending: ``p_(1) ≤ p_(2) ≤ ... ≤ p_(m)``.
    2. Compute ``q_(i) = (m - i + 1) · p_(i)``.
    3. Make the sequence monotone non-decreasing:
       ``adj_(i) = min(1, max_{j ≤ i} q_(j))``.
    4. Re-permute back to the input order.

    Step (3) is what makes ``adj`` consistent with the step-down decision rule:
    a hypothesis is rejected at level α iff ``adj_i ≤ α``, which is iff
    ``p_(j) ≤ α / (m - j + 1)`` for every ``j`` up to its sorted rank. The
    construction matches Holm 1979 §3 and is the standard textbook form.

    With ``m == 0`` the result is the empty tuple. With ``m == 1`` the adjusted
    p-value is the input p-value clamped at 1.0 — Holm-Bonferroni with a single
    test reduces to no correction.
    """
    m = len(p_values)
    if m == 0:
        return ()
    # Pair each p-value with its input index, then sort by p-value ascending.
    # ``sorted`` is stable, so ties keep input order for reproducibility.
    indexed = sorted(enumerate(p_values), key=lambda pair: pair[1])
    raw_q: list[float] = []
    for sorted_rank, (_, p_value) in enumerate(indexed):
        # i = sorted_rank + 1 (1-based); the factor is m - i + 1 = m - sorted_rank.
        factor = m - sorted_rank
        raw_q.append(factor * p_value)
    # Make monotone non-decreasing under the sorted order, then clamp at 1.
    running_max = 0.0
    monotone: list[float] = []
    for q in raw_q:
        running_max = max(running_max, q)
        monotone.append(min(1.0, running_max))
    # Permute back into input order.
    adjusted = [0.0] * m
    for sorted_rank, (input_index, _) in enumerate(indexed):
        adjusted[input_index] = monotone[sorted_rank]
    return tuple(adjusted)


def apply_holm_bonferroni(
    raw_deltas: Sequence[tuple[str, str, str, str, McNemarResult]],
    alpha: float = HOLM_BONFERRONI_ALPHA,
) -> tuple[DeltaRow, ...]:
    """Wrap McNemar results into :class:`DeltaRow`\\s with Holm-Bonferroni adjustment.

    Each input tuple is ``(label, treatment, baseline, isolates, mcnemar)``; the
    output tuple preserves the input order (which mirrors :data:`PAIRWISE_DELTAS`).
    The adjusted p-values are computed across the whole family, and a binary
    ``significant_at_alpha`` flag is attached per row.
    """
    p_values = [row[4].p_value for row in raw_deltas]
    adjusted = holm_bonferroni_adjusted_pvalues(p_values)
    return tuple(
        DeltaRow(
            label=label,
            treatment=treatment,
            baseline=baseline,
            isolates=isolates,
            mcnemar=mcnemar,
            adjusted_p=adj_p,
            significant_at_alpha=adj_p <= alpha,
            alpha=alpha,
        )
        for (label, treatment, baseline, isolates, mcnemar), adj_p in zip(
            raw_deltas, adjusted, strict=True
        )
    )


def apply_holm_bonferroni_per_family(
    raw_p_values: Sequence[float],
    cost_matched_p_values: Sequence[float],
    alpha: float = HOLM_BONFERRONI_ALPHA,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Adjust two pairwise-delta families SEPARATELY via Holm-Bonferroni.

    Two families: the raw paired-McNemar deltas (one per comparison) and the
    cost-matched paired-McNemar deltas (one per comparison). They answer two
    distinct questions about the same arm pair:

    * the **raw** family asks "does the treatment resolve more instances than
      the baseline at whatever spend each arm naturally drew?";
    * the **cost-matched** family asks "does it still resolve more once both
      arms are capped at the equal-budget cheaper arm's max?".

    Adjusting them as ONE family of eight conflates these two questions and
    weakens a marginal cost-matched signal whenever the raw family is strong
    (and vice versa). The spec calls the cost-matched delta out as a SEPARATE
    column in the §Confidence intervals and pairwise tests table; treating it
    as a separate family preserves that distinction at correction time. The
    eight-test alternative is statistically more conservative but conflates
    the two readings.

    Each family carries four planned comparisons (:data:`PAIRWISE_DELTAS`), so
    the within-family family-wise error rate stays at ``α = 0.05`` per the
    spec's pinned default. Returns ``(adjusted_raw, adjusted_cost_matched)`` in
    the same input order as :func:`holm_bonferroni_adjusted_pvalues`.
    """
    _ = alpha  # The alpha is encoded by the caller's significant-at-α decision.
    raw_adj = holm_bonferroni_adjusted_pvalues(raw_p_values)
    cost_adj = holm_bonferroni_adjusted_pvalues(cost_matched_p_values)
    return raw_adj, cost_adj


# --- per-arm slicing helpers -------------------------------------------------


def _arm_scored_results(run: CampaignRun, arm: str) -> list[TrialResult]:
    """The arm's scored TrialResults, in stable driver order."""
    return [r for r in run.scored_results if r.trial.arm == arm]


def _conformance_ci_for_arm(
    reports: Sequence[ScoreReport],
) -> ConfidenceInterval | None:
    """Mean ``conformanceScore`` over an arm's scored reports, with a normal-CI.

    Conformance is on ``[0, 1]`` and applies to every arm on greenfield (each
    arm produces final code judged against the same spec). The mean is the
    arm-level point estimate; the CI is the normal-approximation 95% interval
    on the mean, ``mean ± z · sd / sqrt(n)``, valid for ``n ≥ 2``. With ``n < 2``
    we report the point value in both bounds. With no scored reports carrying a
    conformance score we return ``None`` (the judge was not run for any trial of
    the arm — distinct from a zero score).
    """
    scores = [
        float(r.conformanceScore) for r in reports if r.conformanceScore is not None
    ]
    n = len(scores)
    if n == 0:
        return None
    mean = math.fsum(scores) / n
    if n < 2:
        return ConfidenceInterval(point=mean, low=mean, high=mean)
    variance = math.fsum((s - mean) ** 2 for s in scores) / (n - 1)
    sd = math.sqrt(variance)
    # Reuse the Wilson-z for the 95% interval (same critical value).
    from benchmark.harness.stats.outcome import WILSON_Z_95

    half = WILSON_Z_95 * sd / math.sqrt(n)
    return ConfidenceInterval(
        point=mean,
        low=max(0.0, mean - half),
        high=min(1.0, mean + half),
    )


def _telemetry_means(
    arm_results: Sequence[TrialResult],
) -> tuple[float | None, float | None, float | None]:
    """Mean (tokens, cost_usd, wall_clock_seconds) over an arm's scored trials.

    With no trials carrying telemetry the means are ``None``.
    """
    tokens: list[float] = []
    cost: list[float] = []
    wall: list[float] = []
    for r in arm_results:
        if r.bundle is None:
            continue
        tel = r.bundle.telemetry
        tokens.append(float(tel.inputTokens + tel.outputTokens))
        cost.append(float(tel.costUsd))
        wall.append(float(tel.wallClockSeconds))
    if not tokens:
        return None, None, None
    n = float(len(tokens))
    return (
        math.fsum(tokens) / n,
        math.fsum(cost) / n,
        math.fsum(wall) / n,
    )


def _wilson_or_none(
    successes: int, total: int, applies: bool
) -> ConfidenceInterval | None:
    """Wilson interval, or ``None`` when the metric does not apply.

    Returning ``None`` when ``not applies`` is the rule that distinguishes a
    non-applicable cell from a zero-rate cell.
    """
    if not applies:
        return None
    # Local import avoids a cycle on module import order with outcome.py.
    from benchmark.harness.stats.outcome import wilson_interval

    return wilson_interval(successes, total)


# --- public assembly entry points -------------------------------------------


def build_arm_row(
    run: CampaignRun,
    arm: str,
    *,
    cost_basis: CostBasis,
    budget: float,
    spec_artifacts: Mapping[str, Sequence[str]] | None = None,
    plan_artifacts: Mapping[str, Sequence[str]] | None = None,
    plan_graph_widths: Mapping[str, int] | None = None,
    gate_catch_counts: Mapping[str, tuple[int, int]] | None = None,
    gate_escape_counts: Mapping[str, tuple[int, int]] | None = None,
    merge_conflict_counts: Mapping[str, int] | None = None,
) -> ArmRow:
    """Assemble one arm's :class:`ArmRow` for the ablation table.

    Parameters
    ----------
    run:
        The CampaignRun whose scored results to read.
    arm:
        The arm slug; must be in :data:`ABLATION_ARMS`.
    cost_basis:
        Cost basis for the cost-matched %Resolved (DOLLARS by default).
    budget:
        Equal-budget cap on ``cost_basis``.
    spec_artifacts:
        Optional mapping ``arm → captured spec entries`` (``"<relpath>\\n<body>"``).
        Used to compute plan coverage for the plan-producing arms.
    plan_artifacts:
        Optional mapping ``arm → captured plan entries``. Used for plan
        coverage and DAG validity.
    plan_graph_widths:
        Optional mapping ``arm → graph width`` for the parallel-speedup row.
    gate_catch_counts:
        Optional mapping ``arm → (caught, total)`` for the gate catch rate.
        Distinct from "no gates ran": a gated arm with zero injected defects
        contributes (0, 0) — the metric still applies but the rate is undefined.
    gate_escape_counts:
        Optional mapping ``arm → (escaped, total)`` for the escape rate.
    merge_conflict_counts:
        Optional mapping ``trial-id → conflict count`` for the merge-conflict
        rate (matches the cost_robustness signature).
    """
    if arm not in ABLATION_ARMS:
        raise ValueError(f"arm {arm!r} not in {ABLATION_ARMS}")

    arm_results = _arm_scored_results(run, arm)
    n_trials = len(arm_results)
    reports = _scored_reports_for_arm_outcome(run, arm)

    # Outcome columns (always apply).
    outcome: ArmOutcome = arm_outcome(run, arm)

    # Cost-matched %Resolved (always applies — even A0/A4 produce a basis).
    cmr = (
        cost_matched_resolved_for_arm(arm, arm_results, budget=budget, basis=cost_basis)
        if n_trials
        else None
    )

    # Cost/efficiency means (always apply).
    mean_tokens, mean_cost, mean_wall = _telemetry_means(arm_results)

    # Parallel speedup (always applies; meaningful for A1/A4 where the graph
    # has width > 1).
    width = plan_graph_widths.get(arm) if plan_graph_widths is not None else None
    speedup = parallel_speedup_for_arm(arm, arm_results, graph_width=width)

    # Conformance (greenfield) — always applies; ``None`` when no trial scored.
    conformance = _conformance_ci_for_arm(reports)

    # Plan-producing arms: plan coverage + DAG validity (else None).
    plan_cov: PlanCoverage | None = None
    dag_val: DagValidity | None = None
    if arm in PLAN_PRODUCING_ARMS:
        arm_plans = (
            list(plan_artifacts.get(arm, ())) if plan_artifacts is not None else []
        )
        arm_specs = (
            list(spec_artifacts.get(arm, ())) if spec_artifacts is not None else []
        )
        if arm_plans:
            plan_cov = plan_coverage(arm_specs, arm_plans)
            dag_val = dag_validity(arm_plans)

    # Gated arms: catch rate + escape rate (else None).
    gate_catch: ConfidenceInterval | None = None
    gate_escape: ConfidenceInterval | None = None
    if arm in GATED_ARMS:
        if gate_catch_counts is not None and arm in gate_catch_counts:
            caught, total = gate_catch_counts[arm]
            gate_catch = _wilson_or_none(caught, total, applies=True)
        if gate_escape_counts is not None and arm in gate_escape_counts:
            escaped, total = gate_escape_counts[arm]
            gate_escape = _wilson_or_none(escaped, total, applies=True)

    # Robustness columns (always apply).
    merge_ci = (
        merge_conflict_rate(arm_results, conflict_counts=merge_conflict_counts)
        if n_trials
        else None
    )
    pause_ci = manual_pause_rate(arm_results) if n_trials else None
    retry_depth = gate_retry_depth_for_arm(arm, arm_results) if n_trials else None

    return ArmRow(
        arm=arm,
        n_trials=n_trials,
        n_instances=outcome.n_instances,
        pass_at_1=outcome.pass_at_1 if n_trials else None,
        pass_at_k=outcome.pass_at_k if n_trials else None,
        regression_rate=outcome.regression_rate if n_trials else None,
        cost_matched_resolved=cmr,
        mean_input_output_tokens=mean_tokens,
        mean_cost_usd=mean_cost,
        mean_wall_clock_seconds=mean_wall,
        parallel_speedup=speedup if n_trials else None,
        conformance=conformance,
        plan_coverage=plan_cov,
        dag_validity=dag_val,
        gate_catch_rate=gate_catch,
        gate_escape_rate=gate_escape,
        merge_conflict_rate=merge_ci,
        manual_pause_rate=pause_ci,
        gate_retry_depth=retry_depth,
    )


def _arm_costs_for_pair(run: CampaignRun, arm: str, basis: CostBasis) -> list[float]:
    """Per-trial cost of an arm's scored trials on ``basis``.

    Mirrors the per-arm cost-list extraction in :func:`_budget_for_run`, isolated
    so the pairwise per-pair-budget derivation can reuse it without recomputing
    over all five arms. Skips results without an ArtifactBundle (defensive — the
    driver guarantees one for scored trials).
    """
    costs: list[float] = []
    for r in _arm_scored_results(run, arm):
        if r.bundle is None:
            continue
        tel = r.bundle.telemetry
        if basis is CostBasis.DOLLARS:
            costs.append(float(tel.costUsd))
        elif basis is CostBasis.TOKENS:
            costs.append(float(tel.inputTokens + tel.outputTokens))
        else:  # WALL_CLOCK
            costs.append(float(tel.wallClockSeconds))
    return costs


def _arm_instance_cost_matched_resolved(
    run: CampaignRun,
    arm: str,
    *,
    budget: float,
    basis: CostBasis,
) -> dict[str, bool]:
    """Per-instance bool: ``cost(trial) <= budget AND resolved`` for ANY trial.

    Cost-matched analogue of
    :func:`benchmark.harness.stats.outcome._arm_instance_resolved`. The pairing
    reduction is the same ``any``-over-trials rule
    (:func:`benchmark.harness.stats.outcome._instance_resolved_any`): an
    instance is "cost-matched resolved" for the arm iff any of the arm's
    trials on that instance both came in within budget AND reported resolved.

    The denominator of the McNemar pairing is the set of instances both arms
    scored — :func:`mcnemar_delta` intersects the two bool maps; a missing
    instance (the arm did not score it) is distinct from a False bool.
    """
    arm_results = _arm_scored_results(run, arm)
    by_instance: dict[str, list[bool]] = {}
    for result in arm_results:
        if result.report is None or result.bundle is None:
            continue
        tel = result.bundle.telemetry
        if basis is CostBasis.DOLLARS:
            cost = float(tel.costUsd)
        elif basis is CostBasis.TOKENS:
            cost = float(tel.inputTokens + tel.outputTokens)
        else:  # WALL_CLOCK
            cost = float(tel.wallClockSeconds)
        within_and_resolved = cost <= budget and result.report.resolved
        by_instance.setdefault(result.trial.taskInstance, []).append(
            within_and_resolved
        )
    # Same any-over-trials reduction _arm_instance_resolved uses.
    return {instance: any(trials) for instance, trials in by_instance.items()}


def _budget_for_run(run: CampaignRun, arms: Sequence[str], basis: CostBasis) -> float:
    """Derive the equal-budget cap from the requested arms' per-trial costs.

    Skips arms with no scored trials; if no arm has any, returns 0.0. The cap
    is the cheaper arm's maximum per-trial cost (see ``cost_robustness``).
    """
    arm_costs: dict[str, list[float]] = {}
    for arm in arms:
        results = _arm_scored_results(run, arm)
        costs: list[float] = []
        for r in results:
            if r.bundle is None:
                continue
            tel = r.bundle.telemetry
            if basis is CostBasis.DOLLARS:
                costs.append(float(tel.costUsd))
            elif basis is CostBasis.TOKENS:
                costs.append(float(tel.inputTokens + tel.outputTokens))
            else:  # WALL_CLOCK
                costs.append(float(tel.wallClockSeconds))
        if costs:
            arm_costs[arm] = costs
    if not arm_costs:
        return 0.0
    return equal_budget_for_arms(arm_costs)


def build_ablation_report(
    run: CampaignRun,
    *,
    cost_basis: CostBasis = DEFAULT_COST_BASIS,
    budget: float | None = None,
    spec_artifacts: Mapping[str, Sequence[str]] | None = None,
    plan_artifacts: Mapping[str, Sequence[str]] | None = None,
    plan_graph_widths: Mapping[str, int] | None = None,
    gate_catch_counts: Mapping[str, tuple[int, int]] | None = None,
    gate_escape_counts: Mapping[str, tuple[int, int]] | None = None,
    merge_conflict_counts: Mapping[str, int] | None = None,
    alpha: float = HOLM_BONFERRONI_ALPHA,
) -> AblationReport:
    """Build the full five-arm :class:`AblationReport` from a CampaignRun.

    Per-arm rows are assembled in :data:`ABLATION_ARMS` order; the four
    pairwise deltas (:data:`PAIRWISE_DELTAS`) are computed via the existing
    :func:`mcnemar_delta` then run through :func:`apply_holm_bonferroni` at
    ``alpha`` (default 0.05) — the resolved Open question of which multiple-
    comparison correction to apply.

    Arms that have no scored trials still produce a row (with ``None`` values
    on the outcome columns), so the table is structurally complete and a
    reviewer can see which arms were under-sampled. A delta whose treatment OR
    baseline has no scored trials is still produced — the McNemar n_pairs will
    be zero and its p-value 1.0; Holm-Bonferroni handles the trivial family.
    """
    if budget is None:
        budget = _budget_for_run(run, ABLATION_ARMS, cost_basis)

    arm_rows = tuple(
        build_arm_row(
            run,
            arm,
            cost_basis=cost_basis,
            budget=budget,
            spec_artifacts=spec_artifacts,
            plan_artifacts=plan_artifacts,
            plan_graph_widths=plan_graph_widths,
            gate_catch_counts=gate_catch_counts,
            gate_escape_counts=gate_escape_counts,
            merge_conflict_counts=merge_conflict_counts,
        )
        for arm in ABLATION_ARMS
    )

    raw_deltas: list[tuple[str, str, str, str, McNemarResult]] = []
    for treatment, baseline, label, isolates in PAIRWISE_DELTAS:
        base_resolved = _arm_instance_resolved_outcome(run, baseline)
        treat_resolved = _arm_instance_resolved_outcome(run, treatment)
        mcn = mcnemar_delta(base_resolved, treat_resolved)
        raw_deltas.append((label, treatment, baseline, isolates, mcn))

    deltas = apply_holm_bonferroni(raw_deltas, alpha=alpha)

    # Cost-matched deltas: one McNemar per pairwise comparison, where the
    # per-instance bool is "cost(trial) <= B AND resolved" at the SHARED equal
    # budget B derived from the two arms in the comparison only — the spec's
    # "equalising the budget across the two arms" reading. Built by the
    # single-source helper so :func:`ablation_metric_results` and the renderer
    # agree on every comparison's budget, McNemar result, and adjusted-p.
    # Holm-Bonferroni: raw and cost-matched are TWO SEPARATE families of four,
    # both at α — see :func:`apply_holm_bonferroni_per_family` for the why.
    cost_matched_deltas = _build_cost_matched_delta_rows(
        run, cost_basis=cost_basis, alpha=alpha
    )

    return AblationReport(
        arms=arm_rows,
        deltas=deltas,
        cost_basis=cost_basis,
        budget=budget,
        cost_matched_deltas=cost_matched_deltas,
        alpha=alpha,
    )


# --- MetricResult emission for every ablation column -----------------------
#
# ``cost_robustness_metric_results`` already emits a MetricResult per (arm, suite)
# for the six metrics in :data:`COST_ROBUSTNESS_METRIC_NAMES`. The remaining ten
# ablation-table columns (:data:`OUTCOME_AND_ARTIFACT_METRIC_NAMES`) need
# emitters too so the metric stream covers every column the renderer prints.
#
# The implementation rule (from ``04-metrics.md`` §Implementation layout and
# this task's spec): the :class:`ArmRow` value/CI is the SOURCE OF TRUTH, and
# the MetricResult is its serialised form. Each emitter therefore takes an
# already-built ``ArmRow`` and reads the column off it — no re-derivation of
# Wilson / normal-CI math, no second pass over the scored results. That keeps
# the metric stream and the rendered table exactly in agreement column-for-
# column, which is the agreement the spec calls for.
#
# Applicability is respected: when a metric does not apply to an arm (the
# corresponding ``ArmRow`` field is ``None`` per :data:`APPLICABILITY`) the
# emitter returns ``None`` and the top-level emitter drops the row from the
# stream. A non-applicable cell stays absent — never a zero with a wide CI.


def _metric_result(
    *,
    campaign: str,
    arm: str,
    suite: str,
    metric_name: str,
    value: float,
    ci_low: float,
    ci_high: float,
    n_trials: int,
) -> MetricResult:
    """Build one MetricResult with a fresh id, validated by the schema.

    Mirrors :func:`benchmark.harness.stats.cost_robustness._metric_result` —
    duplicated here (not imported) because the cost-robustness helper is
    module-private and this module already owns the ``ArmRow``-side emission.
    """
    return MetricResult(
        id=new_record_id(METRIC_RESULT_ID_PREFIX),
        campaign=campaign,
        arm=arm,
        suite=suite,
        metricName=metric_name,
        value=value,
        ciLow=ci_low,
        ciHigh=ci_high,
        nTrials=n_trials,
    )


def _emit_ci(
    *,
    campaign: str,
    arm: str,
    suite: str,
    metric_name: str,
    ci: ConfidenceInterval | None,
    n_trials: int,
) -> MetricResult | None:
    """Emit one MetricResult from a :class:`ConfidenceInterval`-bearing field.

    Returns ``None`` when the field is ``None`` — the field-is-None encoding
    of "metric does not apply to this arm" (per :data:`APPLICABILITY`); the
    top-level emitter then drops the row from the stream so the non-
    applicable cell stays absent rather than emitted as zero.
    """
    if ci is None:
        return None
    return _metric_result(
        campaign=campaign,
        arm=arm,
        suite=suite,
        metric_name=metric_name,
        value=ci.point,
        ci_low=ci.low,
        ci_high=ci.high,
        n_trials=n_trials,
    )


def _emit_scalar(
    *,
    campaign: str,
    arm: str,
    suite: str,
    metric_name: str,
    value: float | None,
    n_trials: int,
) -> MetricResult | None:
    """Emit one MetricResult for a scalar (no closed-form interval) column.

    Used for Pass@k (a fraction over instances, not a proportion of trials),
    the mean tokens / cost / wall-clock per trial, and DAG validity (encoded
    1.0 if valid, 0.0 if invalid). The point value is repeated in both
    ``ciLow`` / ``ciHigh`` — same convention the speedup emitter in
    :mod:`benchmark.harness.stats.cost_robustness` uses for the ratio:
    the schema requires the fields, and we report the point value in both
    bounds rather than fabricate a CI we do not have.
    """
    if value is None:
        return None
    return _metric_result(
        campaign=campaign,
        arm=arm,
        suite=suite,
        metric_name=metric_name,
        value=value,
        ci_low=value,
        ci_high=value,
        n_trials=n_trials,
    )


def pass_at_1_metric_result(
    *, campaign: str, arm: str, suite: str, row: ArmRow
) -> MetricResult | None:
    """Emit ``pass_at_1`` from an :class:`ArmRow` — the headline Pass@1 + Wilson CI."""
    return _emit_ci(
        campaign=campaign,
        arm=arm,
        suite=suite,
        metric_name=METRIC_PASS_AT_1,
        ci=row.pass_at_1,
        n_trials=row.n_trials,
    )


def pass_at_k_metric_result(
    *, campaign: str, arm: str, suite: str, row: ArmRow
) -> MetricResult | None:
    """Emit ``pass_at_k`` — fraction of instances resolved by ≥1 of ``k`` trials.

    Pass@k is a fraction over INSTANCES, not a proportion of trials, so the
    Wilson interval over n_trials does not apply; the point value is reported
    in both CI bounds (the source of truth is :attr:`ArmRow.pass_at_k`).
    """
    return _emit_scalar(
        campaign=campaign,
        arm=arm,
        suite=suite,
        metric_name=METRIC_PASS_AT_K,
        value=row.pass_at_k,
        n_trials=row.n_trials,
    )


def mean_tokens_metric_result(
    *, campaign: str, arm: str, suite: str, row: ArmRow
) -> MetricResult | None:
    """Emit ``mean_tokens`` — mean ``inputTokens + outputTokens`` per trial."""
    return _emit_scalar(
        campaign=campaign,
        arm=arm,
        suite=suite,
        metric_name=METRIC_MEAN_TOKENS,
        value=row.mean_input_output_tokens,
        n_trials=row.n_trials,
    )


def mean_cost_usd_metric_result(
    *, campaign: str, arm: str, suite: str, row: ArmRow
) -> MetricResult | None:
    """Emit ``mean_cost_usd`` — mean ``costUsd`` per trial."""
    return _emit_scalar(
        campaign=campaign,
        arm=arm,
        suite=suite,
        metric_name=METRIC_MEAN_COST_USD,
        value=row.mean_cost_usd,
        n_trials=row.n_trials,
    )


def mean_wall_clock_metric_result(
    *, campaign: str, arm: str, suite: str, row: ArmRow
) -> MetricResult | None:
    """Emit ``mean_wall_clock_seconds`` — mean orchestrator wall-clock per trial."""
    return _emit_scalar(
        campaign=campaign,
        arm=arm,
        suite=suite,
        metric_name=METRIC_MEAN_WALL_CLOCK,
        value=row.mean_wall_clock_seconds,
        n_trials=row.n_trials,
    )


def conformance_metric_result(
    *, campaign: str, arm: str, suite: str, row: ArmRow
) -> MetricResult | None:
    """Emit ``conformance`` — mean ``conformanceScore`` over the arm's reports."""
    return _emit_ci(
        campaign=campaign,
        arm=arm,
        suite=suite,
        metric_name=METRIC_CONFORMANCE,
        ci=row.conformance,
        n_trials=row.n_trials,
    )


def plan_coverage_metric_result(
    *, campaign: str, arm: str, suite: str, row: ArmRow
) -> MetricResult | None:
    """Emit ``plan_coverage`` — fraction of in-scope sections covered by ≥1 task.

    Applicability: returns ``None`` for non-plan-producing arms (A0, A4) per
    :data:`APPLICABILITY`. Plan coverage is the fraction
    ``len(covered) / len(in_scope)``; the schema requires ``ciLow`` /
    ``ciHigh``, and we report the point value in both bounds (no closed-form
    interval for a fraction over a fixed-cardinality denominator).
    """
    pc = row.plan_coverage
    if pc is None:
        return None
    return _emit_scalar(
        campaign=campaign,
        arm=arm,
        suite=suite,
        metric_name=METRIC_PLAN_COVERAGE,
        value=pc.fraction,
        n_trials=row.n_trials,
    )


def dag_validity_metric_result(
    *, campaign: str, arm: str, suite: str, row: ArmRow
) -> MetricResult | None:
    """Emit ``dag_validity`` — 1.0 if the plan DAG is valid, 0.0 otherwise.

    Applicability: returns ``None`` for non-plan-producing arms (A0, A4) per
    :data:`APPLICABILITY`. The boolean is encoded as 1.0/0.0 in ``value`` and
    both CI bounds (a bool has no interval).
    """
    dv = row.dag_validity
    if dv is None:
        return None
    return _emit_scalar(
        campaign=campaign,
        arm=arm,
        suite=suite,
        metric_name=METRIC_DAG_VALIDITY,
        value=1.0 if dv.valid else 0.0,
        n_trials=row.n_trials,
    )


def gate_catch_rate_metric_result(
    *, campaign: str, arm: str, suite: str, row: ArmRow
) -> MetricResult | None:
    """Emit ``gate_catch_rate`` — Wilson interval over ``caught / total`` defects.

    Applicability: returns ``None`` for non-gated arms (A0, A3, A4) per
    :data:`APPLICABILITY`, AND when a gated arm has no catch counts supplied
    (the same encoding the :class:`ArmRow` uses — the field is ``None``).
    """
    return _emit_ci(
        campaign=campaign,
        arm=arm,
        suite=suite,
        metric_name=METRIC_GATE_CATCH_RATE,
        ci=row.gate_catch_rate,
        n_trials=row.n_trials,
    )


def gate_escape_rate_metric_result(
    *, campaign: str, arm: str, suite: str, row: ArmRow
) -> MetricResult | None:
    """Emit ``gate_escape_rate`` — Wilson interval over false-``Done`` escapes.

    Applicability: returns ``None`` for non-gated arms (A0, A3, A4); same
    rule as :func:`gate_catch_rate_metric_result`.
    """
    return _emit_ci(
        campaign=campaign,
        arm=arm,
        suite=suite,
        metric_name=METRIC_GATE_ESCAPE_RATE,
        ci=row.gate_escape_rate,
        n_trials=row.n_trials,
    )


#: The ten ArmRow-derived emitters, keyed by their metric name. Iterated in
#: :data:`OUTCOME_AND_ARTIFACT_METRIC_NAMES` order by
#: :func:`ablation_metric_results` so the emission order is deterministic.
_OUTCOME_AND_ARTIFACT_EMITTERS: dict[
    str,
    Callable[..., MetricResult | None],
] = {
    METRIC_PASS_AT_1: pass_at_1_metric_result,
    METRIC_PASS_AT_K: pass_at_k_metric_result,
    METRIC_MEAN_TOKENS: mean_tokens_metric_result,
    METRIC_MEAN_COST_USD: mean_cost_usd_metric_result,
    METRIC_MEAN_WALL_CLOCK: mean_wall_clock_metric_result,
    METRIC_CONFORMANCE: conformance_metric_result,
    METRIC_PLAN_COVERAGE: plan_coverage_metric_result,
    METRIC_DAG_VALIDITY: dag_validity_metric_result,
    METRIC_GATE_CATCH_RATE: gate_catch_rate_metric_result,
    METRIC_GATE_ESCAPE_RATE: gate_escape_rate_metric_result,
}

#: Prefix for the four cost-matched-delta MetricResult names. The full
#: metricName is ``cost_matched_delta__<label>`` where ``<label>`` is the
#: ASCII-safe form of the comparison label (e.g. ``a1_minus_a0``).
COST_MATCHED_DELTA_METRIC_PREFIX: str = "cost_matched_delta__"

#: Encoded as 0.0 for "not significant at α", 1.0 for "significant at α".
#: Mirrors :func:`dag_validity_metric_result`'s 1.0/0.0 encoding of a bool in a
#: float-only schema slot.
_SIGNIFICANT_FLAG_TRUE: float = 1.0
_SIGNIFICANT_FLAG_FALSE: float = 0.0


def _cost_matched_delta_metric_name(label: str) -> str:
    """ASCII-safe metricName for a cost-matched delta row.

    Lowercases and replaces the U+2212 MINUS SIGN in ``A1−A0``-style labels
    with ``_minus_`` so the metricName fits a typical ASCII-only metric
    namespace (the schema only requires minLength=1; this is the convention
    matched by the task spec's example ``cost_matched_delta__a1_minus_a0``).
    """
    return COST_MATCHED_DELTA_METRIC_PREFIX + label.lower().replace("−", "_minus_")


def cost_matched_delta_metric_result(
    *,
    campaign: str,
    suite: str,
    row: CostMatchedDeltaRow,
    n_trials: int,
) -> MetricResult:
    """Emit one ``cost_matched_delta__<label>`` MetricResult.

    Chosen shape (documented because ``ablation_metric_results`` does not
    currently emit delta-row MetricResults — the four cost-matched deltas are
    the first delta rows on the metric stream):

    * ``arm`` = the TREATMENT arm (e.g. ``A1`` for ``A1−A0``). A pairwise
      delta spans two arms; the treatment is the one whose effect the row
      attributes. This matches the column-ordering convention the rendered
      table uses (treatment listed first in every label).
    * ``metricName`` = ``cost_matched_delta__<label>`` per the task spec —
      one of ``cost_matched_delta__a1_minus_a0``,
      ``cost_matched_delta__a1_minus_a2``,
      ``cost_matched_delta__a2_minus_a3``,
      ``cost_matched_delta__a1_minus_a4``.
    * ``value`` = the cost-matched Δ%Resolved (treatment − baseline) as a
      proportion in ``[-1.0, 1.0]`` — matches the units the rendered bullet
      uses (rendered as percentage points; the metric stream stays in
      proportion-space).
    * ``ciLow``, ``ciHigh`` encode BOTH the no-closed-form-CI fact and the
      Holm-Bonferroni-adjusted significance flag, respecting the MetricResult
      schema invariant ``ciLow <= value <= ciHigh``:

      - When the Holm-Bonferroni-adjusted p ≤ α (**significant**):
        ``ciLow == ciHigh == value`` — degenerate point interval, the
        "Holm-adjusted decision rejected H0: delta = 0" reading (same shape as
        the speedup emitter's point-in-both-bounds convention).
      - When the adjusted p > α (**not significant**):
        ``ciLow = min(value, 0.0)``; ``ciHigh = max(value, 0.0)`` — an
        interval that contains zero, the "Holm-adjusted decision failed to
        reject H0: delta = 0 is consistent with the data" reading.

      A consumer recovers the flag with
      ``ci_low == ci_high == value`` ⇔ significant. The two encodings are
      mutually exclusive (a non-zero delta with ``ci_low == ci_high`` cannot
      also straddle zero); both keep the schema invariant.

    * ``nTrials`` = the number of paired instances ``mcn.n_pairs`` — the
      number of trials that fed the McNemar test (each arm contributes one
      bool per instance). Matches the "n" the rendered bullet shows.
    """
    delta = row.mcnemar.delta
    if row.significant_at_alpha:
        ci_low = delta
        ci_high = delta
    else:
        ci_low = min(delta, 0.0)
        ci_high = max(delta, 0.0)
    return _metric_result(
        campaign=campaign,
        arm=row.treatment,
        suite=suite,
        metric_name=_cost_matched_delta_metric_name(row.label),
        value=delta,
        ci_low=ci_low,
        ci_high=ci_high,
        n_trials=n_trials,
    )


def ablation_metric_results(
    run: CampaignRun,
    *,
    suite: str,
    arms: Sequence[str] | None = None,
    cost_basis: CostBasis = DEFAULT_COST_BASIS,
    budget: float | None = None,
    spec_artifacts: Mapping[str, Sequence[str]] | None = None,
    plan_artifacts: Mapping[str, Sequence[str]] | None = None,
    plan_graph_widths: Mapping[str, int] | None = None,
    gate_catch_counts: Mapping[str, tuple[int, int]] | None = None,
    gate_escape_counts: Mapping[str, tuple[int, int]] | None = None,
    merge_conflict_counts: Mapping[str, int] | None = None,
) -> list[MetricResult]:
    """Emit ONE MetricResult per applicable (arm, suite, metric) in the table.

    The canonical surface for the universal claim that every column in
    :data:`METRIC_COLUMNS` is a serialisable :class:`MetricResult`. Composes
    two paths:

    * :func:`cost_robustness_metric_results` — the six metrics in
      :data:`COST_ROBUSTNESS_METRIC_NAMES` (cost-matched %Resolved, parallel
      speedup, merge-conflict rate, manual-pause rate, gate-retry depth,
      regression rate). The stable lower-level entry point; preserved as-is.
    * The ten emitters in :data:`OUTCOME_AND_ARTIFACT_METRIC_NAMES`, each
      reading its value/CI off the same :class:`ArmRow` the renderer
      consumes — so the metric stream and the rendered table agree column-
      for-column.

    Applicability (:data:`APPLICABILITY`) is respected on both paths: gate
    metrics on A0/A3/A4 and plan-coverage/DAG-validity on A0/A4 are absent
    from the stream rather than emitted as zero.

    Negative-space: an arm with zero scored trials yields NO rows for any
    metric. The renderer's "no trials" path is the right home for those
    cells (they appear as empty rows in the table), not the metric stream.

    Parameters
    ----------
    run:
        The CampaignRun whose scored results to read.
    suite:
        The suite slug the metrics are reported for; the caller passes the
        (arm × suite) slice it owns.
    arms:
        Arms to emit metrics for; defaults to :data:`ABLATION_ARMS` (the
        closed five-arm set the ablation table reports on).
    cost_basis:
        Cost basis for the cost-matched %Resolved (DOLLARS by default).
    budget:
        Equal-budget cap on ``cost_basis``; derived via
        :func:`equal_budget_for_arms` over the requested arms when ``None``.
    spec_artifacts, plan_artifacts, plan_graph_widths, gate_catch_counts,
    gate_escape_counts, merge_conflict_counts:
        Optional per-arm inputs threaded to :func:`build_arm_row` —
        see its docstring for the shape of each. Without the gate counts the
        gate catch/escape cells stay absent (the same rule
        :func:`build_arm_row` uses).

    Returns
    -------
    list[MetricResult]
        The concatenated metric stream: the six cost+robustness rows per
        scored arm, then the ten outcome+artifact rows per scored arm,
        with non-applicable (arm, metric) pairs absent. Every row is
        schema-valid (the :class:`MetricResult` constructor validates).
    """
    selected_arms: tuple[str, ...] = tuple(arms) if arms is not None else ABLATION_ARMS

    # Same derivation rule cost_robustness_metric_results uses, computed here
    # so the per-arm ArmRow builds and the cost-robustness emitter share a
    # single budget value. _budget_for_run handles empty/no-bundle arms.
    if budget is None:
        budget = _budget_for_run(run, selected_arms, cost_basis)

    # Build one ArmRow per scored arm — the source of truth the ten ArmRow-
    # derived emitters read off. Arms with zero scored trials are SKIPPED so
    # the metric stream is empty for them (the documented negative-space).
    arm_rows: dict[str, ArmRow] = {}
    for arm_slug in selected_arms:
        if not _arm_scored_results(run, arm_slug):
            continue
        arm_rows[arm_slug] = build_arm_row(
            run,
            arm_slug,
            cost_basis=cost_basis,
            budget=budget,
            spec_artifacts=spec_artifacts,
            plan_artifacts=plan_artifacts,
            plan_graph_widths=plan_graph_widths,
            gate_catch_counts=gate_catch_counts,
            gate_escape_counts=gate_escape_counts,
            merge_conflict_counts=merge_conflict_counts,
        )

    out: list[MetricResult] = []

    # Path 1: cost+robustness — the existing six emitters, restricted to the
    # arms that have scored trials (cost_robustness_metric_results applies the
    # same restriction by default; passing the arms list explicitly keeps the
    # two paths' arm sets aligned).
    if arm_rows:
        out.extend(
            cost_robustness_metric_results(
                run,
                suite=suite,
                arms=tuple(arm_rows),
                basis=cost_basis,
                budget=budget,
                merge_conflict_counts=merge_conflict_counts,
                plan_graph_widths=plan_graph_widths,
            )
        )

    # Path 2: the ten ArmRow-derived emitters, in
    # OUTCOME_AND_ARTIFACT_METRIC_NAMES order per arm.
    campaign_id = run.campaign.id
    for arm_slug, row in arm_rows.items():
        for metric_name in OUTCOME_AND_ARTIFACT_METRIC_NAMES:
            emitter = _OUTCOME_AND_ARTIFACT_EMITTERS[metric_name]
            emitted = emitter(campaign=campaign_id, arm=arm_slug, suite=suite, row=row)
            if emitted is not None:
                out.append(emitted)

    # Path 3: the four cost-matched pairwise-delta rows. Distinct from the
    # column emitters above — these are pairwise deltas, not single-arm metric
    # cells. The metricName is ``cost_matched_delta__<label>`` (one per
    # PAIRWISE_DELTAS); the ``arm`` slot carries the TREATMENT arm (delta
    # rows span two arms; the treatment is the one whose effect the row
    # attributes). The Holm-Bonferroni adjustment is applied within the
    # cost-matched family of four — separate from the raw-delta family.
    #
    # Negative-space rule for the metric stream: emit the delta record only
    # when BOTH arms in the comparison have at least one scored trial — same
    # arms-with-scored-trials rule the column-metric paths use. A comparison
    # whose treatment OR baseline went un-sampled would carry a meaningless
    # treatment-arm slug into the stream (the un-sampled arm contributes no
    # bool map); the in-memory :class:`CostMatchedDeltaRow` still carries it
    # (n_pairs == 0) so the rendered report preserves the structural row.
    cost_matched_rows = _build_cost_matched_delta_rows(run, cost_basis=cost_basis)
    scored_arms = {arm_slug for arm_slug in arm_rows}
    for cmd_row in cost_matched_rows:
        if cmd_row.treatment not in scored_arms or cmd_row.baseline not in scored_arms:
            continue
        out.append(
            cost_matched_delta_metric_result(
                campaign=campaign_id,
                suite=suite,
                row=cmd_row,
                n_trials=cmd_row.mcnemar.n_pairs,
            )
        )

    return out


def _build_cost_matched_delta_rows(
    run: CampaignRun,
    *,
    cost_basis: CostBasis,
    alpha: float = HOLM_BONFERRONI_ALPHA,
) -> tuple[CostMatchedDeltaRow, ...]:
    """Build the four :class:`CostMatchedDeltaRow`s for a CampaignRun.

    Shared single-source helper for :func:`build_ablation_report` and
    :func:`ablation_metric_results`. Computes a per-pair equal budget B over
    just the two arms in each comparison (spec: "equalising the budget across
    the two arms"), caches the per-(arm, budget) cost-matched bool maps, runs
    the existing :func:`mcnemar_delta` to get a McNemar result per comparison,
    then applies Holm-Bonferroni within the cost-matched family of four —
    SEPARATE from the raw-delta family (see
    :func:`apply_holm_bonferroni_per_family`).
    """
    arm_cost_cache: dict[str, list[float]] = {}
    bool_map_cache: dict[tuple[str, float], dict[str, bool]] = {}
    cost_matched_mcnemars: list[tuple[str, str, str, str, McNemarResult, float]] = []
    for treatment, baseline, label, isolates in PAIRWISE_DELTAS:
        for arm in (treatment, baseline):
            if arm not in arm_cost_cache:
                arm_cost_cache[arm] = _arm_costs_for_pair(run, arm, cost_basis)
        treat_costs = arm_cost_cache[treatment]
        base_costs = arm_cost_cache[baseline]
        if treat_costs and base_costs:
            pair_budget = equal_budget_for_arms(
                {treatment: treat_costs, baseline: base_costs}
            )
        else:
            pair_budget = 0.0
        for arm in (baseline, treatment):
            key = (arm, pair_budget)
            if key not in bool_map_cache:
                bool_map_cache[key] = _arm_instance_cost_matched_resolved(
                    run, arm, budget=pair_budget, basis=cost_basis
                )
        base_bools = bool_map_cache[(baseline, pair_budget)]
        treat_bools = bool_map_cache[(treatment, pair_budget)]
        mcn = mcnemar_delta(base_bools, treat_bools)
        cost_matched_mcnemars.append(
            (label, treatment, baseline, isolates, mcn, pair_budget)
        )

    cm_p = [row[4].p_value for row in cost_matched_mcnemars]
    cm_adj = holm_bonferroni_adjusted_pvalues(cm_p)
    return tuple(
        CostMatchedDeltaRow(
            label=label,
            treatment=treatment,
            baseline=baseline,
            isolates=isolates,
            mcnemar=mcn,
            adjusted_p=adj_p,
            significant_at_alpha=adj_p <= alpha,
            budget=pair_budget,
            basis=cost_basis,
            alpha=alpha,
        )
        for (label, treatment, baseline, isolates, mcn, pair_budget), adj_p in zip(
            cost_matched_mcnemars, cm_adj, strict=True
        )
    )


# --- rendering --------------------------------------------------------------


def _fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _fmt_ci(ci: ConfidenceInterval | None) -> str:
    if ci is None:
        return NA_RENDER_TOKEN
    return f"{_fmt_pct(ci.point)} [{_fmt_pct(ci.low)}, {_fmt_pct(ci.high)}]"


def _fmt_optional_number(value: float | None, fmt: str = "{:.2f}") -> str:
    if value is None:
        return NA_RENDER_TOKEN
    return fmt.format(value)


def _fmt_cost_matched(cmr: CostMatchedResolved | None) -> str:
    if cmr is None:
        return NA_RENDER_TOKEN
    return _fmt_ci(cmr.interval)


def _fmt_speedup(sp: ParallelSpeedup | None) -> str:
    if sp is None:
        return NA_RENDER_TOKEN
    suffix = "" if sp.graph_width is None else f" (width={sp.graph_width})"
    return f"{sp.speedup:.2f}x{suffix}"


def _fmt_plan_coverage(pc: PlanCoverage | None) -> str:
    if pc is None:
        return NA_RENDER_TOKEN
    return f"{_fmt_pct(pc.fraction)} ({len(pc.covered)}/{len(pc.in_scope)})"


def _fmt_dag(dv: DagValidity | None) -> str:
    if dv is None:
        return NA_RENDER_TOKEN
    return "valid" if dv.valid else "invalid"


def _fmt_retry(gr: GateRetryDepth | None) -> str:
    if gr is None:
        return NA_RENDER_TOKEN
    return f"{gr.mean:.2f} [{gr.low:.2f}, {gr.high:.2f}]"


_METRIC_RENDER_HEADERS: dict[str, str] = {
    METRIC_PASS_AT_1: "Pass@1 (95% CI)",
    METRIC_PASS_AT_K: "Pass@k",
    METRIC_REGRESSION_RATE: "Regression rate (95% CI)",
    METRIC_COST_MATCHED_RESOLVED: "Cost-matched %Resolved (95% CI)",
    METRIC_MEAN_TOKENS: "Mean tokens/trial",
    METRIC_MEAN_COST_USD: "Mean $/trial",
    METRIC_MEAN_WALL_CLOCK: "Mean wall-clock/trial (s)",
    METRIC_PARALLEL_SPEEDUP: "Parallel speedup",
    METRIC_CONFORMANCE: "Conformance (mean, 95% CI)",
    METRIC_PLAN_COVERAGE: "Plan coverage",
    METRIC_DAG_VALIDITY: "DAG validity",
    METRIC_GATE_CATCH_RATE: "Gate catch rate (95% CI)",
    METRIC_GATE_ESCAPE_RATE: "False-Done escape rate (95% CI)",
    METRIC_MERGE_CONFLICT_RATE: "Merge-conflict rate (95% CI)",
    METRIC_MANUAL_PAUSE_RATE: "Manual-pause rate (95% CI)",
    METRIC_GATE_RETRY_DEPTH: "Gate-retry depth (mean, 95% CI)",
}


def _cell_value(row: ArmRow, metric: str) -> str:
    """Render one cell as a string — ``N/A`` when the metric does not apply.

    Routes by metric to the appropriate formatter; raises on an unknown metric
    so the renderer never silently emits a blank cell.
    """
    if not metric_applies(metric, row.arm):
        return NA_RENDER_TOKEN
    if metric == METRIC_PASS_AT_1:
        return _fmt_ci(row.pass_at_1)
    if metric == METRIC_PASS_AT_K:
        return NA_RENDER_TOKEN if row.pass_at_k is None else _fmt_pct(row.pass_at_k)
    if metric == METRIC_REGRESSION_RATE:
        return _fmt_ci(row.regression_rate)
    if metric == METRIC_COST_MATCHED_RESOLVED:
        return _fmt_cost_matched(row.cost_matched_resolved)
    if metric == METRIC_MEAN_TOKENS:
        return _fmt_optional_number(row.mean_input_output_tokens, "{:.0f}")
    if metric == METRIC_MEAN_COST_USD:
        return _fmt_optional_number(row.mean_cost_usd, "${:.4f}")
    if metric == METRIC_MEAN_WALL_CLOCK:
        return _fmt_optional_number(row.mean_wall_clock_seconds, "{:.2f}")
    if metric == METRIC_PARALLEL_SPEEDUP:
        return _fmt_speedup(row.parallel_speedup)
    if metric == METRIC_CONFORMANCE:
        return _fmt_ci(row.conformance)
    if metric == METRIC_PLAN_COVERAGE:
        return _fmt_plan_coverage(row.plan_coverage)
    if metric == METRIC_DAG_VALIDITY:
        return _fmt_dag(row.dag_validity)
    if metric == METRIC_GATE_CATCH_RATE:
        return _fmt_ci(row.gate_catch_rate)
    if metric == METRIC_GATE_ESCAPE_RATE:
        return _fmt_ci(row.gate_escape_rate)
    if metric == METRIC_MERGE_CONFLICT_RATE:
        return _fmt_ci(row.merge_conflict_rate)
    if metric == METRIC_MANUAL_PAUSE_RATE:
        return _fmt_ci(row.manual_pause_rate)
    if metric == METRIC_GATE_RETRY_DEPTH:
        return _fmt_retry(row.gate_retry_depth)
    raise KeyError(f"unknown metric column: {metric!r}")  # pragma: no cover


def _delta_line(row: DeltaRow) -> str:
    """Render one pairwise-delta row as a Markdown line."""
    mcn = row.mcnemar
    kind = "exact binomial" if mcn.exact else "chi-square_1"
    flag = "**significant**" if row.significant_at_alpha else "not significant"
    return (
        f"- **Delta {row.label}** ({row.isolates}; paired, n={mcn.n_pairs}): "
        f"Δ%Resolved = {mcn.delta * 100:+.1f} pp; "
        f"McNemar χ² = {mcn.statistic:.3f} (cc), "
        f"p = {mcn.p_value:.4f} ({kind}); "
        f"discordant b={mcn.b}, c={mcn.c}; "
        f"Holm-Bonferroni adjusted p = {row.adjusted_p:.4f} "
        f"({flag} at α = {row.alpha})."
    )


def _cost_matched_delta_line(row: CostMatchedDeltaRow) -> str:
    """Render one cost-matched pairwise-delta row as a Markdown line.

    Same shape as :func:`_delta_line` plus the per-comparison equal-budget cap
    ``B`` (so a reader sees the budget the bool map was capped at without
    cross-referencing the section preamble).
    """
    mcn = row.mcnemar
    kind = "exact binomial" if mcn.exact else "chi-square_1"
    flag = "**significant**" if row.significant_at_alpha else "not significant"
    return (
        f"- **Cost-matched delta {row.label}** "
        f"({row.isolates}; paired, n={mcn.n_pairs}; "
        f"B={row.budget:.4f} {row.basis.value}): "
        f"Δ%Resolved = {mcn.delta * 100:+.1f} pp; "
        f"McNemar χ² = {mcn.statistic:.3f} (cc), "
        f"p = {mcn.p_value:.4f} ({kind}); "
        f"discordant b={mcn.b}, c={mcn.c}; "
        f"Holm-Bonferroni adjusted p = {row.adjusted_p:.4f} "
        f"({flag} at α = {row.alpha})."
    )


def render_ablation_report(report: AblationReport) -> str:
    """Render an :class:`AblationReport` as a deterministic Markdown table.

    Header notes the cost-matching basis (the resolved Open question) and the
    multiple-comparison correction in use; then a five-arm table with one row
    per arm in :data:`ABLATION_ARMS` order and one column per metric in
    :data:`METRIC_COLUMNS` order; then the four pairwise-delta lines, each
    carrying its arm pair, McNemar result, and Holm-Bonferroni-adjusted p-value.

    Pure formatting — given the same :class:`AblationReport` the output is
    deterministic, so tests can assert on its content.
    """
    headers = ["Arm", "n trials"] + [
        _METRIC_RENDER_HEADERS[m] for m in report.metric_columns
    ]
    header_line = "| " + " | ".join(headers) + " |"
    rule_line = "| " + " | ".join("---" for _ in headers) + " |"

    body_lines: list[str] = []
    for row in report.arms:
        cells = [row.arm, str(row.n_trials)]
        for metric in report.metric_columns:
            cells.append(_cell_value(row, metric))
        body_lines.append("| " + " | ".join(cells) + " |")

    preamble = [
        "## Ablation table",
        "",
        f"_{_COST_BASIS_HEADER_PREFIX}: {report.cost_basis.value}; "
        f"equal-budget cap = {report.budget:.4f}._",
        "",
        f"_Multiple-comparison correction: Holm-Bonferroni at α = {report.alpha} "
        "across the four planned pairwise deltas (omitting correction is not "
        "honest with four comparisons)._",
        "",
        f"_Not-applicable cells render as ``{NA_RENDER_TOKEN}`` — distinct from a "
        "zero value._",
        "",
    ]

    delta_section = [
        "",
        "### Pairwise deltas",
        "",
    ]
    for d in report.deltas:
        delta_section.append(_delta_line(d))

    cost_matched_section: list[str] = []
    if report.cost_matched_deltas:
        cost_matched_section = [
            "",
            "### Cost-matched pairwise deltas",
            "",
            f"_Cost basis: {report.cost_basis.value}. Each comparison's "
            "equal-budget cap ``B`` is derived from the two arms in that "
            "comparison only (per-comparison budgets are stated on each "
            "bullet)._",
            "",
            "_Multiple-comparison correction: Holm-Bonferroni at α = "
            f"{report.alpha} across the four cost-matched deltas, applied "
            "as a SEPARATE family from the raw pairwise deltas (preserves "
            "the spec's α = 0.05 per-comparison family-wise rate per reading)._",
            "",
        ]
        for cmd in report.cost_matched_deltas:
            cost_matched_section.append(_cost_matched_delta_line(cmd))

    return "\n".join(
        preamble
        + [header_line, rule_line, *body_lines, *delta_section, *cost_matched_section]
    )


__all__ = [
    "ABLATION_ARMS",
    "APPLICABILITY",
    "COST_MATCHED_DELTA_METRIC_PREFIX",
    "GATED_ARMS",
    "HOLM_BONFERRONI_ALPHA",
    "METRIC_COLUMNS",
    "METRIC_CONFORMANCE",
    "METRIC_COST_MATCHED_RESOLVED",
    "METRIC_DAG_VALIDITY",
    "METRIC_GATE_CATCH_RATE",
    "METRIC_GATE_ESCAPE_RATE",
    "METRIC_GATE_RETRY_DEPTH",
    "METRIC_MANUAL_PAUSE_RATE",
    "METRIC_MEAN_COST_USD",
    "METRIC_MEAN_TOKENS",
    "METRIC_MEAN_WALL_CLOCK",
    "METRIC_MERGE_CONFLICT_RATE",
    "METRIC_PARALLEL_SPEEDUP",
    "METRIC_PASS_AT_1",
    "METRIC_PASS_AT_K",
    "METRIC_PLAN_COVERAGE",
    "METRIC_REGRESSION_RATE",
    "NA_RENDER_TOKEN",
    "OUTCOME_AND_ARTIFACT_METRIC_NAMES",
    "PAIRWISE_DELTAS",
    "PLAN_PRODUCING_ARMS",
    "AblationReport",
    "ArmRow",
    "CostMatchedDeltaRow",
    "DeltaRow",
    "ablation_metric_results",
    "apply_holm_bonferroni",
    "apply_holm_bonferroni_per_family",
    "build_ablation_report",
    "build_arm_row",
    "conformance_metric_result",
    "cost_matched_delta_metric_result",
    "dag_validity_metric_result",
    "gate_catch_rate_metric_result",
    "gate_escape_rate_metric_result",
    "holm_bonferroni_adjusted_pvalues",
    "mean_cost_usd_metric_result",
    "mean_tokens_metric_result",
    "mean_wall_clock_metric_result",
    "metric_applies",
    "pass_at_1_metric_result",
    "pass_at_k_metric_result",
    "plan_coverage_metric_result",
    "render_ablation_report",
]
