"""Cost-matched paired-McNemar deltas: per-pair budget, per-family Holm-Bonferroni.

Verifies :func:`benchmark.harness.stats.build_ablation_report`,
:func:`benchmark.harness.stats.ablation_metric_results`,
:func:`benchmark.harness.stats.apply_holm_bonferroni_per_family`,
:func:`benchmark.harness.stats.render_ablation_report` against the spec in
``docs/benchmark/specs/06-scoring-and-statistics.md`` §Confidence intervals
and pairwise tests:

* Each pairwise comparison (A1−A0, A1−A2, A2−A3, A1−A4) carries a cost-matched
  McNemar delta alongside the raw one — same arms, but the per-instance bool is
  ``cost(trial) <= B AND resolved`` at the shared per-pair equal budget B.
* The Holm-Bonferroni adjustment is applied as TWO SEPARATE families of four
  (raw and cost-matched), preserving α = 0.05 per reading rather than
  conflating the two questions.
* Four additional :class:`MetricResult` records named
  ``cost_matched_delta__<label>`` appear on the metric stream from
  :func:`ablation_metric_results`, each schema-valid.
* The rendered report carries a ``### Cost-matched pairwise deltas`` section
  with one bullet per comparison stating the per-pair budget B.
* Negative-space: an arm pair with no shared scored instances yields a
  cost-matched delta with ``b = c = 0`` (no divide-by-zero).
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
    COST_MATCHED_DELTA_METRIC_PREFIX,
    HOLM_BONFERRONI_ALPHA,
    PAIRWISE_DELTAS,
    CostBasis,
    CostMatchedDeltaRow,
    ablation_metric_results,
    apply_holm_bonferroni_per_family,
    build_ablation_report,
    holm_bonferroni_adjusted_pvalues,
    render_ablation_report,
)

_TOL = 1e-9
_SUITE = "greenfield"
_CAMPAIGN_ID = new_record_id(CAMPAIGN_ID_PREFIX)


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


def _cost_matched_run_sign_flip() -> CampaignRun:
    """Synthetic five-arm run where raw and cost-matched A1−A0 deltas DIFFER.

    Two instances per arm, ``trialsPerInstance=1``.

    * **A0** (cheap) resolves BOTH instances at $0.10/trial. Raw Pass@1 = 100%.
    * **A1** (dear) resolves BOTH instances at $1.00/trial. Raw Pass@1 = 100%.
    * **A2** resolves instance-a only at $0.50/trial.
    * **A3** resolves instance-b only at $0.50/trial.
    * **A4** resolves neither at $0.50/trial.

    Equal budget for the A1−A0 pair = min(max($0.10), max($1.00)) = $0.10.

    At that B:
    * A0 stays at 100% cost-matched (both trials within budget).
    * A1 drops to 0% cost-matched (both trials over budget).

    So the RAW A1−A0 delta = 0.0 (both at 100%); the COST-MATCHED A1−A0 delta
    = -1.0 (A1 worse by 100 pp at equal spend). Different sign/magnitude.
    """
    # Conformance scores are passed on every trial so the conformance
    # CI helper does not see a never-set _UNSET sentinel.
    rows: list[TrialResult] = []
    # A0: both resolved at $0.10.
    rows.append(_scored("A0", "inst-a", resolved=True, cost=0.10, conformance=0.8))
    rows.append(_scored("A0", "inst-b", resolved=True, cost=0.10, conformance=0.8))
    # A1: both resolved at $1.00 (over A0's budget).
    rows.append(_scored("A1", "inst-a", resolved=True, cost=1.00, conformance=0.9))
    rows.append(_scored("A1", "inst-b", resolved=True, cost=1.00, conformance=0.9))
    # A2: only inst-a at $0.50.
    rows.append(_scored("A2", "inst-a", resolved=True, cost=0.50, conformance=0.7))
    rows.append(_scored("A2", "inst-b", resolved=False, cost=0.50, conformance=0.4))
    # A3: only inst-b at $0.50.
    rows.append(_scored("A3", "inst-a", resolved=False, cost=0.50, conformance=0.4))
    rows.append(_scored("A3", "inst-b", resolved=True, cost=0.50, conformance=0.7))
    # A4: neither at $0.50.
    rows.append(_scored("A4", "inst-a", resolved=False, cost=0.50, conformance=0.3))
    rows.append(_scored("A4", "inst-b", resolved=False, cost=0.50, conformance=0.3))
    return CampaignRun(campaign=_campaign(), results=rows)


# --- (1) raw and cost-matched A1-A0 differ in sign/magnitude ----------------


def test_cost_matched_a1_minus_a0_has_different_sign_from_raw() -> None:
    """Raw A1−A0 is zero (both arms at 100%); cost-matched A1−A0 is negative.

    The cheaper arm wins on cost-matched ground because the dear arm
    overshoots the shared equal-budget cap.
    """
    report = build_ablation_report(_cost_matched_run_sign_flip())

    raw = next(d for d in report.deltas if d.label == "A1−A0")
    cm = next(d for d in report.cost_matched_deltas if d.label == "A1−A0")

    # Raw: both arms resolved both instances -> delta = 0.0.
    assert math.isclose(raw.mcnemar.delta, 0.0, abs_tol=_TOL)
    assert raw.mcnemar.b == 0
    assert raw.mcnemar.c == 0

    # Cost-matched at B=$0.10: A0 stays 100%, A1 drops to 0% within budget.
    assert math.isclose(cm.budget, 0.10, abs_tol=_TOL)
    assert math.isclose(cm.mcnemar.delta, -1.0, abs_tol=_TOL)
    # Discordant pairs: A0 (baseline) yes, A1 (treatment) no, on both instances.
    assert cm.mcnemar.b == 2
    assert cm.mcnemar.c == 0
    # Sign/magnitude visibly differ from the raw delta.
    assert cm.mcnemar.delta != raw.mcnemar.delta


# --- (2) per-pair budget B is derived from the two arms only ----------------


def test_per_pair_budget_uses_only_the_two_arms_in_the_comparison() -> None:
    """The equal-budget cap B per comparison is derived from the two arms only.

    Spec: "equalising the budget across the two arms" — NOT min over all five.
    Verifies B for each pair: A1−A0 = $0.10, A1−A2 = $0.50, A2−A3 = $0.50,
    A1−A4 = $0.50.
    """
    report = build_ablation_report(_cost_matched_run_sign_flip())
    budgets = {d.label: d.budget for d in report.cost_matched_deltas}
    assert math.isclose(budgets["A1−A0"], 0.10, abs_tol=_TOL)
    assert math.isclose(budgets["A1−A2"], 0.50, abs_tol=_TOL)
    assert math.isclose(budgets["A2−A3"], 0.50, abs_tol=_TOL)
    assert math.isclose(budgets["A1−A4"], 0.50, abs_tol=_TOL)


# --- (3) Holm-Bonferroni is per-family (raw and cost-matched separately) ---


def test_holm_bonferroni_adjusts_within_each_family_of_four() -> None:
    """Adjustment is two separate families of four, not one family of eight."""
    raw_p = [0.005, 0.04, 0.03, 0.05]
    cm_p = [0.03, 0.04, 0.05, 0.06]

    raw_adj, cm_adj = apply_holm_bonferroni_per_family(raw_p, cm_p)

    # Each family was adjusted independently against m = 4.
    expected_raw = holm_bonferroni_adjusted_pvalues(raw_p)
    expected_cm = holm_bonferroni_adjusted_pvalues(cm_p)
    assert raw_adj == expected_raw
    assert cm_adj == expected_cm

    # If we had adjusted as a SINGLE family of eight, the smallest p (0.005)
    # would be inflated by factor 8 (not 4), so the family-of-eight result
    # would differ — verify we did NOT do that.
    pooled_adj = holm_bonferroni_adjusted_pvalues(raw_p + cm_p)
    # raw_adj[0] for p=0.005 with m=4 is 4 * 0.005 = 0.020; pooled would be
    # 8 * 0.005 = 0.040. So the family-of-four answer is strictly less than
    # the family-of-eight answer for the smallest p — confirming separateness.
    assert raw_adj[0] < pooled_adj[0]


def test_report_holm_bonferroni_families_are_separate() -> None:
    """A strong raw signal does not weaken a marginal cost-matched signal.

    Construct deltas where the raw family is uniformly significant and the
    cost-matched family is uniformly marginal. The cost-matched adjusted
    p-values should reflect the cost-matched family ONLY, not the pooled set.
    """
    run = _cost_matched_run_sign_flip()
    report = build_ablation_report(run)

    # Each cost-matched delta carries its OWN Holm-Bonferroni adjusted p,
    # computed within the cost-matched family of four (not against the raw
    # family). The adjusted p is monotone non-decreasing >= the raw p.
    for cmd in report.cost_matched_deltas:
        assert 0.0 <= cmd.adjusted_p <= 1.0
        assert cmd.adjusted_p >= cmd.mcnemar.p_value - _TOL

    # Verify: re-adjusting the four cost-matched raw p-values via
    # holm_bonferroni_adjusted_pvalues directly reproduces the row p-values.
    cm_raw_p = [d.mcnemar.p_value for d in report.cost_matched_deltas]
    expected_adj = holm_bonferroni_adjusted_pvalues(cm_raw_p)
    for cmd, expected in zip(report.cost_matched_deltas, expected_adj, strict=True):
        assert math.isclose(cmd.adjusted_p, expected, abs_tol=_TOL)


# --- (4) rendered report carries both delta sections ------------------------


def test_render_contains_both_pairwise_and_cost_matched_sections() -> None:
    """The rendered report has the existing pairwise-delta section AND a new
    cost-matched section, with one bullet per comparison and the per-comparison
    budget B stated on each cost-matched bullet."""
    report = build_ablation_report(_cost_matched_run_sign_flip())
    text = render_ablation_report(report)

    # Both section headers are present.
    assert "### Pairwise deltas" in text
    assert "### Cost-matched pairwise deltas" in text
    # The cost basis is stated in the cost-matched preamble.
    assert f"Cost basis: {report.cost_basis.value}" in text

    # Four existing raw delta bullets — one per comparison.
    for _, _, label, _ in PAIRWISE_DELTAS:
        assert f"Delta {label}" in text

    # Four new cost-matched delta bullets — one per comparison, each with B.
    for cmd in report.cost_matched_deltas:
        assert f"Cost-matched delta {cmd.label}" in text
        # Per-comparison budget B is on the bullet itself.
        assert f"B={cmd.budget:.4f}" in text


def test_render_cost_matched_section_appears_after_pairwise_section() -> None:
    """The cost-matched section is RENDERED AFTER the existing pairwise section."""
    report = build_ablation_report(_cost_matched_run_sign_flip())
    text = render_ablation_report(report)
    i_pairwise = text.index("### Pairwise deltas")
    i_cm = text.index("### Cost-matched pairwise deltas")
    assert i_pairwise < i_cm


# --- (5) cost_matched_delta__<label> MetricResults emitted -----------------


def test_four_cost_matched_delta_metric_results_emitted() -> None:
    """ablation_metric_results emits one cost_matched_delta__<label> per pair."""
    run = _cost_matched_run_sign_flip()
    results = ablation_metric_results(run, suite=_SUITE)
    cm_rows = [
        r for r in results if r.metricName.startswith(COST_MATCHED_DELTA_METRIC_PREFIX)
    ]
    assert len(cm_rows) == 4

    # Names match the spec example shape: cost_matched_delta__a1_minus_a0, etc.
    names = {r.metricName for r in cm_rows}
    expected = {
        "cost_matched_delta__a1_minus_a0",
        "cost_matched_delta__a1_minus_a2",
        "cost_matched_delta__a2_minus_a3",
        "cost_matched_delta__a1_minus_a4",
    }
    assert names == expected


def test_cost_matched_delta_metric_results_are_schema_valid() -> None:
    """Each cost-matched delta MetricResult round-trips through the schema."""
    run = _cost_matched_run_sign_flip()
    results = ablation_metric_results(run, suite=_SUITE)
    cm_rows = [
        r for r in results if r.metricName.startswith(COST_MATCHED_DELTA_METRIC_PREFIX)
    ]
    assert cm_rows
    for r in cm_rows:
        assert isinstance(r, MetricResult)
        round_tripped = MetricResult.from_dict(r.to_dict())
        assert round_tripped == r
        assert r.id.startswith(METRIC_RESULT_ID_PREFIX)
        assert r.campaign == run.campaign.id
        assert r.suite == _SUITE
        # Treatment arm in the arm slot.
        assert r.arm in ABLATION_ARMS
        # Schema invariant: ciLow <= value <= ciHigh.
        assert r.ciLow <= r.value + _TOL
        assert r.value <= r.ciHigh + _TOL


def test_cost_matched_delta_value_matches_report_row() -> None:
    """The metric-stream value matches the in-memory CostMatchedDeltaRow delta."""
    run = _cost_matched_run_sign_flip()
    report = build_ablation_report(run)
    results = ablation_metric_results(run, suite=_SUITE)

    by_name = {
        r.metricName: r
        for r in results
        if r.metricName.startswith(COST_MATCHED_DELTA_METRIC_PREFIX)
    }
    for cmd in report.cost_matched_deltas:
        name = "cost_matched_delta__" + cmd.label.lower().replace("−", "_minus_")
        mr = by_name[name]
        assert math.isclose(mr.value, cmd.mcnemar.delta, abs_tol=_TOL)
        assert mr.arm == cmd.treatment
        assert mr.nTrials == cmd.mcnemar.n_pairs


def test_cost_matched_delta_significance_flag_encoded_in_ci_bounds() -> None:
    """ciLow == ciHigh ⇔ significant; non-significant rows straddle zero."""
    run = _cost_matched_run_sign_flip()
    report = build_ablation_report(run)
    results = ablation_metric_results(run, suite=_SUITE)
    by_name = {
        r.metricName: r
        for r in results
        if r.metricName.startswith(COST_MATCHED_DELTA_METRIC_PREFIX)
    }
    for cmd in report.cost_matched_deltas:
        name = "cost_matched_delta__" + cmd.label.lower().replace("−", "_minus_")
        mr = by_name[name]
        if cmd.significant_at_alpha:
            # Degenerate-point interval -> ciLow == ciHigh == value.
            assert math.isclose(mr.ciLow, mr.value, abs_tol=_TOL)
            assert math.isclose(mr.ciHigh, mr.value, abs_tol=_TOL)
        else:
            # Interval contains zero (straddles), value is one of the bounds.
            assert mr.ciLow <= 0.0 + _TOL
            assert mr.ciHigh >= 0.0 - _TOL


# --- (6) negative-space: no shared scored instances -------------------------


def test_arm_pair_with_no_shared_instances_yields_zero_delta_no_crash() -> None:
    """An arm pair with no shared scored instances yields b == c == 0 (no NaN)."""
    # Build a run where A1 scores ONLY inst-a and A0 scores ONLY inst-b — the
    # two arms share NO instances. The McNemar pairing intersection is empty.
    rows = [
        _scored("A0", "inst-b", resolved=True, cost=0.10, conformance=0.8),
        _scored("A1", "inst-a", resolved=True, cost=0.10, conformance=0.8),
    ]
    run = CampaignRun(campaign=_campaign(), results=rows)
    report = build_ablation_report(run)
    a1_minus_a0 = next(d for d in report.cost_matched_deltas if d.label == "A1−A0")
    # Well-defined: zero discordants, zero delta, no divide-by-zero.
    assert a1_minus_a0.mcnemar.b == 0
    assert a1_minus_a0.mcnemar.c == 0
    assert a1_minus_a0.mcnemar.n_pairs == 0
    assert a1_minus_a0.mcnemar.delta == 0.0
    # p_value is 1.0 (no test possible), adjusted_p is 1.0.
    assert a1_minus_a0.mcnemar.p_value == 1.0
    assert a1_minus_a0.adjusted_p == 1.0


def test_arm_pair_with_no_scored_arm_yields_well_defined_row() -> None:
    """If one arm in the pair has zero scored trials, row is well-defined."""
    # Build a run where A1 has scored trials but A0 has NONE.
    rows = [
        _scored("A1", "inst-a", resolved=True, cost=0.10, conformance=0.8),
        _scored("A1", "inst-b", resolved=True, cost=0.10, conformance=0.8),
    ]
    run = CampaignRun(campaign=_campaign(), results=rows)
    report = build_ablation_report(run)
    # The in-memory row is still produced (structural completeness).
    a1_minus_a0 = next(d for d in report.cost_matched_deltas if d.label == "A1−A0")
    assert isinstance(a1_minus_a0, CostMatchedDeltaRow)
    assert a1_minus_a0.mcnemar.n_pairs == 0
    assert a1_minus_a0.mcnemar.delta == 0.0
    # Budget defaults to 0.0 when an arm has no costs.
    assert a1_minus_a0.budget == 0.0


# --- (7) cost_basis flows through to the cost-matched section ---------------


def test_cost_matched_section_states_cost_basis() -> None:
    """The cost-matched section preamble names the cost basis (dollars by default)."""
    report = build_ablation_report(
        _cost_matched_run_sign_flip(), cost_basis=CostBasis.DOLLARS
    )
    text = render_ablation_report(report)
    # Cost basis named in BOTH the table header and the cost-matched preamble.
    assert text.count("dollars") >= 2


# --- (8) family choice documented: alpha plumbed through --------------------


def test_cost_matched_delta_alpha_matches_holm_bonferroni_constant() -> None:
    """Every cost-matched DeltaRow carries the Holm-Bonferroni α = 0.05 default."""
    report = build_ablation_report(_cost_matched_run_sign_flip())
    for cmd in report.cost_matched_deltas:
        assert cmd.alpha == HOLM_BONFERRONI_ALPHA
