"""Ablation report tests: five-arm table, four delta rows, Holm-Bonferroni math.

Verifies ``benchmark.harness.stats.ablation_report`` against authority in
``.specs/benchmark/specs/06-scoring-and-statistics.md`` §Reporting and
``.specs/benchmark/specs/02-arms.md`` §The pairwise deltas:

- the table includes every arm (A0..A4) and every metric column;
- the four delta rows reference the correct arm pair (A1−A0, A1−A2, A2−A3,
  A1−A4) and carry their McNemar result;
- Holm-Bonferroni adjusted p-values match a textbook small example;
- N/A cells appear for A0/A4 on the gate metrics and on plan coverage / DAG
  validity — distinct from a 0.0 cell;
- the renderer's Markdown is deterministic and announces the cost-matching
  basis + the multiple-comparison correction.

Synthetic inputs are built from the REAL driver types so the report consumes
exactly what the driver emits.
"""

from __future__ import annotations

import math

import pytest

from benchmark.harness.domain import (
    ARTIFACT_BUNDLE_ID_PREFIX,
    CAMPAIGN_ID_PREFIX,
    SCORE_REPORT_ID_PREFIX,
    TRIAL_ID_PREFIX,
    ArtifactBundle,
    Campaign,
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
    HOLM_BONFERRONI_ALPHA,
    METRIC_COLUMNS,
    NA_RENDER_TOKEN,
    PAIRWISE_DELTAS,
    PLAN_PRODUCING_ARMS,
    AblationReport,
    CostBasis,
    apply_holm_bonferroni,
    build_ablation_report,
    build_arm_row,
    holm_bonferroni_adjusted_pvalues,
    metric_applies,
    render_ablation_report,
)
from benchmark.harness.stats.ablation_report import (
    METRIC_DAG_VALIDITY,
    METRIC_GATE_CATCH_RATE,
    METRIC_GATE_ESCAPE_RATE,
    METRIC_PASS_AT_1,
    METRIC_PLAN_COVERAGE,
    _cell_value,
)

_TOL = 1e-9


# --- builders over the REAL driver types ------------------------------------


_CAMPAIGN_ID = new_record_id(CAMPAIGN_ID_PREFIX)


def _campaign(reps: int = 1) -> Campaign:
    return Campaign(
        id=_CAMPAIGN_ID,
        createdAt="2026-05-27T00:00:00Z",
        model="claude-opus-4-7",
        arms=list(ABLATION_ARMS),
        suites=["greenfield"],
        trialsPerInstance=reps,
        backend="local",
        solver="fixture",
    )


def _telemetry(
    *,
    cost: float = 0.10,
    wall: float = 100.0,
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
    """A scored TrialResult carrying a ScoreReport + ArtifactBundle telemetry."""
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
    """A small synthetic five-arm CampaignRun with two instances per arm.

    Outcomes are picked so the four deltas are non-trivial:

    * A0 resolves inst-a only, A1 resolves both, A2 resolves inst-a only,
      A3 resolves inst-b only, A4 resolves neither.

    With one trial per (arm, instance) the per-arm Pass@1 is just the
    resolved-rate; the deltas test discordant pairs (A1 yes / A0 no on inst-b
    etc.).
    """
    # arm -> {instance -> resolved}
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
            conformance=0.8 if resolved else 0.4,
            cost=0.10 if arm == "A0" else 0.20,
            wall=50.0 if arm == "A0" else 100.0,
        )
        for arm, by_inst in outcomes.items()
        for instance, resolved in by_inst.items()
    ]
    return CampaignRun(campaign=_campaign(reps=1), results=results)


# --- Holm-Bonferroni: textbook small example --------------------------------


def test_holm_bonferroni_textbook_known_answer() -> None:
    """A textbook 4-test family (Holm 1979 §3 worked example).

    Input p-values: (0.01, 0.04, 0.03, 0.005). m = 4.
    Sorted ascending: 0.005 (rank 1), 0.01 (rank 2), 0.03 (rank 3),
    0.04 (rank 4). Sort-position factors: 4, 3, 2, 1.

        raw_q (sorted)  = 0.020, 0.030, 0.060, 0.040
        monotone (sorted)= 0.020, 0.030, 0.060, 0.060

    Re-permuted to input order: (0.030, 0.060, 0.060, 0.020).
    """
    p = [0.01, 0.04, 0.03, 0.005]
    adj = holm_bonferroni_adjusted_pvalues(p)
    expected = (0.030, 0.060, 0.060, 0.020)
    assert len(adj) == 4
    for got, want in zip(adj, expected, strict=True):
        assert math.isclose(got, want, abs_tol=1e-9)


