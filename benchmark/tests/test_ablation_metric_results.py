"""Universal MetricResult emission for every ablation column.

Verifies :func:`benchmark.harness.stats.ablation_metric_results` against
``docs/benchmark/specs/04-metrics.md`` §Implementation layout — each metric
is a named MetricResult keyed by (campaign, arm, suite, metricName), carrying
``value``/``ciLow``/``ciHigh``, and the universe of (Arm, Suite) records
covers every applicable column in :data:`METRIC_COLUMNS`.

What this file pins:

* (a) Every ``(metric, applicable arm)`` pair appears once and only once in
  the emitted stream.
* (b) Every emitted MetricResult is schema-valid against the
  :class:`benchmark.harness.domain.MetricResult` constructor (i.e. against the
  ``MetricResult`` ``$def`` in ``canonical-types.schema.json``).
* (c) Every record's ``value`` / ``ciLow`` / ``ciHigh`` agree with the matching
  :class:`ArmRow` cell — both paths share the same Wilson/normal-CI math, so
  the agreement is exact (within float tolerance).
* (d) For A0/A4 the gate metrics (catch/escape) and plan-artifact metrics
  (plan coverage / DAG validity) are ABSENT from the stream — not emitted as
  zero with a wide CI. A3 is also gate-absent (gates are turned off).
* Negative-space: an arm with zero scored trials emits NO rows for ANY metric
  in the stream — the renderer's "no trials" path is the right home for it.

Synthetic inputs are built from the REAL driver types so the metrics consume
exactly what the driver emits.
"""

from __future__ import annotations

import math

from benchmark.harness.domain import (
    ARTIFACT_BUNDLE_ID_PREFIX,
    CAMPAIGN_ID_PREFIX,
    METRIC_RESULT_ID_PREFIX,
    SCORE_REPORT_ID_PREFIX,
    TRIAL_ID_PREFIX,
    ArtifactBundle,
    Campaign,
    MetricResult,
    ScoreReport,
    Telemetry,
    Trial,
    new_record_id,
)
from benchmark.harness.driver import (
    STATUS_AGGREGATED,
    CampaignRun,
    TrialResult,
)
from benchmark.harness.stats import (
    ABLATION_ARMS,
    APPLICABILITY,
    COST_MATCHED_DELTA_METRIC_PREFIX,
    COST_ROBUSTNESS_METRIC_NAMES,
    METRIC_COLUMNS,
    OUTCOME_AND_ARTIFACT_METRIC_NAMES,
    PLAN_PRODUCING_ARMS,
    ablation_metric_results,
    build_ablation_report,
    metric_applies,
)
from benchmark.harness.stats.ablation_report import (
    METRIC_CONFORMANCE,
    METRIC_DAG_VALIDITY,
    METRIC_GATE_CATCH_RATE,
    METRIC_GATE_ESCAPE_RATE,
    METRIC_MEAN_COST_USD,
    METRIC_MEAN_TOKENS,
    METRIC_MEAN_WALL_CLOCK,
    METRIC_PASS_AT_1,
    METRIC_PASS_AT_K,
    METRIC_PLAN_COVERAGE,
)
from benchmark.harness.stats.cost_robustness import (
    METRIC_COST_MATCHED_RESOLVED,
    METRIC_GATE_RETRY_DEPTH,
    METRIC_MANUAL_PAUSE_RATE,
    METRIC_MERGE_CONFLICT_RATE,
    METRIC_PARALLEL_SPEEDUP,
    METRIC_REGRESSION_RATE,
)

_TOL = 1e-9
_CI_TOL = 1e-9
_SUITE = "greenfield"

_CAMPAIGN_ID = new_record_id(CAMPAIGN_ID_PREFIX)


# --- builders --------------------------------------------------------------


def _campaign() -> Campaign:
    return Campaign(
        id=_CAMPAIGN_ID,
        createdAt="2026-05-27T00:00:00Z",
        model="claude-opus-4-7",
        arms=list(ABLATION_ARMS),
        suites=[_SUITE],
        trialsPerInstance=1,
        backend="local",
        solver="fixture",
    )


def _telemetry(*, cost: float = 0.10, wall: float = 100.0) -> Telemetry:
    return Telemetry(
        inputTokens=1000,
        outputTokens=500,
        costUsd=cost,
        wallClockSeconds=wall,
        agentTurns=10,
    )


