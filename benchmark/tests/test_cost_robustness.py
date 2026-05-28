"""Cost-matched %Resolved, parallel speedup, and robustness columns: KNOWN answers.

Verifies ``benchmark.harness.stats.cost_robustness`` against authority in
``docs/benchmark/specs/04-metrics.md`` (§Bucket 2 cost-matched %Resolved and
parallel speedup; §Bucket 4 — Robustness) on SYNTHETIC inputs whose values are
hand-computed in each test. No live API, no Docker, no network.

The synthetic inputs are built from the REAL driver types (``CampaignRun``,
``TrialResult``, ``Trial``, ``ArtifactBundle``, ``Telemetry``,
``ScoreReport``, ``GateEvent``) so the metrics consume exactly what the driver
emits. Real-data zeros (gate retry depth = 0, manual-pause rate = 0) are a
sample limitation, documented in the module docstring; this file exercises the
NON-ZERO paths each metric must handle.
"""

from __future__ import annotations

import math

import pytest

from benchmark.harness.domain import (
    ARTIFACT_BUNDLE_ID_PREFIX,
    CAMPAIGN_ID_PREFIX,
    GATE_EVENT_ID_PREFIX,
    SCORE_REPORT_ID_PREFIX,
    TRIAL_ID_PREFIX,
    ArtifactBundle,
    Campaign,
    GateEvent,
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
    COST_ROBUSTNESS_METRIC_NAMES,
    METRIC_COST_MATCHED_RESOLVED,
    METRIC_GATE_RETRY_DEPTH,
    METRIC_MANUAL_PAUSE_RATE,
    METRIC_MERGE_CONFLICT_RATE,
    METRIC_PARALLEL_SPEEDUP,
    METRIC_REGRESSION_RATE,
    CostBasis,
    cost_matched_resolved_for_arm,
    cost_robustness_metric_results,
    equal_budget_for_arms,
    gate_retry_depth_for_arm,
    manual_pause_rate,
    merge_conflict_rate,
    parallel_speedup_for_arm,
    regression_rate_for_arm,
    wilson_interval,
)

_TOL = 1e-9
_CI_TOL = 1e-6


# --- builders over the REAL driver types ------------------------------------


def _campaign(arms: tuple[str, ...] = ("A0", "A1")) -> Campaign:
    return Campaign(
        id=new_record_id(CAMPAIGN_ID_PREFIX),
        createdAt="2026-05-27T00:00:00Z",
        model="claude-opus-4-7",
        arms=list(arms),
        suites=["local-fixture"],
        trialsPerInstance=1,
        backend="local",
        solver="fixture",
    )


def _telemetry(
    *,
    cost: float,
    wall: float,
    in_tokens: int = 1000,
    out_tokens: int = 500,
    turns: int = 10,
) -> Telemetry:
    return Telemetry(
        inputTokens=in_tokens,
        outputTokens=out_tokens,
        costUsd=cost,
        wallClockSeconds=wall,
        agentTurns=turns,
    )


def _trial(arm: str, instance: str) -> Trial:
    return Trial(
        id=new_record_id(TRIAL_ID_PREFIX),
        campaign=new_record_id(CAMPAIGN_ID_PREFIX),
        arm=arm,
        taskInstance=instance,
        seed=0,
        createdAt="2026-05-27T00:00:00Z",
        status=STATUS_AGGREGATED,
    )


def _scored_result(
    arm: str,
    instance: str,
    *,
    resolved: bool,
    regressed: bool = False,
    cost: float = 0.5,
    wall: float = 100.0,
    in_tokens: int = 1000,
    out_tokens: int = 500,
    gate_events: tuple[GateEvent, ...] = (),
) -> TrialResult:
    """A scored (aggregated) TrialResult with a Telemetry-bearing bundle."""
    trial = _trial(arm, instance)
    bundle = ArtifactBundle(
        id=new_record_id(ARTIFACT_BUNDLE_ID_PREFIX),
        trial=trial.id,
        telemetry=_telemetry(
            cost=cost, wall=wall, in_tokens=in_tokens, out_tokens=out_tokens
        ),
    )
    report = ScoreReport(
        id=new_record_id(SCORE_REPORT_ID_PREFIX),
        trial=trial.id,
        resolved=resolved,
        regressed=regressed,
    )
    # Re-key any synthetic GateEvents onto this trial id so they validate.
    events = tuple(
        GateEvent(
            id=event.id,
            trial=trial.id,
            task=event.task,
            gateKind=event.gateKind,
            verdict=event.verdict,
            retryIndex=event.retryIndex,
        )
        for event in gate_events
    )
    return TrialResult(trial=trial, bundle=bundle, report=report, gate_events=events)


