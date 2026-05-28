"""Cost-matched %Resolved, parallel speedup, and the robustness columns.

Implements ``docs/benchmark/specs/04-metrics.md`` §Bucket 2 (cost-matched
%Resolved, parallel speedup) and §Bucket 4 — Robustness (merge-conflict rate,
manual-pause rate, gate-retry depth, regression rate).

Every quantity is emitted as a :class:`benchmark.harness.domain.MetricResult`
per (arm, suite), with a 95% Wilson interval where the quantity is a binomial
proportion. For non-proportion quantities (mean gate-retry depth, the
speedup ratio) we still emit ``ciLow``/``ciHigh`` from a closed-form interval
where one applies (normal-approximation t-interval on the mean), or repeat the
point value when no defensible interval is available — the field is required by
the schema. Each metric documents which it does.

Cost-matching basis (PINNED)
---------------------------
The Open question in ``04-metrics.md`` (§Assumptions and open questions —
"Cost-matching method") asks whether the fair budget is equalised on tokens,
dollars, or wall-clock. The decision pinned for this task:

* **Headline basis: dollars (``costUsd``).** Most directly comparable across
  arms ("the same spend"); the spec's prose says "token (or dollar) budget" and
  Bucket 2's "cost per trial" is already in dollars.
* **Tokens (``inputTokens + outputTokens``)** is selectable for ablation
  reports that want to factor out per-model pricing.
* **Wall-clock (``wallClockSeconds``)** is selectable for "the same hours"
  comparisons; it is NOT the headline because wall-clock is dominated by
  scheduling parallelism rather than the workflow's intrinsic spend.

The basis is a named enum (:class:`CostBasis`) carried through every cost-
matched call, so the choice is explicit at the call site, not implicit.

Cost-matching rule (PINNED — equal-budget)
-----------------------------------------
For a (arm-A, arm-B) comparison the budget ``B`` is the cheaper arm's MAXIMUM
per-trial cost: ``B = min(max(cost(arm A)), max(cost(arm B)))``. With ``B`` so
chosen, the cheaper arm pays no penalty (its every trial is within budget by
construction), and the more expensive arm's trials that overshot ``B`` count
as un-resolved at the equal budget — the standard "compare each arm at the
budget of the cheaper arm" rule. For a SINGLE arm we report the ARM-LOCAL
cost-matched rate at the campaign-supplied budget; with no budget given the
arm's own max is used (which trivially equals raw %Resolved — useful as a
sanity row).

The cost-matched %Resolved for an arm at budget ``B`` is:

    cost_matched_pass_at_1(arm, B) =
        |{ trial : trial.cost <= B AND trial.resolved }| / n_scored

The denominator is the arm's total scored trials, NOT the count within budget
— answering "of the trials I ran, how many resolved within budget ``B``", which
is comparable across arms even when one arm has fewer affordable trials.

Parallel-speedup definition (DOCUMENTED HONESTLY)
-------------------------------------------------
The spec wants "A1's wall-clock vs the same plan run sequentially". Our captured
runs do NOT carry intra-trial per-task timing, only ONE ``wallClockSeconds`` per
trial. The honest estimate we CAN compute from ``CampaignRun`` is the
INTRA-CAMPAIGN speedup: how much the scheduler's pool saved over running this
arm's trials one after another.

    sequential_estimate(arm) = sum of wallClockSeconds across arm's trials
    observed_parallel_wall(arm) = max wallClockSeconds across arm's trials
    speedup(arm) = sequential_estimate / observed_parallel_wall

With one trial the ratio is 1.0 (no parallelism observable). The result also
carries the task-graph WIDTH (from :func:`dag_validity` over the arm's
plan artifacts when present) so a reviewer can read the "wide graphs help"
correlation directly. We document that this is an inter-trial estimate, not
intra-trial; the bigger comparison the spec ideally wants (A1's observed
wall-clock vs the SAME plan re-run task-by-task without parallel agents) is
NOT computable from a single captured bundle and so is not invented here.

Real-data zeros (SAMPLE LIMITATION)
-----------------------------------
On our captured live data:

* Gate retry depth is 0 (every ``GateEvent.retryIndex`` was 0 — Task 10 records
  this: the merged certificate reflects only the FINAL gate discharge, the
  retries before it are not currently preserved as separate events).
* Manual-pause rate is 0 (no ``UNVERIFIED`` verdicts emitted on the real
  pipelines).
* Merge-conflict rate is 0 except A4 (which DID record 3 conflicts but in a
  side channel the driver does not currently thread to ``TrialResult``).

These zeros are a SAMPLE LIMITATION, not a bug in the metric. The synthetic
tests (``test_cost_robustness.py``) exercise the non-zero paths with KNOWN
answers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from benchmark.harness.domain import (
    METRIC_RESULT_ID_PREFIX,
    MetricResult,
    new_record_id,
)
from benchmark.harness.stats.outcome import (
    CONFIDENCE_LEVEL,
    WILSON_Z_95,
    ConfidenceInterval,
    wilson_interval,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from benchmark.harness.domain import GateEvent
    from benchmark.harness.driver import CampaignRun, TrialResult

# --- named limits / constants ----------------------------------------------

#: The two-sided z critical value for the 95% interval (same as in outcome.py).
#: Reused here so both files name the same constant.
_Z_95 = WILSON_Z_95

#: Metric-name strings (the ``metricName`` field of every emitted MetricResult).
#: Stable, lower-snake, machine-readable; the renderer turns them into headings.
METRIC_COST_MATCHED_RESOLVED = "cost_matched_resolved"
METRIC_PARALLEL_SPEEDUP = "parallel_speedup"
METRIC_MERGE_CONFLICT_RATE = "merge_conflict_rate"
METRIC_MANUAL_PAUSE_RATE = "manual_pause_rate"
METRIC_GATE_RETRY_DEPTH = "gate_retry_depth"
METRIC_REGRESSION_RATE = "regression_rate"

#: The full set of metric names this module emits (for tests + the renderer).
COST_ROBUSTNESS_METRIC_NAMES: tuple[str, ...] = (
    METRIC_COST_MATCHED_RESOLVED,
    METRIC_PARALLEL_SPEEDUP,
    METRIC_MERGE_CONFLICT_RATE,
    METRIC_MANUAL_PAUSE_RATE,
    METRIC_GATE_RETRY_DEPTH,
    METRIC_REGRESSION_RATE,
)

#: The Gate verdict that signals a manual pause (human sign-off required), per
#: ``04-metrics.md`` §Bucket 4 — Robustness.
GATE_VERDICT_UNVERIFIED = "UNVERIFIED"

#: Speedup is undefined when an arm has no observed parallel wall-clock (every
#: trial wall-clock is 0). We report 1.0 — "no parallel benefit observable" —
#: rather than NaN so the field is always JSON-finite for the MetricResult
#: schema. Documented at the call site.
_DEFAULT_SPEEDUP_NO_OBSERVATION = 1.0

#: A single-trial arm has no parallelism to measure: by definition the
#: observed-parallel wall equals the sequential estimate (the sum of one
#: number). We report 1.0 in that case.
_SINGLE_TRIAL_SPEEDUP = 1.0


class CostBasis(StrEnum):
    """The basis on which arms are cost-matched (the resolved Open question).

    DOLLARS is the pinned headline; TOKENS and WALL_CLOCK are selectable for
    ablation comparisons. The basis is part of every cost-matched call so the
    choice is explicit at the call site, not implicit in the data.
    """

    DOLLARS = "dollars"
    TOKENS = "tokens"
    WALL_CLOCK = "wall_clock"


#: The pinned headline basis. Functions default to this; callers can override.
DEFAULT_COST_BASIS = CostBasis.DOLLARS


# --- per-trial cost extraction ----------------------------------------------


def _trial_cost(result: TrialResult, basis: CostBasis) -> float:
    """The per-trial cost of a scored TrialResult on the chosen basis.

    A scored TrialResult carries an ArtifactBundle whose Telemetry has all
    three of (costUsd, inputTokens + outputTokens, wallClockSeconds). For a
    result without a bundle (only possible if the caller filters incorrectly)
    we raise — the function is called on ``CampaignRun.scored_results`` which
    is guaranteed to have one.
    """
    if result.bundle is None:
        raise ValueError(
            f"trial {result.trial.id!r} has no ArtifactBundle; cannot read cost"
        )
    telemetry = result.bundle.telemetry
    if basis is CostBasis.DOLLARS:
        return float(telemetry.costUsd)
    if basis is CostBasis.TOKENS:
        return float(telemetry.inputTokens + telemetry.outputTokens)
    if basis is CostBasis.WALL_CLOCK:
        return float(telemetry.wallClockSeconds)
    raise ValueError(f"unknown CostBasis: {basis!r}")  # pragma: no cover


# --- cost-matched %Resolved -------------------------------------------------


@dataclass(frozen=True)
class CostMatchedResolved:
    """The cost-matched %Resolved of one arm at a fixed budget.

    ``arm`` is the arm slug; ``basis`` the cost basis used; ``budget`` the
    equal-budget cap applied; ``n_trials`` the total scored trials of the arm;
    ``within_budget`` the count of trials whose per-trial cost ≤ budget;
    ``resolved_within_budget`` the count of those that also resolved.
    ``interval`` is a Wilson 95% interval on
    ``resolved_within_budget / n_trials``.
    """

    arm: str
    basis: CostBasis
    budget: float
    n_trials: int
    within_budget: int
    resolved_within_budget: int
    interval: ConfidenceInterval


def equal_budget_for_arms(
    arm_costs: Mapping[str, Sequence[float]],
) -> float:
    """Equal-budget rule: ``min`` over arms of ``max(per-trial cost)``.

    ``arm_costs`` maps an arm slug to the per-trial costs of its scored trials
    (on a single basis). The budget is the cheaper arm's max — the cap at which
    that arm trivially stays at parity with its raw %Resolved, and the more
    expensive arm pays for any trial that overshot. With one arm we return that
    arm's max (a degenerate cap). With zero arms or any empty arm we raise —
    there is no equal-budget at all in that case.
    """
    if not arm_costs:
        raise ValueError("need at least one arm to compute equal budget")
    arm_maxes: list[float] = []
    for arm, costs in arm_costs.items():
        if not costs:
            raise ValueError(f"arm {arm!r} has no scored trials; budget undefined")
        arm_maxes.append(max(costs))
    return min(arm_maxes)


def cost_matched_resolved_for_arm(
    arm: str,
    arm_results: Sequence[TrialResult],
    budget: float,
    basis: CostBasis = DEFAULT_COST_BASIS,
) -> CostMatchedResolved:
    """Cost-matched %Resolved for one arm at a fixed ``budget`` on ``basis``.

    ``arm_results`` are the SCORED trials of the arm (the ones with a
    ScoreReport — failed/infra trials are excluded by the caller). The metric:

        |{ trial : cost(trial) <= budget AND trial.resolved }| / n_scored

    with a Wilson 95% interval. Documented denominator: total scored trials,
    not within-budget trials — "of the trials I ran, how many resolved within
    budget", comparable across arms (see module docstring).
    """
    n_trials = len(arm_results)
    within = 0
    resolved_within = 0
    for result in arm_results:
        if result.report is None:
            continue  # caller filter slipped; defensive
        cost = _trial_cost(result, basis)
        if cost <= budget:
            within += 1
            if result.report.resolved:
                resolved_within += 1
    interval = wilson_interval(resolved_within, n_trials)
    return CostMatchedResolved(
        arm=arm,
        basis=basis,
        budget=budget,
        n_trials=n_trials,
        within_budget=within,
        resolved_within_budget=resolved_within,
        interval=interval,
    )


# --- parallel speedup --------------------------------------------------------


@dataclass(frozen=True)
class ParallelSpeedup:
    """Intra-campaign parallel-speedup estimate for one arm.

    ``sequential_estimate`` is the sum of per-trial wall-clock across the arm's
    scored trials; ``observed_parallel_wall`` is the max per-trial wall-clock
    (the bound a perfect scheduler would reach if every trial ran in parallel);
    ``speedup`` is the ratio. ``graph_width`` is the task-graph width of the
    arm's plan when one was captured (None otherwise) — supplied so a reviewer
    can read the "wide graphs help" correlation directly.
    """

    arm: str
    n_trials: int
    sequential_estimate_seconds: float
    observed_parallel_wall_seconds: float
    speedup: float
    graph_width: int | None


def parallel_speedup_for_arm(
    arm: str,
    arm_results: Sequence[TrialResult],
    graph_width: int | None = None,
) -> ParallelSpeedup:
    """Intra-campaign parallel-speedup for one arm, with an optional graph width.

    See the module docstring for the "honest estimate" framing. With zero
    scored trials we report speedup 1.0 and a zero baseline (defensible "no
    parallelism observable"); with one trial the speedup is exactly 1.0 by
    construction (sum == max). With every trial wall-clock 0 we also report
    1.0 — the ratio is undefined and 1.0 means "no benefit observable".
    """
    walls: list[float] = []
    for result in arm_results:
        if result.bundle is None:
            continue
        walls.append(float(result.bundle.telemetry.wallClockSeconds))
    n = len(walls)
    if n == 0:
        return ParallelSpeedup(
            arm=arm,
            n_trials=0,
            sequential_estimate_seconds=0.0,
            observed_parallel_wall_seconds=0.0,
            speedup=_DEFAULT_SPEEDUP_NO_OBSERVATION,
            graph_width=graph_width,
        )
    sequential = math.fsum(walls)
    parallel = max(walls)
    if n == 1:
        speedup = _SINGLE_TRIAL_SPEEDUP
    elif parallel <= 0.0:
        speedup = _DEFAULT_SPEEDUP_NO_OBSERVATION
    else:
        speedup = sequential / parallel
    return ParallelSpeedup(
        arm=arm,
        n_trials=n,
        sequential_estimate_seconds=sequential,
        observed_parallel_wall_seconds=parallel,
        speedup=speedup,
        graph_width=graph_width,
    )


# --- robustness columns -----------------------------------------------------


def merge_conflict_rate(
    arm_results: Sequence[TrialResult],
    conflict_counts: Mapping[str, int] | None = None,
) -> ConfidenceInterval:
    """Merge-conflict rate: fraction of an arm's trials with ≥1 recorded conflict.

    ``conflict_counts`` maps a Trial id to the number of merge conflicts the run
    recorded for it (the A4 ``last_merge_conflicts`` channel keyed by trial id).
    A trial counts toward the numerator when its count is > 0. With no map (or
    the map empty for every trial), the rate is 0 on every trial — the honest
    answer when conflicts were not threaded through, NOT a hallucinated value.

    Returned as a Wilson interval over the arm's total trials (matches the
    other proportion metrics).
    """
    counts = conflict_counts or {}
    n_trials = len(arm_results)
    conflicted = sum(1 for r in arm_results if counts.get(r.trial.id, 0) > 0)
    return wilson_interval(conflicted, n_trials)


def manual_pause_rate(
    arm_results: Sequence[TrialResult],
) -> ConfidenceInterval:
    """Manual-pause rate: fraction of trials with ≥1 ``UNVERIFIED`` GateEvent.

    Reads ``TrialResult.gate_events`` (threaded by the driver after task 14).
    A trial counts when any of its gate events carries verdict ``UNVERIFIED``.
    A trial with NO gate events (gated arms only emit them; A0/A3/A4 don't)
    counts as un-paused — those arms simply do not gate. With zero trials the
    interval is the whole [0, 1].
    """
    n_trials = len(arm_results)
    paused = sum(
        1
        for r in arm_results
        if any(e.verdict == GATE_VERDICT_UNVERIFIED for e in r.gate_events)
    )
    return wilson_interval(paused, n_trials)


@dataclass(frozen=True)
class GateRetryDepth:
    """Gate-retry depth: mean ``retryIndex`` over the arm's GateEvents.

    ``mean`` is the mean retryIndex over all events; ``low``/``high`` is a
    normal-approximation 95% interval on the mean
    (``mean ± z · sd / sqrt(n)``), valid for n ≥ 2; for n < 2 we report the
    point value in both bounds (the interval is undefined). ``n_events`` is
    the total event count, ``n_trials`` the arm's total trials.
    """

    arm: str
    mean: float
    low: float
    high: float
    n_events: int
    n_trials: int


def gate_retry_depth_for_arm(
    arm: str, arm_results: Sequence[TrialResult]
) -> GateRetryDepth:
    """Mean ``retryIndex`` over an arm's GateEvents, with a 95% mean CI.

    Empty (no events) → mean 0.0 and a degenerate [0.0, 0.0] interval; the
    sample-limitation case our captured data hits (Task 10: retryIndex is
    always 0 in real evidence). The synthetic tests exercise the non-zero path.
    """
    events: list[GateEvent] = [e for r in arm_results for e in r.gate_events]
    n_events = len(events)
    n_trials = len(arm_results)
    if n_events == 0:
        return GateRetryDepth(
            arm=arm,
            mean=0.0,
            low=0.0,
            high=0.0,
            n_events=0,
            n_trials=n_trials,
        )
    indices = [float(e.retryIndex) for e in events]
    mean = math.fsum(indices) / n_events
    if n_events < 2:
        return GateRetryDepth(
            arm=arm,
            mean=mean,
            low=mean,
            high=mean,
            n_events=n_events,
            n_trials=n_trials,
        )
    # Sample variance (Bessel-corrected) and normal-approximation CI for the mean.
    variance = math.fsum((x - mean) ** 2 for x in indices) / (n_events - 1)
    sd = math.sqrt(variance)
    half = _Z_95 * sd / math.sqrt(n_events)
    return GateRetryDepth(
        arm=arm,
        mean=mean,
        low=mean - half,
        high=mean + half,
        n_events=n_events,
        n_trials=n_trials,
    )


def regression_rate_for_arm(
    arm_results: Sequence[TrialResult],
) -> ConfidenceInterval:
    """Regression rate: fraction of trials whose ScoreReport.regressed is true.

    Composes with the existing outcome.py definition (same numerator and
    denominator), exposed here so the cost+robustness emitter has it without
    importing the outcome module's per-arm wrapper. Failed trials (no
    ScoreReport) are excluded — the caller passes the scored TrialResults.
    """
    n_trials = len(arm_results)
    regressed = sum(
        1 for r in arm_results if r.report is not None and r.report.regressed
    )
    return wilson_interval(regressed, n_trials)


# --- MetricResult emitters --------------------------------------------------


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
    """Build one MetricResult with a fresh id, validated by the schema."""
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


def _arm_scored_results(run: CampaignRun, arm: str) -> list[TrialResult]:
    """The arm's scored TrialResults (with reports), in stable order."""
    return [r for r in run.scored_results if r.trial.arm == arm]


