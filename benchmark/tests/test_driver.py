"""Driver tests: a small Campaign driven through a backend test-double.

Asserts the task's definition of done:

- a Campaign over a suite completes and yields one ``ScoreReport`` per Trial,
  the driver calling run then score through the INJECTED backend interface;
- raw %Resolved is computable from the per-Trial reports;
- a forced infra fault lands the Trial in ``failed`` (excluded from metrics,
  re-queueable), DISTINCT from a legitimate ``resolved: false``;
- every scored Trial traversed the lifecycle to ``aggregated``.

The backend double here implements BOTH ``RunBackend`` and ``ScoringBackend``,
mirroring ``benchmark/tests/test_backends.py``; one variant raises ``InfraFault``
on a chosen instance to exercise the infra-fault path.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from benchmark.harness import domain
from benchmark.harness.backends import CandidatePatch
from benchmark.harness.domain import (
    Arm,
    ArtifactBundle,
    Campaign,
    ScoreReport,
    TaskInstance,
    Telemetry,
    new_record_id,
)
from benchmark.harness.driver import (
    DEFAULT_POOL_SIZE,
    STATUS_AGGREGATED,
    STATUS_FAILED,
    CampaignRun,
    InfraFault,
    TrialResult,
    expand_matrix,
    run_campaign,
)

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


def _arm(slug: str) -> Arm:
    return Arm(
        slug=slug,
        pluginsEnabled=[],
        gatesEnabled=False,
        specProvided=False,
        executionMode="single",
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
class DoubleBackend:
    """In-memory double implementing BOTH backend protocols (cf. test_backends).

    The run side is the scripted fixture solver: it returns ``patch_to_emit`` and
    a bundle built only from non-oracle inputs. The scoring side holds the hidden
    tests and applies the shared resolution rule. If an instance slug is in
    ``fault_on``, the run side raises ``InfraFault`` so the driver routes the
    Trial to ``failed``.
    """

    patch_to_emit: CandidatePatch = _GOLD_PATCH
    fault_on: frozenset[str] = field(default_factory=frozenset)

    def run(
        self, instance: TaskInstance, arm_or_solver: object
    ) -> tuple[ArtifactBundle, CandidatePatch]:
        if instance.slug in self.fault_on:
            raise InfraFault(f"provisioning crashed for {instance.slug}")
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
        return bundle, self.patch_to_emit

    def score(
        self, instance: TaskInstance, candidate_patch: CandidatePatch
    ) -> ScoreReport:
        resolves = candidate_patch == instance.goldPatch
        fail_to_pass = {sel: resolves for sel in instance.failToPass}
        pass_to_pass = {sel: candidate_patch is not None for sel in instance.passToPass}
        resolved = all(fail_to_pass.values()) and all(pass_to_pass.values())
        regressed = bool(pass_to_pass) and not all(pass_to_pass.values())
        return ScoreReport(
            id=new_record_id(domain.SCORE_REPORT_ID_PREFIX),
            trial=new_record_id(domain.TRIAL_ID_PREFIX),
            resolved=resolved,
            regressed=regressed,
            failToPassResults=fail_to_pass,
            passToPassResults=pass_to_pass,
        )


def test_default_pool_size_is_a_named_constant() -> None:
    assert DEFAULT_POOL_SIZE >= 1


def test_expand_matrix_is_arm_x_instance_x_seed() -> None:
    campaign = _campaign(["A0", "A1"], ["local-fixture"], reps=3)
    arms = [_arm("A0"), _arm("A1")]
    instances = [_instance("localfix__demo__0001")]

    trials = expand_matrix(campaign, arms, instances)

    # 2 arms x 1 instance x 3 seeds = 6 trials.
    assert len(trials) == 6
    seeds = sorted({t.seed for t in trials})
    assert seeds == [0, 1, 2]
    # Every (arm, instance, seed) triple is unique.
    triples = {(t.arm, t.taskInstance, t.seed) for t in trials}
    assert len(triples) == 6
    assert all(t.status == "queued" for t in trials)


def test_small_campaign_yields_one_score_report_per_trial() -> None:
    campaign = _campaign(["A0", "A1"], ["local-fixture"], reps=2)
    arms = [_arm("A0"), _arm("A1")]
    instances = [_instance("localfix__demo__0001"), _instance("localfix__demo__0002")]
    backend = DoubleBackend(patch_to_emit=_GOLD_PATCH)

    run: CampaignRun = run_campaign(campaign, arms, instances, backend, backend)

    # 2 arms x 2 instances x 2 reps = 8 trials, all scored.
    assert len(run.results) == 8
    assert len(run.score_reports) == 8
    assert all(r.trial.status == STATUS_AGGREGATED for r in run.results)
    # The fixture solver emits the gold patch -> every trial resolves.
    assert run.raw_resolved_rate == 1.0
    # Each scored trial links its own ScoreReport.
    for result in run.results:
        assert result.report is not None
        assert result.report.trial == result.trial.id
        assert result.bundle is not None
        assert result.bundle.trial == result.trial.id


def test_noop_patch_is_resolved_false_not_failed() -> None:
    campaign = _campaign(["A0"], ["local-fixture"], reps=1)
    arms = [_arm("A0")]
    instances = [_instance("localfix__demo__0001")]
    backend = DoubleBackend(patch_to_emit=None)  # no-op patch

    run = run_campaign(campaign, arms, instances, backend, backend)

    # A no-op patch is a legitimate scored outcome, NOT an infra failure.
    assert len(run.score_reports) == 1
    assert run.failed_results == []
    assert run.results[0].trial.status == STATUS_AGGREGATED
    assert run.results[0].report is not None
    assert run.results[0].report.resolved is False
    assert run.raw_resolved_rate == 0.0


def test_infra_fault_lands_in_failed_not_scored() -> None:
    campaign = _campaign(["A0"], ["faulty", "healthy"], reps=2)
    arms = [_arm("A0")]
    instances = [_instance("faulty"), _instance("healthy")]
    # Force an infra fault on every trial of the "faulty" instance.
    backend = DoubleBackend(patch_to_emit=_GOLD_PATCH, fault_on=frozenset({"faulty"}))

    run = run_campaign(campaign, arms, instances, backend, backend)

    # 2 instances x 2 reps = 4 trials: 2 healthy scored, 2 faulty failed.
    assert len(run.results) == 4
    failed = run.failed_results
    scored = run.scored_results
    assert len(failed) == 2
    assert len(scored) == 2

    # Faulty trials are 'failed' (excluded, re-queueable), carry no ScoreReport.
    for result in failed:
        assert result.trial.taskInstance == "faulty"
        assert result.trial.status == STATUS_FAILED
        assert result.report is None
        assert result.fault is not None

    # Scored trials are 'aggregated' and resolved; failed are excluded from rate.
    assert all(r.trial.taskInstance == "healthy" for r in scored)
    assert len(run.score_reports) == 2  # one per scored trial only
    assert run.raw_resolved_rate == 1.0  # over the 2 scored, not the 4 total


def test_results_are_order_independent_across_pool_sizes() -> None:
    campaign = _campaign(["A0", "A1"], ["local-fixture"], reps=3)
    arms = [_arm("A1"), _arm("A0")]  # deliberately unsorted input
    instances = [_instance("localfix__demo__0002"), _instance("localfix__demo__0001")]
    backend = DoubleBackend()

    run_serial = run_campaign(campaign, arms, instances, backend, backend, pool_size=1)
    run_parallel = run_campaign(
        campaign, arms, instances, backend, backend, pool_size=4
    )

    def key(result: TrialResult) -> tuple[str, str, int]:
        return (result.trial.arm, result.trial.taskInstance, result.trial.seed)

    assert [key(r) for r in run_serial.results] == [
        key(r) for r in run_parallel.results
    ]