def _scored(
    arm: str,
    instance: str,
    *,
    resolved: bool,
    regressed: bool = False,
    conformance: float | None = None,
    cost: float = 0.10,
    wall: float = 100.0,
) -> TrialResult:
    trial = Trial(
        id=new_record_id(TRIAL_ID_PREFIX),
        campaign=_CAMPAIGN_ID,
        arm=arm,
        taskInstance=instance,
        seed=0,
        createdAt="2026-05-27T00:00:00Z",
        status=STATUS_AGGREGATED,
    )
    bundle = ArtifactBundle(
        id=new_record_id(ARTIFACT_BUNDLE_ID_PREFIX),
        trial=trial.id,
        telemetry=_telemetry(cost=cost, wall=wall),
    )
    payload: dict[str, object] = {
        "id": new_record_id(SCORE_REPORT_ID_PREFIX),
        "trial": trial.id,
        "resolved": resolved,
        "regressed": regressed,
    }
    if conformance is not None:
        payload["conformanceScore"] = conformance
    report = ScoreReport.from_dict(payload)
    return TrialResult(trial=trial, bundle=bundle, report=report)


def _five_arm_run() -> CampaignRun:
    """Two instances per arm; resolutions and conformance picked to be non-trivial."""
    outcomes: dict[str, dict[str, bool]] = {
        "A0": {"inst-a": True, "inst-b": False},
        "A1": {"inst-a": True, "inst-b": True},
        "A2": {"inst-a": True, "inst-b": False},
        "A3": {"inst-a": False, "inst-b": True},
        "A4": {"inst-a": False, "inst-b": False},
    }
    results = [
        _scored(
            arm,
            instance,
            resolved=resolved,
            # Distinct conformance per (arm, outcome) so the CI math is non-degenerate.
            conformance=0.8 if resolved else 0.4,
            cost=0.10 if arm == "A0" else 0.20,
            wall=50.0 if arm == "A0" else 100.0,
        )
        for arm, by_inst in outcomes.items()
        for instance, resolved in by_inst.items()
    ]
    return CampaignRun(campaign=_campaign(), results=results)