def _gate_event(
    *,
    verdict: str,
    retry: int,
    task: str = "T01",
    kind: str = "semi-formal-review",
) -> GateEvent:
    """A GateEvent template; trial is re-keyed by ``_scored_result``."""
    return GateEvent(
        id=new_record_id(GATE_EVENT_ID_PREFIX),
        # Caller-supplied trial replaced inside _scored_result; placeholder OK.
        trial=new_record_id(TRIAL_ID_PREFIX),
        task=task,
        gateKind=kind,
        verdict=verdict,
        retryIndex=retry,
    )


# --- cost-matched %Resolved: hand-computed values ----------------------------


def test_equal_budget_picks_min_of_max_per_arm() -> None:
    # A0 max = 0.20; A1 max = 1.00 -> budget = min(0.20, 1.00) = 0.20.
    arm_costs = {"A0": [0.10, 0.15, 0.20], "A1": [0.50, 0.80, 1.00]}
    assert equal_budget_for_arms(arm_costs) == pytest.approx(0.20, abs=_TOL)


def test_equal_budget_single_arm_is_that_arms_max() -> None:
    assert equal_budget_for_arms({"A1": [0.3, 0.6, 0.4]}) == pytest.approx(0.6)


def test_equal_budget_empty_arm_raises() -> None:
    with pytest.raises(ValueError, match="no scored trials"):
        equal_budget_for_arms({"A0": []})


def test_cost_matched_resolved_dollars_known_answer() -> None:
    # Synthetic A1 with 4 trials at the dollars basis:
    #   trial 1: $0.10, resolved
    #   trial 2: $0.15, resolved
    #   trial 3: $0.50, resolved   <- over budget
    #   trial 4: $0.20, not resolved
    # Budget B = $0.20 (the cheaper-arm cap).
    #   within budget = {1, 2, 4} = 3
    #   resolved within budget = {1, 2} = 2
    # cost_matched_pass_at_1 = 2/4 = 0.5 (denominator = total scored trials).
    results = [
        _scored_result("A1", "inst-1", resolved=True, cost=0.10),
        _scored_result("A1", "inst-2", resolved=True, cost=0.15),
        _scored_result("A1", "inst-3", resolved=True, cost=0.50),
        _scored_result("A1", "inst-4", resolved=False, cost=0.20),
    ]
    cmr = cost_matched_resolved_for_arm(
        "A1", results, budget=0.20, basis=CostBasis.DOLLARS
    )
    assert cmr.n_trials == 4
    assert cmr.within_budget == 3
    assert cmr.resolved_within_budget == 2
    assert math.isclose(cmr.interval.point, 0.5, abs_tol=_TOL)
    # The Wilson interval matches the textbook 2/4 interval directly.
    ref = wilson_interval(2, 4)
    assert math.isclose(cmr.interval.low, ref.low, abs_tol=_CI_TOL)
    assert math.isclose(cmr.interval.high, ref.high, abs_tol=_CI_TOL)


