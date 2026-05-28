"""ScoreReport.gateEscape is populated by the driver pipeline (not downstream).

Implements the negative-and-positive shape of
``docs/benchmark/specs/06-scoring-and-statistics.md`` §The test oracle:

- gated trials (A1, A2) have ``ScoreReport.gateEscape == not report.resolved``
  written onto every report the driver returns;
- non-gated trials (A0, A4) leave the field UNSET (i.e. ``to_dict`` omits it /
  reads back as ``None``) — the driver never propagates a stale gate-escape
  value across trials, even when the same instance is re-run later under A1;
- every emitted ``ScoreReport`` still validates against the canonical schema
  (``ScoreReport.from_dict`` does this on construction);
- the metric ``escape_rate`` returns the same number on the populated reports
  it returned on the un-populated baseline — populating the field does not
  silently shift the metric.

The harness here is the small in-memory backend double from ``test_driver.py``
(NOT re-imported to keep this test independent): one fixture solver, one
instance whose hidden tests are gated against the gold patch, and a
``patch_to_emit`` we can flip to drive ``resolved=True`` vs ``resolved=False``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from benchmark.harness import domain
from benchmark.harness.arms import A0, A1, A2, A4
from benchmark.harness.backends import CandidatePatch
from benchmark.harness.domain import (
    CANONICAL_SCHEMA_PATH,
    Arm,
    ArtifactBundle,
    Campaign,
    ScoreReport,
    TaskInstance,
    Telemetry,
    new_record_id,
)
from benchmark.harness.driver import (
    InfraFault,
    run_campaign,
)
from benchmark.harness.scoring.probes import GATED_ARMS, escape_rate

_GOLD_PATCH = "--- a/mod.py\n+++ b/mod.py\n@@\n+def f():\n+    return 1\n"


def _instance(slug: str) -> TaskInstance:
    return TaskInstance(
        slug=slug,
        suite="local-fixture",
        repo="fixtures/demo",
        baseCommit="0000000",
        problemStatement="Make f() return 1.",
        failToPass=["tests::test_f_returns_one"],
        passToPass=["tests::test_smoke"],
        contaminationTier="authored-private",
        headlessVerifiable=True,
        goldPatch=_GOLD_PATCH,
    )


def _campaign(arms: list[str], suites: list[str], reps: int) -> Campaign:
    return Campaign(
        id=new_record_id(domain.CAMPAIGN_ID_PREFIX),
        createdAt="2026-05-27T00:00:00Z",
        model="claude-opus-4-7",
        arms=arms,
        suites=suites,
        trialsPerInstance=reps,
        backend="local",
        solver="fixture",
    )


@dataclass
class _DoubleBackend:
    """In-memory double implementing BOTH backend protocols (cf. test_driver).

    ``patch_by_instance`` lets the test choose, per instance, whether the
    fixture solver emits the gold patch (``resolved=True``) or a no-op
    (``resolved=False``). Reports the scoring side builds carry NO
    ``gateEscape`` value — the driver pipeline is what populates the field.
    """

    patch_by_instance: dict[str, CandidatePatch] = field(default_factory=dict)
    default_patch: CandidatePatch = _GOLD_PATCH

    def run(
        self, instance: TaskInstance, arm_or_solver: object
    ) -> tuple[ArtifactBundle, CandidatePatch]:
        bundle = ArtifactBundle(
            id=new_record_id(domain.ARTIFACT_BUNDLE_ID_PREFIX),
            trial=new_record_id(domain.TRIAL_ID_PREFIX),
            telemetry=Telemetry(
                inputTokens=10,
                outputTokens=5,
                costUsd=0.0,
                wallClockSeconds=0.1,
                agentTurns=1,
            ),
            transcript=f"solved {instance.slug} with {arm_or_solver}",
        )
        patch = self.patch_by_instance.get(instance.slug, self.default_patch)
        return bundle, patch

    def score(
        self, instance: TaskInstance, candidate_patch: CandidatePatch
    ) -> ScoreReport:
        resolves = candidate_patch == instance.goldPatch
        fail_to_pass = {sel: resolves for sel in instance.failToPass}
        pass_to_pass = {sel: candidate_patch is not None for sel in instance.passToPass}
        resolved = all(fail_to_pass.values()) and all(pass_to_pass.values())
        regressed = bool(pass_to_pass) and not all(pass_to_pass.values())
        # NOTE: the scoring side deliberately does NOT set gateEscape — only
        # the driver pipeline does.
        return ScoreReport(
            id=new_record_id(domain.SCORE_REPORT_ID_PREFIX),
            trial=new_record_id(domain.TRIAL_ID_PREFIX),
            resolved=resolved,
            regressed=regressed,
            failToPassResults=fail_to_pass,
            passToPassResults=pass_to_pass,
        )


_INST_RESOLVED = "fixture__resolved"
_INST_UNRESOLVED = "fixture__unresolved"


def _build_run():
    """A synthetic CampaignRun spanning A0, A1, A2, A4 over two instances.

    One instance resolves (gold patch), the other does not (no-op patch). Each
    arm runs against both instances under one repetition — yielding two A1
    trials (one resolved, one not), one A2 trial against the unresolved
    instance, one A0 trial, and one A4 trial, as the task spells out.
    """
    inst_resolved = _instance(_INST_RESOLVED)
    inst_unresolved = _instance(_INST_UNRESOLVED)
    # A2 only runs on the unresolved instance; A0/A4 run on the resolved one;
    # A1 runs on both. We achieve that by giving each arm its own one-arm
    # campaign and running them one at a time, then aggregating.
    arms_and_instances: list[tuple[Arm, list[TaskInstance]]] = [
        (A0, [inst_resolved]),
        (A1, [inst_resolved, inst_unresolved]),
        (A2, [inst_unresolved]),
        (A4, [inst_resolved]),
    ]
    backend = _DoubleBackend(
        patch_by_instance={
            _INST_RESOLVED: _GOLD_PATCH,
            _INST_UNRESOLVED: None,
        }
    )
    results = []
    for arm, instances in arms_and_instances:
        campaign = _campaign([arm.slug], ["local-fixture"], reps=1)
        run = run_campaign(campaign, [arm], instances, backend, backend)
        results.extend(run.results)
    return results, {
        _INST_RESOLVED: inst_resolved,
        _INST_UNRESOLVED: inst_unresolved,
    }


def test_gated_arms_have_gate_escape_populated() -> None:
    results, _ = _build_run()
    a1_results = [r for r in results if r.trial.arm == "A1"]
    a2_results = [r for r in results if r.trial.arm == "A2"]

    # The task spec says: two A1 trials (one resolved, one not).
    assert len(a1_results) == 2
    a1_by_inst = {r.trial.taskInstance: r for r in a1_results}
    a1_resolved = a1_by_inst[_INST_RESOLVED]
    a1_unresolved = a1_by_inst[_INST_UNRESOLVED]
    assert a1_resolved.report is not None
    assert a1_unresolved.report is not None
    assert a1_resolved.report.resolved is True
    assert a1_unresolved.report.resolved is False
    # gateEscape == not resolved on every gated trial.
    assert a1_resolved.report.gateEscape is False
    assert a1_unresolved.report.gateEscape is True

    # And the single A2 trial (against the unresolved instance).
    assert len(a2_results) == 1
    a2_report = a2_results[0].report
    assert a2_report is not None
    assert a2_report.resolved is False
    assert a2_report.gateEscape is True


def test_non_gated_arms_leave_gate_escape_unset() -> None:
    results, _ = _build_run()
    a0_results = [r for r in results if r.trial.arm == "A0"]
    a4_results = [r for r in results if r.trial.arm == "A4"]

    assert len(a0_results) == 1
    assert len(a4_results) == 1

    # The DoD: non-gated trials (A0, A4) carry ``None`` for gateEscape —
    # i.e. ``to_dict`` omits the key (canonical-schema null/absent are equivalent
    # under the ScoreReport $def).
    for result in a0_results + a4_results:
        assert result.report is not None
        payload = result.report.to_dict()
        assert payload.get("gateEscape") is None, (
            f"non-gated arm {result.trial.arm} must not carry a gateEscape value, "
            f"got {payload.get('gateEscape')!r}"
        )


def test_every_emitted_report_validates_against_canonical_schema() -> None:
    # ScoreReport.from_dict validates on construction; round-tripping the
    # ``to_dict`` payload through ``from_dict`` re-validates every report
    # against ``canonical-types.schema.json`` (the same path that built it).
    assert CANONICAL_SCHEMA_PATH.exists(), CANONICAL_SCHEMA_PATH
    results, _ = _build_run()
    for result in results:
        assert result.report is not None
        # Re-validate through the canonical schema: build a fresh dict, then
        # construct a new ScoreReport from it (calls ``_validate`` on the
        # canonical ``ScoreReport`` $def).
        payload = result.report.to_dict()
        rebuilt = ScoreReport.from_dict(payload)
        assert rebuilt == result.report


def test_escape_rate_unchanged_after_population() -> None:
    # The metric must not silently shift: ``escape_rate`` over the populated
    # reports must equal ``escape_rate`` over the un-populated baseline (a
    # version of the same reports stripped of gateEscape).
    results, instances_by_slug = _build_run()
    gated_results = [r for r in results if r.trial.arm in GATED_ARMS]
    instances_by_trial = {
        r.trial.id: instances_by_slug[r.trial.taskInstance] for r in gated_results
    }

    populated_reports = [r.report for r in gated_results if r.report is not None]

    # An "old" report is the same record minus the populated gateEscape — i.e.
    # what the scoring backend used to return before the driver-side write.
    def _strip_gate_escape(report: ScoreReport) -> ScoreReport:
        payload = report.to_dict()
        payload.pop("gateEscape", None)
        return ScoreReport.from_dict(payload)

    unpopulated_reports = [_strip_gate_escape(r) for r in populated_reports]

    new_rate = escape_rate(populated_reports, instances_by_trial)
    old_rate = escape_rate(unpopulated_reports, instances_by_trial)
    assert new_rate.rate == old_rate.rate
    assert new_rate.total == old_rate.total
    assert new_rate.escaped == old_rate.escaped
    assert new_rate.granularity == old_rate.granularity


def test_stale_gate_escape_does_not_propagate_across_trials() -> None:
    """Re-running an instance under A0 after an A1 escape must NOT leak the
    A1 ``gateEscape`` onto the A0 trial. The driver writes per-arm, not
    per-instance.
    """
    inst = _instance(_INST_UNRESOLVED)
    backend = _DoubleBackend(default_patch=None)  # always unresolved

    # First: run A1 — gateEscape must be True on this report.
    campaign_a1 = _campaign(["A1"], ["local-fixture"], reps=1)
    run_a1 = run_campaign(campaign_a1, [A1], [inst], backend, backend)
    [a1_result] = run_a1.results
    assert a1_result.report is not None
    assert a1_result.report.gateEscape is True

    # Then: re-run the SAME instance under A0 — gateEscape must be absent.
    campaign_a0 = _campaign(["A0"], ["local-fixture"], reps=1)
    run_a0 = run_campaign(campaign_a0, [A0], [inst], backend, backend)
    [a0_result] = run_a0.results
    assert a0_result.report is not None
    assert a0_result.report.to_dict().get("gateEscape") is None


def test_infra_fault_on_gated_arm_carries_no_gate_escape() -> None:
    """An A1 trial that hits an infra fault never has a ScoreReport at all —
    the driver does not pass through a None-gateEscape payload."""

    @dataclass
    class _FaultyBackend(_DoubleBackend):
        def run(  # type: ignore[override]
            self, instance: TaskInstance, arm_or_solver: object
        ) -> tuple[ArtifactBundle, CandidatePatch]:
            raise InfraFault("boom")

    inst = _instance(_INST_UNRESOLVED)
    backend = _FaultyBackend()
    campaign = _campaign(["A1"], ["local-fixture"], reps=1)
    run = run_campaign(campaign, [A1], [inst], backend, backend)
    [result] = run.results
    assert result.is_failed
    assert result.report is None