def test_holm_bonferroni_all_significant_textbook() -> None:
    # m=4, p = (0.005, 0.011, 0.02, 0.04). All adjusted p-values should
    # remain <= 0.05 -- the Holm step-down rejects every hypothesis.
    p = [0.005, 0.011, 0.02, 0.04]
    adj = holm_bonferroni_adjusted_pvalues(p)
    expected = (0.020, 0.033, 0.040, 0.040)
    for got, want in zip(adj, expected, strict=True):
        assert math.isclose(got, want, abs_tol=1e-9)
    assert all(a <= 0.05 for a in adj)


def test_holm_bonferroni_first_failure_stops_rejection() -> None:
    # Textbook step-down stop-at-first-failure: p1=0.005 passes alpha/4=0.0125
    # but p2=0.02 fails alpha/3 ~= 0.01667 at alpha=0.05 -- so only the smallest
    # is rejected. Adjusted-p formulation: adj_(1) = 4*0.005 = 0.020 (<= 0.05),
    # adj_(2) = max(0.020, 3*0.02) = 0.060 (> 0.05).
    p = [0.005, 0.02, 0.03, 0.04]
    adj = holm_bonferroni_adjusted_pvalues(p)
    expected = (0.020, 0.060, 0.060, 0.060)
    for got, want in zip(adj, expected, strict=True):
        assert math.isclose(got, want, abs_tol=1e-9)
    assert sum(a <= 0.05 for a in adj) == 1


def test_holm_bonferroni_clamps_at_one() -> None:
    # Any q > 1 must be clamped to 1.0.
    p = [0.5, 0.6, 0.7, 0.9]
    adj = holm_bonferroni_adjusted_pvalues(p)
    assert all(a == 1.0 for a in adj)


def test_holm_bonferroni_empty_and_single() -> None:
    assert holm_bonferroni_adjusted_pvalues([]) == ()
    # m=1: no correction beyond clamp.
    assert holm_bonferroni_adjusted_pvalues([0.03]) == (0.03,)
    assert holm_bonferroni_adjusted_pvalues([1.5]) == (1.0,)


def test_holm_bonferroni_preserves_input_order_on_ties() -> None:
    # Ties: equal p-values keep input order (stable sort), so the adjusted
    # p-values are well-defined and equal.
    p = [0.02, 0.02, 0.02, 0.02]
    adj = holm_bonferroni_adjusted_pvalues(p)
    # Each input p contributes raw_q = factor * 0.02; the monotone running max
    # ends at 4 * 0.02 = 0.08 for all entries.
    for a in adj:
        assert math.isclose(a, 0.08, abs_tol=1e-9)


# --- ablation report shape: arms, columns, deltas ---------------------------


def test_report_includes_all_five_arms() -> None:
    report = build_ablation_report(_five_arm_run())
    assert isinstance(report, AblationReport)
    arm_slugs = tuple(row.arm for row in report.arms)
    assert arm_slugs == ABLATION_ARMS  # closed five-arm set, in order


def test_report_metric_columns_complete() -> None:
    # The table's column list matches the named METRIC_COLUMNS and every
    # column has an applicability entry.
    report = build_ablation_report(_five_arm_run())
    assert report.metric_columns == METRIC_COLUMNS
    for metric in METRIC_COLUMNS:
        # Applies to A1 at minimum (every metric should apply to the headline arm).
        assert metric_applies(metric, "A1")


def test_report_has_four_delta_rows_with_correct_arm_pairs() -> None:
    report = build_ablation_report(_five_arm_run())
    assert len(report.deltas) == 4
    pairs = [(d.treatment, d.baseline, d.label) for d in report.deltas]
    assert pairs == [
        ("A1", "A0", "A1−A0"),
        ("A1", "A2", "A1−A2"),
        ("A2", "A3", "A2−A3"),
        ("A1", "A4", "A1−A4"),
    ]
    # PAIRWISE_DELTAS constant agrees.
    constant_pairs = [(t, b, label) for (t, b, label, _) in PAIRWISE_DELTAS]
    assert pairs == constant_pairs


def test_delta_rows_carry_mcnemar_and_adjusted_p() -> None:
    report = build_ablation_report(_five_arm_run())
    for d in report.deltas:
        assert d.alpha == HOLM_BONFERRONI_ALPHA
        # adjusted_p in [0, 1].
        assert 0.0 <= d.adjusted_p <= 1.0
        # Monotone w.r.t. raw p across the sorted order is checked above; here
        # just that the McNemar result is structurally populated.
        assert d.mcnemar.n_pairs >= 0
    # Adjusted p-values must be >= the raw p-values (Holm-Bonferroni only
    # INCREASES p-values).
    for d in report.deltas:
        assert d.adjusted_p >= d.mcnemar.p_value - 1e-12


# --- N/A vs 0.0 encoding ----------------------------------------------------