def cost_robustness_metric_results(
    run: CampaignRun,
    *,
    suite: str,
    arms: Iterable[str] | None = None,
    basis: CostBasis = DEFAULT_COST_BASIS,
    budget: float | None = None,
    merge_conflict_counts: Mapping[str, int] | None = None,
    plan_graph_widths: Mapping[str, int] | None = None,
) -> list[MetricResult]:
    """Emit the six cost+robustness MetricResults per (arm, suite) for a CampaignRun.

    Parameters
    ----------
    run:
        The CampaignRun whose scored results to read.
    suite:
        The suite slug the metrics are reported for (``MetricResult.suite``);
        the caller passes the (arm × suite) slice it owns — this function does
        not partition further.
    arms:
        Arms to emit metrics for; defaults to every arm with ≥1 scored trial.
    basis:
        Cost-matching basis (DOLLARS by default — the pinned headline).
    budget:
        Equal-budget cap on ``basis``. When ``None`` we derive it via
        :func:`equal_budget_for_arms` over the requested arms — the standard
        "compare each arm at the cheaper arm's max" rule.
    merge_conflict_counts:
        Optional mapping ``trial-id → conflict count``. Without it the merge-
        conflict rate is 0 on every trial (the honest "not threaded" answer).
    plan_graph_widths:
        Optional mapping ``arm → graph width`` so the parallel-speedup row
        can correlate against width without re-parsing artifacts here.

    Returns
    -------
    list[MetricResult]
        One MetricResult per (arm, metric) in :data:`COST_ROBUSTNESS_METRIC_NAMES`,
        validated by the canonical schema (the MetricResult constructor).
    """
    by_arm_results: dict[str, list[TrialResult]] = {
        arm_slug: _arm_scored_results(run, arm_slug)
        for arm_slug in (arms if arms is not None else _arms_with_scored(run))
    }

    if budget is None:
        arm_costs = {
            arm_slug: [_trial_cost(r, basis) for r in results]
            for arm_slug, results in by_arm_results.items()
            if results
        }
        if arm_costs:
            budget = equal_budget_for_arms(arm_costs)
        else:
            budget = 0.0

    out: list[MetricResult] = []
    for arm_slug, results in by_arm_results.items():
        out.extend(
            _emit_metrics_for_arm(
                run=run,
                arm=arm_slug,
                arm_results=results,
                suite=suite,
                basis=basis,
                budget=budget,
                merge_conflict_counts=merge_conflict_counts,
                graph_width=(
                    plan_graph_widths.get(arm_slug)
                    if plan_graph_widths is not None
                    else None
                ),
            )
        )
    return out


