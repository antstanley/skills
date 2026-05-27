"""Stats tests: outcome metrics and the A1−A0 ablation table on KNOWN answers.

Verifies ``benchmark/harness/stats`` against the authority in
``docs/benchmark/specs/06-scoring-and-statistics.md`` and ``04-metrics.md``:

- the Wilson 95% interval at 0/10, 5/10, 10/10 to textbook values;
- Pass@1 vs Pass@k where they DIFFER (resolved on one trial only);
- McNemar on a textbook discordant pair (b=8, c=2) and the b+c=0 edge;
- regression rate and the failed-trials-EXCLUDED rule, on a CampaignRun that
  mixes scored and failed trials;
- the renderer: both arm rows, the metric columns, the A1−A0 delta row.

Synthetic inputs are built from the REAL driver types (``CampaignRun``,
``TrialResult``, ``Trial``, ``ScoreReport``) so the stats consume exactly what
the driver emits.
"""

from __future__ import annotations

import math

from benchmark.harness.domain import (
    CAMPAIGN_ID_PREFIX,
    SCORE_REPORT_ID_PREFIX,
    TRIAL_ID_PREFIX,
    Campaign,
    ScoreReport,
    Trial,
    new_record_id,
)
from benchmark.harness.driver import (
    STATUS_AGGREGATED,
    STATUS_FAILED,
    CampaignRun,
    TrialResult,
)
from benchmark.harness.stats import (
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
from benchmark.harness.stats.outcome import (
    _exact_binomial_two_sided,
    _trial_instance_map,
)

_TOL = 1e-6


# --- builders over the REAL driver types ------------------------------------


def _campaign(reps: int) -> Campaign:
    return Campaign(
        id=new_record_id(CAMPAIGN_ID_PREFIX),
        createdAt="2026-05-27T00:00:00Z",
        model="claude-opus-4-7",
        arms=["A0", "A1"],
        suites=["local-fixture"],
        trialsPerInstance=reps,
        backend="local",
        solver="fixture",
    )


_CAMPAIGN_ID = new_record_id(CAMPAIGN_ID_PREFIX)


def _scored(
    arm: str, instance: str, *, resolved: bool, regressed: bool = False
) -> TrialResult:
    """A scored (aggregated) TrialResult carrying a ScoreReport with a verdict."""
    trial = Trial(
        id=new_record_id(TRIAL_ID_PREFIX),
        campaign=_CAMPAIGN_ID,
        arm=arm,
        taskInstance=instance,
        seed=0,
        createdAt="2026-05-27T00:00:00Z",
        status=STATUS_AGGREGATED,
    )
    report = ScoreReport(
        id=new_record_id(SCORE_REPORT_ID_PREFIX),
        trial=trial.id,
        resolved=resolved,
        regressed=regressed,
    )
    return TrialResult(trial=trial, report=report)


def _failed(arm: str, instance: str) -> TrialResult:
    """An infra-failed TrialResult: no ScoreReport, excluded from every stat."""
    trial = Trial(
        id=new_record_id(TRIAL_ID_PREFIX),
        campaign=_CAMPAIGN_ID,
        arm=arm,
        taskInstance=instance,
        seed=0,
        createdAt="2026-05-27T00:00:00Z",
        status=STATUS_FAILED,
    )
    return TrialResult(trial=trial, fault="boom")


# --- Wilson interval: textbook known answers --------------------------------


def test_wilson_interval_known_values() -> None:
    # 0/10: point 0, lower bound 0, upper ≈ 0.27753 (textbook Wilson).
    ci0 = wilson_interval(0, 10)
    assert ci0.point == 0.0
    assert ci0.low == 0.0
    assert math.isclose(ci0.high, 0.277533, abs_tol=1e-5)

    # 5/10: symmetric about 0.5, [0.23659, 0.76341] (textbook Wilson).
    ci5 = wilson_interval(5, 10)
    assert math.isclose(ci5.point, 0.5, abs_tol=_TOL)
    assert math.isclose(ci5.low, 0.236593, abs_tol=1e-5)
    assert math.isclose(ci5.high, 0.763407, abs_tol=1e-5)

    # 10/10: point 1, upper bound 1, lower the mirror of the 0/10 upper.
    ci10 = wilson_interval(10, 10)
    assert ci10.point == 1.0
    assert ci10.high == 1.0
    assert math.isclose(ci10.low, 0.722467, abs_tol=1e-5)
    assert math.isclose(ci10.low, 1.0 - ci0.high, abs_tol=_TOL)


def test_wilson_interval_zero_total_is_unit_interval() -> None:
    ci = wilson_interval(0, 0)
    assert (ci.point, ci.low, ci.high) == (0.0, 0.0, 1.0)


# --- Pass@1 vs Pass@k where they differ -------------------------------------


def test_pass_at_1_and_pass_at_k_differ() -> None:
    # One instance, 3 trials, resolved on trial 2 only:
    #   Pass@1 = 1/3 ≈ 0.3333 (mean over trials)
    #   Pass@k = 1.0          (the instance was resolved by >=1 trial)
    reports = [
        _scored("A1", "inst-a", resolved=False).report,
        _scored("A1", "inst-a", resolved=True).report,
        _scored("A1", "inst-a", resolved=False).report,
    ]
    reports = [r for r in reports if r is not None]
    trial_instance = {r.trial: "inst-a" for r in reports}

    p1 = pass_at_1(reports)
    assert math.isclose(p1.point, 1.0 / 3.0, abs_tol=_TOL)

    grouped = group_resolved_by_instance(reports, trial_instance)
    assert pass_at_k(grouped) == 1.0


def test_pass_at_k_groups_by_instance() -> None:
    # inst-a resolved (trial 2), inst-b never resolved -> Pass@k = 0.5.
    results = [
        _scored("A1", "inst-a", resolved=False),
        _scored("A1", "inst-a", resolved=True),
        _scored("A1", "inst-b", resolved=False),
        _scored("A1", "inst-b", resolved=False),
    ]
    reports = [r.report for r in results if r.report is not None]
    trial_instance = {r.trial.id: r.trial.taskInstance for r in results}
    grouped = group_resolved_by_instance(reports, trial_instance)
    assert set(grouped) == {"inst-a", "inst-b"}
    assert pass_at_k(grouped) == 0.5


def test_pass_at_k_empty_is_zero() -> None:
    assert pass_at_k({}) == 0.0


# --- McNemar: textbook case and the no-discordant edge ----------------------


def test_mcnemar_textbook_b8_c2() -> None:
    # Construct shared instances with b=8 (A0 yes, A1 no) and c=2 (A1 yes, A0 no).
    baseline = {}
    treatment = {}
    for i in range(8):  # discordant favouring A0
        baseline[f"b{i}"] = True
        treatment[f"b{i}"] = False
    for i in range(2):  # discordant favouring A1
        baseline[f"c{i}"] = False
        treatment[f"c{i}"] = True
    # a concordant pair so n_pairs > discordant
    baseline["both"] = True
    treatment["both"] = True

    res = mcnemar_delta(baseline, treatment)
    assert res.b == 8
    assert res.c == 2
    assert res.n_pairs == 11
    # Continuity-corrected statistic (|8-2|-1)^2 / (8+2) = 25/10 = 2.5.
    assert math.isclose(res.statistic, 2.5, abs_tol=_TOL)
    # Exact two-sided binomial: 2 * P(X<=2 | Binom(10,0.5)) = 2 * 56/1024 = 0.109375.
    assert res.exact is True
    assert math.isclose(res.p_value, 0.109375, abs_tol=_TOL)
    # Delta = (2/11) resolved by A1 - (8+1)/11 by A0 = (3-9)/11.
    assert math.isclose(res.delta, (3 - 9) / 11, abs_tol=_TOL)


def test_mcnemar_no_discordant_pairs_is_well_defined() -> None:
    # All concordant: b = c = 0 -> delta 0, statistic 0, p 1.0 (no div-by-zero).
    baseline = {"x": True, "y": False}
    treatment = {"x": True, "y": False}
    res = mcnemar_delta(baseline, treatment)
    assert (res.b, res.c) == (0, 0)
    assert res.delta == 0.0
    assert res.statistic == 0.0
    assert res.p_value == 1.0


def test_mcnemar_only_shared_instances_paired() -> None:
    # A1 has an extra instance A0 never ran; it must not enter the pairing.
    baseline = {"shared": True}
    treatment = {"shared": False, "a1-only": True}
    res = mcnemar_delta(baseline, treatment)
    assert res.n_pairs == 1
    assert res.b == 1  # A0 yes, A1 no on the shared instance
    assert res.c == 0


def test_exact_binomial_n_zero_is_one() -> None:
    assert _exact_binomial_two_sided(0, 0) == 1.0


# --- regression rate and the failed-trials-excluded rule --------------------


def test_regression_rate_and_failed_excluded() -> None:
    run = CampaignRun(
        campaign=_campaign(reps=1),
        results=[
            _scored("A1", "inst-a", resolved=True, regressed=True),
            _scored("A1", "inst-b", resolved=False, regressed=False),
            _failed("A1", "inst-c"),  # infra fault: excluded from EVERY stat
        ],
    )
    out = arm_outcome(run, "A1")
    # Only the 2 scored trials enter: n_trials excludes the failed one.
    assert out.n_trials == 2
    assert out.n_instances == 2
    # Regression rate = 1 of 2 scored trials regressed.
    assert math.isclose(out.regression_rate.point, 0.5, abs_tol=_TOL)
    # Pass@1 = 1 of 2 resolved.
    assert math.isclose(out.pass_at_1.point, 0.5, abs_tol=_TOL)
    # The failed trial's instance (inst-c) is absent from the instance map's
    # scored grouping — it contributed nothing.
    reports = [r.report for r in run.scored_results if r.report is not None]
    grouped = group_resolved_by_instance(reports, _trial_instance_map(run))
    assert "inst-c" not in grouped


def test_regression_rate_direct() -> None:
    reports = [
        _scored("A0", "i", resolved=True, regressed=True).report,
        _scored("A0", "i", resolved=True, regressed=False).report,
        _scored("A0", "i", resolved=True, regressed=False).report,
        _scored("A0", "i", resolved=True, regressed=False).report,
    ]
    reports = [r for r in reports if r is not None]
    rr = regression_rate(reports)
    assert math.isclose(rr.point, 0.25, abs_tol=_TOL)


# --- the renderer: both arm rows, metric columns, delta row -----------------


def _two_arm_run() -> CampaignRun:
    # 2 instances x 2 reps per arm. A0 resolves inst-a only; A1 resolves both.
    results = [
        # A0
        _scored("A0", "inst-a", resolved=True),
        _scored("A0", "inst-a", resolved=True),
        _scored("A0", "inst-b", resolved=False),
        _scored("A0", "inst-b", resolved=False),
        # A1
        _scored("A1", "inst-a", resolved=True),
        _scored("A1", "inst-a", resolved=True),
        _scored("A1", "inst-b", resolved=False),
        _scored("A1", "inst-b", resolved=True),  # resolved on one trial
    ]
    return CampaignRun(campaign=_campaign(reps=2), results=results)


def test_ablation_table_structure_and_delta() -> None:
    table = ablation_table(_two_arm_run())
    assert tuple(row.arm for row in table.arms) == ("A0", "A1")

    a0, a1 = table.arms
    # A0: Pass@1 = 2/4 = 0.5; Pass@k = 1/2 instances (inst-a) = 0.5.
    assert math.isclose(a0.pass_at_1.point, 0.5, abs_tol=_TOL)
    assert a0.pass_at_k == 0.5
    # A1: Pass@1 = 3/4 = 0.75; Pass@k = both instances resolved = 1.0.
    assert math.isclose(a1.pass_at_1.point, 0.75, abs_tol=_TOL)
    assert a1.pass_at_k == 1.0

    # Delta: paired on inst-a (both yes) and inst-b (A0 no, A1 yes-by-any).
    # b = 0, c = 1; delta = (2/2 by A1) - (1/2 by A0) = 0.5.
    assert table.delta is not None
    assert (table.delta.b, table.delta.c) == (0, 1)
    assert math.isclose(table.delta.delta, 0.5, abs_tol=_TOL)


def test_render_ablation_table_text() -> None:
    text = render_ablation_table(ablation_table(_two_arm_run()))
    assert "| Arm |" in text
    assert "Pass@1" in text
    assert "Pass@k" in text
    assert "Regression rate" in text
    # Both arm rows present.
    assert "| A0 |" in text
    assert "| A1 |" in text
    # The A1−A0 delta row present with the McNemar result.
    assert "Delta A1−A0" in text
    assert "McNemar" in text


def test_ablation_table_delta_none_when_arm_missing() -> None:
    # Only A0 scored: the delta is not computable, per-arm rows still render.
    run = CampaignRun(
        campaign=_campaign(reps=1),
        results=[_scored("A0", "inst-a", resolved=True)],
    )
    table = ablation_table(run)
    assert table.delta is None
    text = render_ablation_table(table)
    assert "not computable" in text