def test_gate_metrics_na_on_a0_and_a4() -> None:
    # No catch/escape inputs supplied AND A0/A4 are not gated -> cells are None.
    report = build_ablation_report(_five_arm_run())
    by_arm = {row.arm: row for row in report.arms}
    for arm in ("A0", "A3", "A4"):
        # A3 is not in GATED_ARMS either (gates are OFF in A3).
        assert by_arm[arm].gate_catch_rate is None
        assert by_arm[arm].gate_escape_rate is None
    # Applicability table agrees.
    assert not metric_applies(METRIC_GATE_CATCH_RATE, "A0")
    assert not metric_applies(METRIC_GATE_CATCH_RATE, "A4")
    assert not metric_applies(METRIC_GATE_ESCAPE_RATE, "A0")
    assert not metric_applies(METRIC_GATE_ESCAPE_RATE, "A4")


def test_plan_metrics_na_on_a0_and_a4() -> None:
    report = build_ablation_report(_five_arm_run())
    by_arm = {row.arm: row for row in report.arms}
    for arm in ("A0", "A4"):
        assert by_arm[arm].plan_coverage is None
        assert by_arm[arm].dag_validity is None
    # Applicability table agrees.
    assert not metric_applies(METRIC_PLAN_COVERAGE, "A0")
    assert not metric_applies(METRIC_PLAN_COVERAGE, "A4")
    assert not metric_applies(METRIC_DAG_VALIDITY, "A0")
    assert not metric_applies(METRIC_DAG_VALIDITY, "A4")
    # Plan-producing arms DO apply.
    for arm in PLAN_PRODUCING_ARMS:
        assert metric_applies(METRIC_PLAN_COVERAGE, arm)
        assert metric_applies(METRIC_DAG_VALIDITY, arm)


def test_cell_value_renders_na_token_for_non_applicable() -> None:
    # Build an A0 row that has data (n_trials > 0) but the gate / plan cells are
    # absent: the renderer must emit the N/A token, not "0.0%".
    report = build_ablation_report(_five_arm_run())
    a0 = next(row for row in report.arms if row.arm == "A0")
    assert _cell_value(a0, METRIC_GATE_CATCH_RATE) == NA_RENDER_TOKEN
    assert _cell_value(a0, METRIC_GATE_ESCAPE_RATE) == NA_RENDER_TOKEN
    assert _cell_value(a0, METRIC_PLAN_COVERAGE) == NA_RENDER_TOKEN
    assert _cell_value(a0, METRIC_DAG_VALIDITY) == NA_RENDER_TOKEN
    # Outcome cell IS rendered (not N/A).
    assert _cell_value(a0, METRIC_PASS_AT_1) != NA_RENDER_TOKEN


def test_gate_metrics_zero_value_distinct_from_na() -> None:
    """When a gated arm reports (0, 5) catch counts, the cell is 0% — not N/A."""
    run = _five_arm_run()
    report = build_ablation_report(
        run,
        gate_catch_counts={"A1": (0, 5), "A2": (0, 5)},
        gate_escape_counts={"A1": (0, 5), "A2": (0, 5)},
    )
    by_arm = {row.arm: row for row in report.arms}
    # A1 has a real (0.0) value -- the rate IS measured, just zero.
    assert by_arm["A1"].gate_catch_rate is not None
    assert by_arm["A1"].gate_catch_rate.point == 0.0
    # A0 / A4 still N/A — no gates ran.
    assert by_arm["A0"].gate_catch_rate is None
    assert by_arm["A4"].gate_catch_rate is None
    # Renderer reflects the distinction.
    cell_a1 = _cell_value(by_arm["A1"], METRIC_GATE_CATCH_RATE)
    cell_a0 = _cell_value(by_arm["A0"], METRIC_GATE_CATCH_RATE)
    assert "0.0%" in cell_a1
    assert cell_a0 == NA_RENDER_TOKEN


# --- delta arm-pair routing -------------------------------------------------


def test_delta_a1_minus_a0_uses_correct_arms() -> None:
    # In the synthetic run: A0 resolves inst-a only; A1 resolves both. On the
    # paired McNemar, the discordant pairs are b=0 (A0 yes / A1 no — none) and
    # c=1 (A1 yes / A0 no — inst-b).
    report = build_ablation_report(_five_arm_run())
    delta = next(d for d in report.deltas if d.label == "A1−A0")
    assert (delta.mcnemar.b, delta.mcnemar.c) == (0, 1)
    assert delta.mcnemar.n_pairs == 2


def test_delta_a2_minus_a3_uses_correct_arms() -> None:
    # A2 resolves inst-a only; A3 resolves inst-b only.
    # Treatment is A2, baseline is A3 (per PAIRWISE_DELTAS).
    # b = baseline (A3) yes AND treatment (A2) no = {inst-b}  -> b=1
    # c = treatment (A2) yes AND baseline (A3) no = {inst-a} -> c=1
    report = build_ablation_report(_five_arm_run())
    delta = next(d for d in report.deltas if d.label == "A2−A3")
    assert delta.treatment == "A2"
    assert delta.baseline == "A3"
    assert (delta.mcnemar.b, delta.mcnemar.c) == (1, 1)
    assert delta.mcnemar.n_pairs == 2