def _arms_with_scored(run: CampaignRun) -> list[str]:
    """The arm slugs that have at least one scored TrialResult in this run.

    Sorted for deterministic emission order.
    """
    seen: dict[str, None] = {}
    for result in run.scored_results:
        seen.setdefault(result.trial.arm, None)
    return sorted(seen)


def _emit_metrics_for_arm(
    *,
    run: CampaignRun,
    arm: str,
    arm_results: Sequence[TrialResult],
    suite: str,
    basis: CostBasis,
    budget: float,
    merge_conflict_counts: Mapping[str, int] | None,
    graph_width: int | None,
) -> list[MetricResult]:
    """Emit the six MetricResults for ONE arm of a CampaignRun."""
    campaign_id = run.campaign.id
    n_trials = len(arm_results)

    cmr = cost_matched_resolved_for_arm(arm, arm_results, budget=budget, basis=basis)
    speedup = parallel_speedup_for_arm(arm, arm_results, graph_width=graph_width)
    merge = merge_conflict_rate(arm_results, conflict_counts=merge_conflict_counts)
    pause = manual_pause_rate(arm_results)
    retry = gate_retry_depth_for_arm(arm, arm_results)
    regress = regression_rate_for_arm(arm_results)

    return [
        _metric_result(
            campaign=campaign_id,
            arm=arm,
            suite=suite,
            metric_name=METRIC_COST_MATCHED_RESOLVED,
            value=cmr.interval.point,
            ci_low=cmr.interval.low,
            ci_high=cmr.interval.high,
            n_trials=n_trials,
        ),
        _metric_result(
            campaign=campaign_id,
            arm=arm,
            suite=suite,
            metric_name=METRIC_PARALLEL_SPEEDUP,
            value=speedup.speedup,
            # Speedup is a ratio, not a proportion; we have no closed-form 95%
            # CI for it from a single arm's per-trial walls. Report the point
            # value in both bounds — documented at the docstring of
            # ParallelSpeedup — rather than fabricate one.
            ci_low=speedup.speedup,
            ci_high=speedup.speedup,
            n_trials=n_trials,
        ),
        _metric_result(
            campaign=campaign_id,
            arm=arm,
            suite=suite,
            metric_name=METRIC_MERGE_CONFLICT_RATE,
            value=merge.point,
            ci_low=merge.low,
            ci_high=merge.high,
            n_trials=n_trials,
        ),
        _metric_result(
            campaign=campaign_id,
            arm=arm,
            suite=suite,
            metric_name=METRIC_MANUAL_PAUSE_RATE,
            value=pause.point,
            ci_low=pause.low,
            ci_high=pause.high,
            n_trials=n_trials,
        ),
        _metric_result(
            campaign=campaign_id,
            arm=arm,
            suite=suite,
            metric_name=METRIC_GATE_RETRY_DEPTH,
            value=retry.mean,
            ci_low=retry.low,
            ci_high=retry.high,
            n_trials=n_trials,
        ),
        _metric_result(
            campaign=campaign_id,
            arm=arm,
            suite=suite,
            metric_name=METRIC_REGRESSION_RATE,
            value=regress.point,
            ci_low=regress.low,
            ci_high=regress.high,
            n_trials=n_trials,
        ),
    ]


__all__ = [
    "COST_ROBUSTNESS_METRIC_NAMES",
    "DEFAULT_COST_BASIS",
    "GATE_VERDICT_UNVERIFIED",
    "METRIC_COST_MATCHED_RESOLVED",
    "METRIC_GATE_RETRY_DEPTH",
    "METRIC_MANUAL_PAUSE_RATE",
    "METRIC_MERGE_CONFLICT_RATE",
    "METRIC_PARALLEL_SPEEDUP",
    "METRIC_REGRESSION_RATE",
    "CONFIDENCE_LEVEL",
    "CostBasis",
    "CostMatchedResolved",
    "GateRetryDepth",
    "ParallelSpeedup",
    "cost_matched_resolved_for_arm",
    "cost_robustness_metric_results",
    "equal_budget_for_arms",
    "gate_retry_depth_for_arm",
    "manual_pause_rate",
    "merge_conflict_rate",
    "parallel_speedup_for_arm",
    "regression_rate_for_arm",
]