def test_cost_matched_resolved_tokens_basis() -> None:
    # Tokens basis: in+out tokens; budget 1500.
    #   trial 1: 500+500=1000 tokens, resolved              -> in budget, resolved
    #   trial 2: 1000+400=1400 tokens, resolved             -> in budget, resolved
    #   trial 3: 1000+1000=2000 tokens, resolved            -> over budget
    # Expect cost-matched rate = 2/3.
    results = [
        _scored_result("A1", "i1", resolved=True, in_tokens=500, out_tokens=500),
        _scored_result("A1", "i2", resolved=True, in_tokens=1000, out_tokens=400),
        _scored_result("A1", "i3", resolved=True, in_tokens=1000, out_tokens=1000),
    ]
    cmr = cost_matched_resolved_for_arm(
        "A1", results, budget=1500.0, basis=CostBasis.TOKENS
    )
    assert cmr.within_budget == 2
    assert cmr.resolved_within_budget == 2
    assert math.isclose(cmr.interval.point, 2.0 / 3.0, abs_tol=_TOL)


def test_cost_matched_resolved_wall_clock_basis() -> None:
    # wall clock basis; budget 200s; 3 trials at 100/150/250 seconds, all resolved.
    results = [
        _scored_result("A1", "i1", resolved=True, wall=100.0),
        _scored_result("A1", "i2", resolved=True, wall=150.0),
        _scored_result("A1", "i3", resolved=True, wall=250.0),
    ]
    cmr = cost_matched_resolved_for_arm(
        "A1", results, budget=200.0, basis=CostBasis.WALL_CLOCK
    )
    assert cmr.within_budget == 2
    assert cmr.resolved_within_budget == 2
    assert math.isclose(cmr.interval.point, 2.0 / 3.0, abs_tol=_TOL)


def test_cost_matched_resolved_at_arms_own_max_equals_raw() -> None:
    # At B = arm's own max cost every trial is in-budget; cost-matched %Resolved
    # MUST equal raw %Resolved.
    results = [
        _scored_result("A0", "i1", resolved=True, cost=0.05),
        _scored_result("A0", "i2", resolved=False, cost=0.10),
        _scored_result("A0", "i3", resolved=True, cost=0.20),
    ]
    cmr = cost_matched_resolved_for_arm("A0", results, budget=0.20)
    assert cmr.within_budget == 3
    assert cmr.resolved_within_budget == 2
    assert math.isclose(cmr.interval.point, 2.0 / 3.0, abs_tol=_TOL)


# --- parallel speedup: hand-computed ratios ---------------------------------


def test_parallel_speedup_known_ratio() -> None:
    # Per-trial walls 100, 200, 300 -> sequential 600, parallel 300, speedup 2.0.
    results = [
        _scored_result("A1", f"i{i}", resolved=True, wall=w)
        for i, w in enumerate([100.0, 200.0, 300.0])
    ]
    sp = parallel_speedup_for_arm("A1", results, graph_width=3)
    assert sp.n_trials == 3
    assert math.isclose(sp.sequential_estimate_seconds, 600.0, abs_tol=_TOL)
    assert math.isclose(sp.observed_parallel_wall_seconds, 300.0, abs_tol=_TOL)
    assert math.isclose(sp.speedup, 2.0, abs_tol=_TOL)
    assert sp.graph_width == 3


def test_parallel_speedup_single_trial_is_unity() -> None:
    results = [_scored_result("A1", "i1", resolved=True, wall=120.0)]
    sp = parallel_speedup_for_arm("A1", results)
    assert sp.n_trials == 1
    assert sp.speedup == 1.0


def test_parallel_speedup_no_trials_is_unity() -> None:
    sp = parallel_speedup_for_arm("A1", [])
    assert sp.n_trials == 0
    assert sp.speedup == 1.0


def test_parallel_speedup_zero_walls_reports_unity() -> None:
    results = [
        _scored_result("A1", "i1", resolved=True, wall=0.0),
        _scored_result("A1", "i2", resolved=True, wall=0.0),
    ]
    sp = parallel_speedup_for_arm("A1", results)
    assert sp.speedup == 1.0


# --- merge-conflict rate -----------------------------------------------------