# --- renderer: deterministic, headers, cost basis, correction note ---------


def test_render_includes_cost_basis_header() -> None:
    report = build_ablation_report(_five_arm_run(), cost_basis=CostBasis.DOLLARS)
    text = render_ablation_report(report)
    assert "Cost-matching basis: dollars" in text


def test_render_includes_multiple_comparison_note() -> None:
    report = build_ablation_report(_five_arm_run())
    text = render_ablation_report(report)
    assert "Holm-Bonferroni" in text
    assert "α = 0.05" in text
    # Per-row Holm-Bonferroni adjusted-p annotation.
    assert "Holm-Bonferroni adjusted p" in text


def test_render_includes_every_arm_row() -> None:
    report = build_ablation_report(_five_arm_run())
    text = render_ablation_report(report)
    for arm in ABLATION_ARMS:
        # Each arm is the first cell of one body row.
        assert f"| {arm} |" in text


def test_render_includes_every_delta_label() -> None:
    report = build_ablation_report(_five_arm_run())
    text = render_ablation_report(report)
    for _, _, label, _ in PAIRWISE_DELTAS:
        assert f"Delta {label}" in text


def test_render_includes_na_token() -> None:
    report = build_ablation_report(_five_arm_run())
    text = render_ablation_report(report)
    assert NA_RENDER_TOKEN in text


def test_render_is_deterministic() -> None:
    report = build_ablation_report(_five_arm_run())
    text_a = render_ablation_report(report)
    text_b = render_ablation_report(report)
    assert text_a == text_b


# --- arm-pair: applicability/holm-bonferroni integration --------------------


def test_apply_holm_bonferroni_attaches_significance_flag() -> None:
    # Build a synthetic raw-deltas tuple with KNOWN p-values to verify the
    # wrapper attaches the flag correctly. Build a McNemarResult from scratch.
    from benchmark.harness.stats.outcome import McNemarResult

    fake = [
        (
            label,
            t,
            b,
            isolates,
            McNemarResult(
                b=0, c=0, n_pairs=0, delta=0.0, statistic=0.0, p_value=p, exact=True
            ),
        )
        for ((t, b, label, isolates), p) in zip(
            PAIRWISE_DELTAS, [0.005, 0.02, 0.03, 0.04], strict=True
        )
    ]
    rows = apply_holm_bonferroni(fake)
    expected = (0.020, 0.060, 0.060, 0.060)
    for row, want in zip(rows, expected, strict=True):
        assert math.isclose(row.adjusted_p, want, abs_tol=1e-9)
    # Only the smallest is below alpha (0.020 <= 0.05).
    assert [r.significant_at_alpha for r in rows] == [True, False, False, False]


# --- build_arm_row: error path on unknown arm -------------------------------


def test_build_arm_row_rejects_unknown_arm() -> None:
    with pytest.raises(ValueError, match="A99"):
        build_arm_row(_five_arm_run(), "A99", cost_basis=CostBasis.DOLLARS, budget=0.0)


# --- plan-coverage applicability via supplied artifacts ---------------------


def test_plan_metrics_populated_when_plan_artifacts_supplied() -> None:
    # Minimal spec + plan capture entries that the artifact-metrics module can
    # parse: one component heading in the spec, one task file with an
    # Implements line pointing at it, and a plan.md index with a dep table.
    spec_entry = (
        ".specs/02-components.md\n# Spec\n\n## Component 1: tokenizer\n\nDoes things.\n"
    )
    task_entry = (
        ".specs/plans/p/01-tokenizer.md\n"
        "**Implements:** `.specs/02-components.md` § Component 1: tokenizer\n"
    )
    plan_entry = (
        ".specs/plans/p/plan.md\n"
        "| Task | File | Depends on | Edge | Produces |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 01 | [01](01-tokenizer.md) | — | seed | the tokenizer |\n"
    )
    artifacts_a1 = [task_entry, plan_entry]
    report = build_ablation_report(
        _five_arm_run(),
        spec_artifacts={"A1": [spec_entry]},
        plan_artifacts={"A1": artifacts_a1},
    )
    a1 = next(row for row in report.arms if row.arm == "A1")
    assert a1.plan_coverage is not None
    assert a1.plan_coverage.fraction == 1.0
    assert a1.dag_validity is not None
    assert a1.dag_validity.valid is True
    # A0 still N/A — no artifacts to read.
    a0 = next(row for row in report.arms if row.arm == "A0")
    assert a0.plan_coverage is None
    assert a0.dag_validity is None
