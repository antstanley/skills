"""Backend-neutral driver: expand a Campaign, schedule Trials, run the lifecycle.

The driver is a scheduler over the Trial lifecycle defined in
``01-domain-model.md`` (§Lifecycle / state machine) and shaped by
``05-harness-architecture.md`` (§Component shape, §Concurrency and
reproducibility). It:

1. expands a ``Campaign`` into ``Trial``s over (arm × instance × seed), with
   ``trialsPerInstance`` seeds per (arm, instance);
2. drives each Trial through ``queued → provisioning → running → captured →
   scored → aggregated``, calling the *injected* ``RunBackend`` then the
   injected ``ScoringBackend`` through their interfaces — never a hardcoded
   backend (per the local-backends change spec, the driver is backend-NEUTRAL);
3. runs independent Trials concurrently up to a configured pool size; and
4. records an infrastructure fault as ``failed`` (excluded from metrics,
   re-queueable), DISTINCT from a legitimate ``resolved: false`` from scoring.

Reproducibility: each Trial carries a deterministic ``seed`` derived from its
(arm, instance) position and its repetition index, and the results list is
sorted into a stable, order-independent key before it is returned, so a run
over a fixed pool size yields the same ordering regardless of which worker
finishes first (``05-harness-architecture.md`` §Concurrency and reproducibility).
"""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from benchmark.harness.backends import RunBackend, ScoringBackend
from benchmark.harness.domain import (
    ARTIFACT_BUNDLE_ID_PREFIX,
    TRIAL_ID_PREFIX,
    ArtifactBundle,
    Campaign,
    ScoreReport,
    Trial,
    new_record_id,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from benchmark.harness.backends import ArmOrSolver
    from benchmark.harness.domain import Arm, TaskInstance

# --- named limits / constants ---------------------------------------------

#: Default size of the worker pool that runs independent Trials concurrently
#: (``05-harness-architecture.md`` §Concurrency and reproducibility — "up to a
#: configured pool size"). A named constant, overridable per ``run_campaign``.
DEFAULT_POOL_SIZE = 4

#: The first repetition's seed; repetition ``i`` of a (arm, instance) pair uses
#: ``SEED_BASE + i`` (deterministic, reproducible across runs).
SEED_BASE = 0

#: Trial lifecycle states the driver walks (mirrors ``01-domain-model.md``
#: §Lifecycle). ``failed`` is the off-path infra-fault sink, kept separate.
STATUS_QUEUED = "queued"
STATUS_PROVISIONING = "provisioning"
STATUS_RUNNING = "running"
STATUS_CAPTURED = "captured"
STATUS_SCORED = "scored"
STATUS_AGGREGATED = "aggregated"
STATUS_FAILED = "failed"


class InfraFault(Exception):
    """An infrastructure fault during a Trial (provision/run/score crash).

    Distinct from a legitimate ``resolved: false`` ScoreReport: a Trial whose
    run raises this lands in ``failed`` and is excluded from scored metrics and
    re-queueable, per ``01-domain-model.md`` §Lifecycle and
    ``05-harness-architecture.md`` §Concurrency and reproducibility.
    """


@dataclass(frozen=True)
class TrialResult:
    """The outcome of driving one Trial through the lifecycle.

    A ``scored`` Trial carries its ``ArtifactBundle`` and ``ScoreReport``; a
    ``failed`` Trial carries neither and records the fault for the re-queue log.
    """

    trial: Trial
    bundle: ArtifactBundle | None = None
    report: ScoreReport | None = None
    fault: str | None = None

    @property
    def is_scored(self) -> bool:
        """Whether this Trial produced a ScoreReport (entered metrics)."""
        return self.trial.status == STATUS_AGGREGATED and self.report is not None

    @property
    def is_failed(self) -> bool:
        """Whether this Trial hit an infra fault (excluded, re-queueable)."""
        return self.trial.status == STATUS_FAILED


@dataclass
class CampaignRun:
    """The result of running a Campaign: per-Trial outcomes, plus rollups."""

    campaign: Campaign
    results: list[TrialResult] = field(default_factory=list)

    @property
    def score_reports(self) -> list[ScoreReport]:
        """One ScoreReport per scored Trial, in stable order."""
        return [r.report for r in self.results if r.is_scored and r.report is not None]

    @property
    def scored_results(self) -> list[TrialResult]:
        """Results that entered metrics (``aggregated`` with a ScoreReport)."""
        return [r for r in self.results if r.is_scored]

    @property
    def failed_results(self) -> list[TrialResult]:
        """Results excluded from metrics (infra ``failed``, re-queueable)."""
        return [r for r in self.results if r.is_failed]

    @property
    def raw_resolved_rate(self) -> float:
        """Raw %Resolved over scored Trials only (failed Trials excluded).

        The fraction of scored Trials whose ScoreReport ``resolved`` is true.
        Returns ``0.0`` when no Trial scored.
        """
        scored = self.scored_results
        if not scored:
            return 0.0
        resolved = sum(1 for r in scored if r.report is not None and r.report.resolved)
        return resolved / len(scored)


def expand_matrix(
    campaign: Campaign,
    arms: Iterable[Arm],
    instances: Iterable[TaskInstance],
) -> list[Trial]:
    """Expand ``campaign`` into ``queued`` Trials over (arm × instance × seed).

    One Trial per (arm, instance, repetition); ``trialsPerInstance`` repetitions
    per (arm, instance), each with a deterministic ``seed`` of ``SEED_BASE + i``.
    ``arms`` and ``instances`` are the resolved records for the campaign's arm
    and suite slugs (the driver does not own a registry; callers resolve slugs
    to records). The expansion is ordered (arm, instance, repetition) so the
    matrix is reproducible.
    """
    arm_list = sorted(arms, key=lambda a: a.slug)
    instance_list = sorted(instances, key=lambda i: i.slug)
    created_at = datetime.now(UTC).isoformat()
    trials: list[Trial] = []
    for arm in arm_list:
        for instance in instance_list:
            for repetition in range(campaign.trialsPerInstance):
                trials.append(
                    Trial(
                        id=new_record_id(TRIAL_ID_PREFIX),
                        campaign=campaign.id,
                        arm=arm.slug,
                        taskInstance=instance.slug,
                        seed=SEED_BASE + repetition,
                        createdAt=created_at,
                        status=STATUS_QUEUED,
                    )
                )
    return trials


def _arm_or_solver(campaign: Campaign, arm: Arm) -> ArmOrSolver:
    """The run-input shape for a Trial: the fixture solver slug or the Arm.

    Per the local-backends change spec, ``Campaign.solver == "fixture"`` runs
    the scripted solver (the run side receives the solver-mode slug); otherwise
    the real ``Arm`` record is handed to the backend.
    """
    if campaign.solver == "fixture":
        return campaign.solver
    return arm


def _drive_trial(
    trial: Trial,
    instance: TaskInstance,
    arm_or_solver: ArmOrSolver,
    run_backend: RunBackend,
    scoring_backend: ScoringBackend,
) -> TrialResult:
    """Drive one Trial through the lifecycle via the INJECTED backends.

    ``queued → provisioning → running → captured`` is the run side (``run``);
    ``scored`` is the scoring side (``score``); ``aggregated`` marks it folded
    into results. An ``InfraFault`` from either backend diverts the Trial to
    ``failed`` (excluded, re-queueable) — never confused with ``resolved: false``.
    """
    # provisioning + running: the injected RunBackend produces (bundle, patch).
    current = replace(trial, status=STATUS_PROVISIONING)
    current = replace(current, status=STATUS_RUNNING)
    try:
        bundle, patch = run_backend.run(instance, arm_or_solver)
    except InfraFault as fault:
        return TrialResult(
            trial=replace(current, status=STATUS_FAILED),
            fault=str(fault) or "run fault",
        )

    # captured: patch + bundle persisted, run environment discarded.
    bundle = _rebind_bundle_trial(bundle, current.id)
    current = replace(
        current,
        status=STATUS_CAPTURED,
        candidatePatch=patch,
        artifactBundle=bundle.id,
    )

    # scored: the injected ScoringBackend applies the patch in a clean env.
    try:
        report = scoring_backend.score(instance, patch)
    except InfraFault as fault:
        return TrialResult(
            trial=replace(current, status=STATUS_FAILED),
            bundle=bundle,
            fault=str(fault) or "score fault",
        )
    report = _rebind_report_trial(report, current.id)
    current = replace(current, status=STATUS_SCORED, scoreReport=report.id)

    # aggregated: the ScoreReport has been folded into the campaign results.
    current = replace(current, status=STATUS_AGGREGATED)
    return TrialResult(trial=current, bundle=bundle, report=report)


def _rebind_bundle_trial(bundle: ArtifactBundle, trial_id: str) -> ArtifactBundle:
    """Re-key a backend's ArtifactBundle to this Trial's id (fresh bundle id)."""
    payload = bundle.to_dict()
    payload["id"] = new_record_id(ARTIFACT_BUNDLE_ID_PREFIX)
    payload["trial"] = trial_id
    return ArtifactBundle.from_dict(payload)


def _rebind_report_trial(report: ScoreReport, trial_id: str) -> ScoreReport:
    """Re-key a backend's ScoreReport to this Trial's id (preserve verdict)."""
    return replace(report, trial=trial_id)


def run_campaign(
    campaign: Campaign,
    arms: Iterable[Arm],
    instances: Iterable[TaskInstance],
    run_backend: RunBackend,
    scoring_backend: ScoringBackend,
    *,
    pool_size: int = DEFAULT_POOL_SIZE,
) -> CampaignRun:
    """Run ``campaign`` end to end through the injected backends.

    Expands the matrix, drives every Trial concurrently (up to ``pool_size``
    workers) through the lifecycle, and returns a ``CampaignRun`` with one
    ``TrialResult`` per Trial — one ``ScoreReport`` per scored Trial — from which
    raw %Resolved is computable (``CampaignRun.raw_resolved_rate``).

    The backends are INJECTED (``run_backend`` / ``scoring_backend``); the driver
    never constructs or names a concrete backend. Results are returned in a
    stable, order-independent order (sorted by arm, instance, seed) so a run is
    reproducible regardless of worker finish order.
    """
    if pool_size < 1:
        raise ValueError(f"pool_size must be >= 1, got {pool_size}")

    instance_by_slug: Mapping[str, TaskInstance] = {i.slug: i for i in instances}
    arm_by_slug: Mapping[str, Arm] = {a.slug: a for a in arms}
    trials = expand_matrix(campaign, arm_by_slug.values(), instance_by_slug.values())

    def work(trial: Trial) -> TrialResult:
        instance = instance_by_slug[trial.taskInstance]
        arm = arm_by_slug[trial.arm]
        return _drive_trial(
            trial,
            instance,
            _arm_or_solver(campaign, arm),
            run_backend,
            scoring_backend,
        )

    results: list[TrialResult] = []
    workers = min(pool_size, len(trials)) or 1
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures: list[Future[TrialResult]] = [pool.submit(work, t) for t in trials]
        for future in futures:
            results.append(future.result())

    results.sort(key=_result_sort_key)
    return CampaignRun(campaign=campaign, results=results)


def _result_sort_key(result: TrialResult) -> tuple[str, str, int]:
    """Order-independent sort key for a TrialResult: (arm, instance, seed)."""
    trial = result.trial
    return (trial.arm, trial.taskInstance, trial.seed)


def order_independent_results(results: Sequence[TrialResult]) -> list[TrialResult]:
    """Return ``results`` in the driver's stable (arm, instance, seed) order."""
    return sorted(results, key=_result_sort_key)