def test_merge_conflict_rate_known_fraction() -> None:
    # 4 parallel trials; 1 records ≥1 conflict; rate = 1/4 = 0.25.
    results = [_scored_result("A4", f"i{i}", resolved=True) for i in range(4)]
    counts = {results[0].trial.id: 3}  # one trial with 3 conflicts
    rate = merge_conflict_rate(results, conflict_counts=counts)
    assert math.isclose(rate.point, 0.25, abs_tol=_TOL)
    ref = wilson_interval(1, 4)
    assert math.isclose(rate.low, ref.low, abs_tol=_CI_TOL)
    assert math.isclose(rate.high, ref.high, abs_tol=_CI_TOL)


def test_merge_conflict_rate_no_conflicts_is_zero() -> None:
    results = [_scored_result("A4", f"i{i}", resolved=True) for i in range(3)]
    rate = merge_conflict_rate(results, conflict_counts=None)
    assert rate.point == 0.0


def test_merge_conflict_rate_counts_only_positive() -> None:
    # A zero-count entry is NOT a conflict; only count > 0 toggles the trial.
    results = [_scored_result("A4", f"i{i}", resolved=True) for i in range(2)]
    counts = {results[0].trial.id: 0, results[1].trial.id: 1}
    rate = merge_conflict_rate(results, conflict_counts=counts)
    assert math.isclose(rate.point, 0.5, abs_tol=_TOL)


# --- manual-pause rate -------------------------------------------------------


def test_manual_pause_rate_unverified_fraction() -> None:
    # 4 trials; 1 has an UNVERIFIED verdict -> 1/4.
    results = [
        _scored_result(
            "A1",
            "i0",
            resolved=False,
            gate_events=(_gate_event(verdict="UNVERIFIED", retry=0),),
        ),
        _scored_result(
            "A1",
            "i1",
            resolved=True,
            gate_events=(_gate_event(verdict="PASS", retry=0),),
        ),
        _scored_result(
            "A1",
            "i2",
            resolved=True,
            gate_events=(),
        ),
        _scored_result(
            "A1",
            "i3",
            resolved=False,
            gate_events=(_gate_event(verdict="FAIL", retry=0),),
        ),
    ]
    rate = manual_pause_rate(results)
    assert math.isclose(rate.point, 0.25, abs_tol=_TOL)


def test_manual_pause_rate_zero_when_no_unverified() -> None:
    results = [
        _scored_result(
            "A1",
            "i1",
            resolved=True,
            gate_events=(_gate_event(verdict="PASS", retry=0),),
        ),
        _scored_result(
            "A1",
            "i2",
            resolved=False,
            gate_events=(),
        ),
    ]
    rate = manual_pause_rate(results)
    assert rate.point == 0.0


# --- gate retry depth -------------------------------------------------------


def test_gate_retry_depth_mean_known_value() -> None:
    # retry indices [0, 1, 2, 3] -> mean 1.5.
    results = [
        _scored_result(
            "A1",
            f"i{i}",
            resolved=True,
            gate_events=(_gate_event(verdict="PASS", retry=i),),
        )
        for i in range(4)
    ]
    depth = gate_retry_depth_for_arm("A1", results)
    assert depth.n_events == 4
    assert math.isclose(depth.mean, 1.5, abs_tol=_TOL)
    # Sample sd = sqrt(((0-1.5)^2 + (1-1.5)^2 + (2-1.5)^2 + (3-1.5)^2) / 3)
    # = sqrt(5/3) ≈ 1.290994.
    expected_sd = math.sqrt(5.0 / 3.0)
    expected_half = 1.959963985 * expected_sd / math.sqrt(4.0)
    assert math.isclose(depth.low, 1.5 - expected_half, abs_tol=_CI_TOL)
    assert math.isclose(depth.high, 1.5 + expected_half, abs_tol=_CI_TOL)


def test_gate_retry_depth_no_events_is_zero() -> None:
    results = [_scored_result("A1", "i1", resolved=True, gate_events=())]
    depth = gate_retry_depth_for_arm("A1", results)
    assert depth.n_events == 0
    assert depth.mean == 0.0
    assert depth.low == 0.0
    assert depth.high == 0.0