def _plan_artifacts_for_a1_a2_a3() -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Tiny but valid spec + plan capture entries for the plan-producing arms.

    Reused across tests so plan_coverage / dag_validity have data to read.
    """
    spec_entry = (
        "docs/specs/02-components.md\n"
        "# Spec\n\n## Component 1: tokenizer\n\nDoes things.\n"
    )
    task_entry = (
        "docs/plans/p/01-tokenizer.md\n"
        "**Implements:** `docs/specs/02-components.md` § Component 1: tokenizer\n"
    )
    plan_entry = (
        "docs/plans/p/plan.md\n"
        "| Task | File | Depends on | Edge | Produces |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 01 | [01](01-tokenizer.md) | — | seed | the tokenizer |\n"
    )
    spec_artifacts = {arm: [spec_entry] for arm in PLAN_PRODUCING_ARMS}
    plan_artifacts = {arm: [task_entry, plan_entry] for arm in PLAN_PRODUCING_ARMS}
    return spec_artifacts, plan_artifacts


# --- (a) every applicable (arm, metric) appears once and only once ---------


def test_every_applicable_arm_metric_pair_emitted_exactly_once() -> None:
    """For every metric in METRIC_COLUMNS and every applicable arm, exactly one row."""
    run = _five_arm_run()
    spec_artifacts, plan_artifacts = _plan_artifacts_for_a1_a2_a3()

    results = ablation_metric_results(
        run,
        suite=_SUITE,
        spec_artifacts=spec_artifacts,
        plan_artifacts=plan_artifacts,
        gate_catch_counts={"A1": (4, 5), "A2": (3, 5)},
        gate_escape_counts={"A1": (0, 5), "A2": (1, 5)},
    )

    # The cost-matched delta rows are pairwise (one per PAIRWISE_DELTAS, named
    # cost_matched_delta__<label>), not column rows — they are NOT in
    # METRIC_COLUMNS. Filter them out of the column-universe assertions; the
    # delta rows have their own test below.
    column_results = [
        r
        for r in results
        if not r.metricName.startswith(COST_MATCHED_DELTA_METRIC_PREFIX)
    ]

    # The stream's universe of column-metric names is EXACTLY METRIC_COLUMNS (no
    # unknown names, no missing names that apply somewhere).
    emitted_names = {row.metricName for row in column_results}
    assert emitted_names == set(METRIC_COLUMNS)

    # Per metric, the set of arms that emitted EQUALS the applicable arm set.
    by_metric: dict[str, set[str]] = {m: set() for m in METRIC_COLUMNS}
    counts: dict[tuple[str, str], int] = {}
    for row in column_results:
        by_metric[row.metricName].add(row.arm)
        counts[(row.arm, row.metricName)] = counts.get((row.arm, row.metricName), 0) + 1

    # Every (arm, metric) appears once and only once.
    for key, n in counts.items():
        assert n == 1, f"duplicate emission for {key}: {n} rows"

    # Per-metric arm sets match APPLICABILITY (with every arm having scored trials,
    # the emitted set is exactly the applicable set).
    for metric in METRIC_COLUMNS:
        assert by_metric[metric] == APPLICABILITY[metric], (
            f"{metric}: emitted={by_metric[metric]} applicable={APPLICABILITY[metric]}"
        )


def test_metric_columns_universe_equals_sum_of_two_paths() -> None:
    """16 ablation columns = 6 cost-robustness + 10 outcome-and-artifact."""
    assert set(COST_ROBUSTNESS_METRIC_NAMES).isdisjoint(
        set(OUTCOME_AND_ARTIFACT_METRIC_NAMES)
    )
    assert set(COST_ROBUSTNESS_METRIC_NAMES) | set(
        OUTCOME_AND_ARTIFACT_METRIC_NAMES
    ) == set(METRIC_COLUMNS)
    assert len(COST_ROBUSTNESS_METRIC_NAMES) == 6
    assert len(OUTCOME_AND_ARTIFACT_METRIC_NAMES) == 10
    assert len(METRIC_COLUMNS) == 16


# --- (b) each record is schema-valid against the MetricResult $def ---------


def test_every_record_is_schema_valid() -> None:
    """Every emitted record is a MetricResult instance (constructor enforces schema)."""
    run = _five_arm_run()
    spec_artifacts, plan_artifacts = _plan_artifacts_for_a1_a2_a3()
    results = ablation_metric_results(
        run,
        suite=_SUITE,
        spec_artifacts=spec_artifacts,
        plan_artifacts=plan_artifacts,
        gate_catch_counts={"A1": (4, 5), "A2": (3, 5)},
        gate_escape_counts={"A1": (0, 5), "A2": (1, 5)},
    )

    assert results, "expected non-empty MetricResult stream from a fully populated run"
    for row in results:
        assert isinstance(row, MetricResult)
        # Round-trip through to_dict/from_dict re-validates against the schema.
        round_tripped = MetricResult.from_dict(row.to_dict())
        assert round_tripped == row
        # Field-shape spot checks the schema $def encodes.
        assert row.id.startswith(METRIC_RESULT_ID_PREFIX)
        assert row.campaign == run.campaign.id
        assert row.suite == _SUITE
        assert row.arm in ABLATION_ARMS
        # Column metrics are in METRIC_COLUMNS; pairwise cost-matched deltas
        # are named cost_matched_delta__<label> (not a column, but still a
        # schema-valid MetricResult).
        if row.metricName.startswith(COST_MATCHED_DELTA_METRIC_PREFIX):
            assert len(row.metricName) > len(COST_MATCHED_DELTA_METRIC_PREFIX)
        else:
            assert row.metricName in METRIC_COLUMNS
        assert row.nTrials >= 0
        assert row.ciLow <= row.value + _CI_TOL
        assert row.value <= row.ciHigh + _CI_TOL


# --- (c) value/ciLow/ciHigh agree with the matching ArmRow cell ------------


def test_metric_result_values_agree_with_arm_row() -> None:
    """Both paths share the same source-of-truth math; agreement is exact."""
    run = _five_arm_run()
    spec_artifacts, plan_artifacts = _plan_artifacts_for_a1_a2_a3()
    gate_catch = {"A1": (4, 5), "A2": (3, 5)}
    gate_escape = {"A1": (0, 5), "A2": (1, 5)}

    # Build the report the renderer reads — same parameters, so the per-arm
    # ArmRow values match across the two paths exactly.
    report = build_ablation_report(
        run,
        spec_artifacts=spec_artifacts,
        plan_artifacts=plan_artifacts,
        gate_catch_counts=gate_catch,
        gate_escape_counts=gate_escape,
    )
    results = ablation_metric_results(
        run,
        suite=_SUITE,
        spec_artifacts=spec_artifacts,
        plan_artifacts=plan_artifacts,
        gate_catch_counts=gate_catch,
        gate_escape_counts=gate_escape,
    )

    by_arm_metric = {(row.arm, row.metricName): row for row in results}
    rows_by_arm = {arm_row.arm: arm_row for arm_row in report.arms}

    for arm in ABLATION_ARMS:
        arm_row = rows_by_arm[arm]
        for metric in METRIC_COLUMNS:
            if not metric_applies(metric, arm):
                continue
            assert (arm, metric) in by_arm_metric, (
                f"missing emitted MetricResult for ({arm}, {metric})"
            )
            mr = by_arm_metric[(arm, metric)]
            assert mr.nTrials == arm_row.n_trials

            # Compare value/ciLow/ciHigh against the ArmRow cell. Each branch
            # uses the exact same source field the renderer's _cell_value uses.
            if metric == METRIC_PASS_AT_1:
                ci = arm_row.pass_at_1
                assert ci is not None
                assert math.isclose(mr.value, ci.point, abs_tol=_TOL)
                assert math.isclose(mr.ciLow, ci.low, abs_tol=_TOL)
                assert math.isclose(mr.ciHigh, ci.high, abs_tol=_TOL)
            elif metric == METRIC_PASS_AT_K:
                assert arm_row.pass_at_k is not None
                assert math.isclose(mr.value, arm_row.pass_at_k, abs_tol=_TOL)
                # No CI for a scalar fraction over instances → point in both bounds.
                assert mr.ciLow == mr.value
                assert mr.ciHigh == mr.value
            elif metric == METRIC_REGRESSION_RATE:
                ci = arm_row.regression_rate
                assert ci is not None
                assert math.isclose(mr.value, ci.point, abs_tol=_TOL)
                assert math.isclose(mr.ciLow, ci.low, abs_tol=_TOL)
                assert math.isclose(mr.ciHigh, ci.high, abs_tol=_TOL)
            elif metric == METRIC_COST_MATCHED_RESOLVED:
                cmr = arm_row.cost_matched_resolved
                assert cmr is not None
                assert math.isclose(mr.value, cmr.interval.point, abs_tol=_TOL)
                assert math.isclose(mr.ciLow, cmr.interval.low, abs_tol=_TOL)
                assert math.isclose(mr.ciHigh, cmr.interval.high, abs_tol=_TOL)
            elif metric == METRIC_MEAN_TOKENS:
                assert arm_row.mean_input_output_tokens is not None
                assert math.isclose(
                    mr.value, arm_row.mean_input_output_tokens, abs_tol=_TOL
                )
                assert mr.ciLow == mr.value
                assert mr.ciHigh == mr.value
            elif metric == METRIC_MEAN_COST_USD:
                assert arm_row.mean_cost_usd is not None
                assert math.isclose(mr.value, arm_row.mean_cost_usd, abs_tol=_TOL)
                assert mr.ciLow == mr.value
                assert mr.ciHigh == mr.value
            elif metric == METRIC_MEAN_WALL_CLOCK:
                assert arm_row.mean_wall_clock_seconds is not None
                assert math.isclose(
                    mr.value, arm_row.mean_wall_clock_seconds, abs_tol=_TOL
                )
                assert mr.ciLow == mr.value
                assert mr.ciHigh == mr.value
            elif metric == METRIC_PARALLEL_SPEEDUP:
                sp = arm_row.parallel_speedup
                assert sp is not None
                assert math.isclose(mr.value, sp.speedup, abs_tol=_TOL)
                # Ratio: point in both bounds.
                assert math.isclose(mr.ciLow, sp.speedup, abs_tol=_TOL)
                assert math.isclose(mr.ciHigh, sp.speedup, abs_tol=_TOL)
            elif metric == METRIC_CONFORMANCE:
                ci = arm_row.conformance
                assert ci is not None
                assert math.isclose(mr.value, ci.point, abs_tol=_TOL)
                assert math.isclose(mr.ciLow, ci.low, abs_tol=_TOL)
                assert math.isclose(mr.ciHigh, ci.high, abs_tol=_TOL)
            elif metric == METRIC_PLAN_COVERAGE:
                pc = arm_row.plan_coverage
                assert pc is not None
                assert math.isclose(mr.value, pc.fraction, abs_tol=_TOL)
                assert mr.ciLow == mr.value
                assert mr.ciHigh == mr.value
            elif metric == METRIC_DAG_VALIDITY:
                dv = arm_row.dag_validity
                assert dv is not None
                assert mr.value == (1.0 if dv.valid else 0.0)
                assert mr.ciLow == mr.value
                assert mr.ciHigh == mr.value
            elif metric == METRIC_GATE_CATCH_RATE:
                ci = arm_row.gate_catch_rate
                assert ci is not None
                assert math.isclose(mr.value, ci.point, abs_tol=_TOL)
                assert math.isclose(mr.ciLow, ci.low, abs_tol=_TOL)
                assert math.isclose(mr.ciHigh, ci.high, abs_tol=_TOL)
            elif metric == METRIC_GATE_ESCAPE_RATE:
                ci = arm_row.gate_escape_rate
                assert ci is not None
                assert math.isclose(mr.value, ci.point, abs_tol=_TOL)
                assert math.isclose(mr.ciLow, ci.low, abs_tol=_TOL)
                assert math.isclose(mr.ciHigh, ci.high, abs_tol=_TOL)
            elif metric == METRIC_MERGE_CONFLICT_RATE:
                ci = arm_row.merge_conflict_rate
                assert ci is not None
                assert math.isclose(mr.value, ci.point, abs_tol=_TOL)
                assert math.isclose(mr.ciLow, ci.low, abs_tol=_TOL)
                assert math.isclose(mr.ciHigh, ci.high, abs_tol=_TOL)
            elif metric == METRIC_MANUAL_PAUSE_RATE:
                ci = arm_row.manual_pause_rate
                assert ci is not None
                assert math.isclose(mr.value, ci.point, abs_tol=_TOL)
                assert math.isclose(mr.ciLow, ci.low, abs_tol=_TOL)
                assert math.isclose(mr.ciHigh, ci.high, abs_tol=_TOL)
            elif metric == METRIC_GATE_RETRY_DEPTH:
                gr = arm_row.gate_retry_depth
                assert gr is not None
                assert math.isclose(mr.value, gr.mean, abs_tol=_TOL)
                assert math.isclose(mr.ciLow, gr.low, abs_tol=_TOL)
                assert math.isclose(mr.ciHigh, gr.high, abs_tol=_TOL)
            else:  # pragma: no cover -- defensive: every column has a branch.
                raise AssertionError(f"unhandled metric in test: {metric!r}")


# --- (d) non-applicable cells are ABSENT, not zero with a wide CI -----------


def test_gate_and_plan_metrics_absent_for_non_applicable_arms() -> None:
    """A0/A4: gate AND plan metrics absent. A3: gate metrics absent (gates off)."""
    run = _five_arm_run()
    spec_artifacts, plan_artifacts = _plan_artifacts_for_a1_a2_a3()
    results = ablation_metric_results(
        run,
        suite=_SUITE,
        spec_artifacts=spec_artifacts,
        plan_artifacts=plan_artifacts,
        # Supply gate counts to PROVE the absence is from non-applicability,
        # not from missing input — for A0/A4 the counts would be ignored anyway
        # (and we deliberately do not pass any for A0/A3/A4 below).
        gate_catch_counts={"A1": (4, 5), "A2": (3, 5)},
        gate_escape_counts={"A1": (0, 5), "A2": (1, 5)},
    )
    by_key = {(row.arm, row.metricName) for row in results}

    # Gate metrics: absent on A0, A3 (gates off), A4 — they would be zero
    # rates otherwise, but the metric does not APPLY to those arms.
    for arm in ("A0", "A3", "A4"):
        assert (arm, METRIC_GATE_CATCH_RATE) not in by_key
        assert (arm, METRIC_GATE_ESCAPE_RATE) not in by_key

    # Plan metrics: absent on A0 and A4 (no plan produced); present on A1, A2, A3.
    for arm in ("A0", "A4"):
        assert (arm, METRIC_PLAN_COVERAGE) not in by_key
        assert (arm, METRIC_DAG_VALIDITY) not in by_key
    for arm in PLAN_PRODUCING_ARMS:
        assert (arm, METRIC_PLAN_COVERAGE) in by_key
        assert (arm, METRIC_DAG_VALIDITY) in by_key


def test_gate_metric_absent_distinct_from_zero_rate() -> None:
    """A gated arm that caught nothing emits 0.0; a non-gated arm emits nothing."""
    run = _five_arm_run()
    results = ablation_metric_results(
        run,
        suite=_SUITE,
        # A1 actually ran gates and caught 0 of 5 — that is a measurable 0% rate.
        gate_catch_counts={"A1": (0, 5)},
        gate_escape_counts={"A1": (0, 5)},
    )
    by_key = {(row.arm, row.metricName): row for row in results}

    # A1's gate-catch row is PRESENT with value 0.0 (rate IS measured, just zero).
    assert ("A1", METRIC_GATE_CATCH_RATE) in by_key
    assert by_key[("A1", METRIC_GATE_CATCH_RATE)].value == 0.0
    # A0 / A4 have no gate-catch row at all — the metric does not apply.
    assert ("A0", METRIC_GATE_CATCH_RATE) not in by_key
    assert ("A4", METRIC_GATE_CATCH_RATE) not in by_key


# --- negative-space: zero-trial arms emit no rows ---------------------------


def test_arm_with_zero_scored_trials_emits_no_rows() -> None:
    """An arm absent from CampaignRun.scored_results contributes 0 MetricResults."""
    # Build a run with only A0 and A1 trials (no A2/A3/A4 at all).
    results = [
        _scored("A0", "i1", resolved=True, conformance=0.5),
        _scored("A1", "i1", resolved=True, conformance=0.5),
    ]
    run = CampaignRun(campaign=_campaign(), results=results)

    emitted = ablation_metric_results(run, suite=_SUITE)
    arms_emitted = {row.arm for row in emitted}
    assert arms_emitted == {"A0", "A1"}
    # No row at all for the un-sampled arms — NOT a zero-valued row with nTrials=0.
    for row in emitted:
        assert row.arm not in {"A2", "A3", "A4"}
        # Every emitted row has nTrials >= 1 (this is a scored arm).
        assert row.nTrials >= 1


def test_empty_run_emits_no_rows() -> None:
    """A CampaignRun with zero scored trials produces an empty MetricResult stream."""
    run = CampaignRun(campaign=_campaign(), results=[])
    assert ablation_metric_results(run, suite=_SUITE) == []


# --- composition: ablation = cost-robustness ∪ outcome-and-artifact --------


def test_ablation_metric_results_extends_cost_robustness_metric_results() -> None:
    """ablation_metric_results' cost-robustness subset matches the lower-level emitter.

    The wrapper preserves :func:`cost_robustness_metric_results` as the stable
    lower-level entry point: every cost-robustness MetricResult emitted by
    :func:`ablation_metric_results` has the same (arm, metricName, value,
    ciLow, ciHigh, nTrials) as the lower-level emitter would produce.
    """
    from benchmark.harness.stats import cost_robustness_metric_results

    run = _five_arm_run()
    spec_artifacts, plan_artifacts = _plan_artifacts_for_a1_a2_a3()
    kwargs = {
        "suite": _SUITE,
        "spec_artifacts": spec_artifacts,
        "plan_artifacts": plan_artifacts,
        "gate_catch_counts": {"A1": (4, 5), "A2": (3, 5)},
        "gate_escape_counts": {"A1": (0, 5), "A2": (1, 5)},
    }

    full = ablation_metric_results(run, **kwargs)  # type: ignore[arg-type]

    # The cost-robustness path called independently — same arms, same budget.
    cr = cost_robustness_metric_results(run, suite=_SUITE)

    # Compare on the (arm, metricName) key — record ids differ (fresh new_record_id).
    full_cr = {
        (r.arm, r.metricName): (r.value, r.ciLow, r.ciHigh, r.nTrials)
        for r in full
        if r.metricName in COST_ROBUSTNESS_METRIC_NAMES
    }
    direct = {
        (r.arm, r.metricName): (r.value, r.ciLow, r.ciHigh, r.nTrials) for r in cr
    }
    assert full_cr == direct