def test_gate_retry_depth_single_event_no_interval() -> None:
    # One event: mean = retryIndex, low == high == mean (interval undefined).
    results = [
        _scored_result(
            "A1",
            "i1",
            resolved=True,
            gate_events=(_gate_event(verdict="PASS", retry=2),),
        )
    ]
    depth = gate_retry_depth_for_arm("A1", results)
    assert depth.n_events == 1
    assert depth.mean == 2.0
    assert depth.low == 2.0
    assert depth.high == 2.0


# --- regression rate (composed) ---------------------------------------------


def test_regression_rate_known_fraction() -> None:
    results = [
        _scored_result("A1", "i1", resolved=True, regressed=False),
        _scored_result("A1", "i2", resolved=True, regressed=True),
        _scored_result("A1", "i3", resolved=False, regressed=True),
        _scored_result("A1", "i4", resolved=True, regressed=False),
    ]
    rate = regression_rate_for_arm(results)
    assert math.isclose(rate.point, 0.5, abs_tol=_TOL)


# --- MetricResult emission ---------------------------------------------------


def test_cost_robustness_metric_results_emits_six_per_arm() -> None:
    """Every arm with ≥1 scored trial gets the full set of metric rows."""
    a0 = [
        _scored_result("A0", "i1", resolved=False, cost=0.10, wall=30.0),
        _scored_result("A0", "i2", resolved=True, cost=0.20, wall=40.0),
    ]
    a1 = [
        _scored_result(
            "A1",
            "i1",
            resolved=True,
            cost=0.80,
            wall=100.0,
            gate_events=(_gate_event(verdict="UNVERIFIED", retry=1),),
        ),
        _scored_result(
            "A1",
            "i2",
            resolved=True,
            cost=1.20,
            wall=200.0,
            gate_events=(_gate_event(verdict="PASS", retry=0),),
        ),
    ]
    campaign = _campaign(arms=("A0", "A1"))
    run = CampaignRun(campaign=campaign, results=a0 + a1)

    results = cost_robustness_metric_results(run, suite="local-fixture")

    # 6 metrics × 2 arms = 12 rows.
    assert len(results) == 2 * len(COST_ROBUSTNESS_METRIC_NAMES)

    # Each row carries the campaign id, an arm slug, and one of the known names.
    expected_names = set(COST_ROBUSTNESS_METRIC_NAMES)
    by_arm: dict[str, set[str]] = {"A0": set(), "A1": set()}
    for row in results:
        assert row.campaign == campaign.id
        assert row.suite == "local-fixture"
        assert row.metricName in expected_names
        by_arm[row.arm].add(row.metricName)
    assert by_arm["A0"] == expected_names
    assert by_arm["A1"] == expected_names


def test_cost_robustness_metric_results_known_values() -> None:
    """End-to-end: every emitted metric matches its hand-computed value."""
    # A0: cheaper, max cost = 0.20. A1: max cost = 1.20. Budget = $0.20.
    # A0: both within budget; resolved {i2} -> 1/2 cost-matched.
    # A1: neither within budget; 0/2 cost-matched.
    # Wall clocks A0 = [30, 40] -> seq 70, parallel 40, speedup 1.75.
    # Wall clocks A1 = [100, 200] -> seq 300, parallel 200, speedup 1.5.
    # Merge conflicts: A1.i1 has 2 conflicts -> A1 rate = 1/2; A0 rate = 0/2.
    # UNVERIFIED: A1.i1 only -> A1 pause rate = 1/2; A0 = 0/2.
    # Retry indices: A1 events [1, 0] -> mean 0.5; A0 has no events -> 0.0.
    # Regression: A0.i1 regressed -> 1/2; A1 none -> 0/2.
    a0_t1 = _scored_result(
        "A0", "i1", resolved=False, regressed=True, cost=0.10, wall=30.0
    )
    a0_t2 = _scored_result("A0", "i2", resolved=True, cost=0.20, wall=40.0)
    a1_t1 = _scored_result(
        "A1",
        "i1",
        resolved=True,
        cost=0.80,
        wall=100.0,
        gate_events=(_gate_event(verdict="UNVERIFIED", retry=1),),
    )
    a1_t2 = _scored_result(
        "A1",
        "i2",
        resolved=True,
        cost=1.20,
        wall=200.0,
        gate_events=(_gate_event(verdict="PASS", retry=0),),
    )
    a0 = [a0_t1, a0_t2]
    a1 = [a1_t1, a1_t2]

    campaign = _campaign(arms=("A0", "A1"))
    run = CampaignRun(campaign=campaign, results=a0 + a1)
    counts = {a1_t1.trial.id: 2}
    results = cost_robustness_metric_results(
        run,
        suite="local-fixture",
        merge_conflict_counts=counts,
        plan_graph_widths={"A1": 4, "A0": 1},
    )
    by_key = {(r.arm, r.metricName): r for r in results}

    # Cost-matched %Resolved on the AUTO-DERIVED equal budget ($0.20).
    assert math.isclose(
        by_key[("A0", METRIC_COST_MATCHED_RESOLVED)].value, 0.5, abs_tol=_TOL
    )
    assert by_key[("A1", METRIC_COST_MATCHED_RESOLVED)].value == 0.0

    # Parallel speedup.
    assert math.isclose(
        by_key[("A0", METRIC_PARALLEL_SPEEDUP)].value, 70.0 / 40.0, abs_tol=_TOL
    )
    assert math.isclose(
        by_key[("A1", METRIC_PARALLEL_SPEEDUP)].value, 1.5, abs_tol=_TOL
    )

    # Merge-conflict rate.
    assert math.isclose(
        by_key[("A1", METRIC_MERGE_CONFLICT_RATE)].value, 0.5, abs_tol=_TOL
    )
    assert by_key[("A0", METRIC_MERGE_CONFLICT_RATE)].value == 0.0

    # Manual-pause (UNVERIFIED) rate.
    assert math.isclose(
        by_key[("A1", METRIC_MANUAL_PAUSE_RATE)].value, 0.5, abs_tol=_TOL
    )
    assert by_key[("A0", METRIC_MANUAL_PAUSE_RATE)].value == 0.0

    # Gate retry depth (mean retryIndex over events).
    assert math.isclose(
        by_key[("A1", METRIC_GATE_RETRY_DEPTH)].value, 0.5, abs_tol=_TOL
    )
    assert by_key[("A0", METRIC_GATE_RETRY_DEPTH)].value == 0.0

    # Regression rate.
    assert math.isclose(by_key[("A0", METRIC_REGRESSION_RATE)].value, 0.5, abs_tol=_TOL)
    assert by_key[("A1", METRIC_REGRESSION_RATE)].value == 0.0

    # Every row carries an interval (ciLow ≤ value ≤ ciHigh).
    for row in results:
        assert row.ciLow <= row.value + _CI_TOL
        assert row.value <= row.ciHigh + _CI_TOL
        assert row.nTrials == 2


def test_cost_robustness_metric_results_empty_run_is_empty() -> None:
    """No scored trials → no MetricResult rows (defensive edge)."""
    campaign = _campaign(arms=("A0", "A1"))
    run = CampaignRun(campaign=campaign, results=[])
    assert cost_robustness_metric_results(run, suite="local-fixture") == []


def test_cost_robustness_metric_results_explicit_budget_overrides_auto() -> None:
    """Passing ``budget=`` skips the auto equal-budget derivation."""
    a0 = [_scored_result("A0", "i1", resolved=True, cost=0.10)]
    a1 = [_scored_result("A1", "i1", resolved=True, cost=1.00)]
    campaign = _campaign(arms=("A0", "A1"))
    run = CampaignRun(campaign=campaign, results=a0 + a1)
    # With B = $2.00 every trial is in-budget, so cost-matched == raw.
    results = cost_robustness_metric_results(
        run, suite="local-fixture", budget=2.00, basis=CostBasis.DOLLARS
    )
    by_key = {(r.arm, r.metricName): r for r in results}
    assert by_key[("A0", METRIC_COST_MATCHED_RESOLVED)].value == 1.0
    assert by_key[("A1", METRIC_COST_MATCHED_RESOLVED)].value == 1.0
