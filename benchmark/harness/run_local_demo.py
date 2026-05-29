"""Run the local run -> score -> aggregate pipeline end to end, no Docker.

This is the M0 capstone demonstration. It assembles a local ``Campaign``
(``backend: local``, ``solver: fixture``) over the bundled ``local-fixture``
suite and drives it through the *real* task-07 driver (:func:`run_campaign`)
using the *real* local backends — the task-22 :class:`LocalRunBackend` and the
task-20 :class:`LocalScoringBackend`. There is no Docker, no BenchFlow, no API:
the fixture solver emits the instance ``goldPatch`` and the local scorer runs
the hidden ``pytest`` suite in a temp checkout, yielding a deterministic
``resolved`` verdict and a minimal %Resolved.

A reviewer runs this module (``uv run python -m benchmark.harness.run_local_demo``
or :func:`run_local_demo`) to read the verdict and %Resolved printed for both
the fixture solver (``1.0``) and a no-op variant (``0.0``).

The whole pipeline goes through the driver — matrix expansion, the Trial
lifecycle ``queued -> ... -> aggregated``, and the %Resolved rollup
(:attr:`CampaignRun.raw_resolved_rate`) — exactly as the production
``container`` path does, only with the Docker-free backends injected.
"""

from __future__ import annotations

from dataclasses import dataclass

from benchmark.harness import domain
from benchmark.harness.backends import CandidatePatch, LocalRunBackend
from benchmark.harness.domain import (
    ARTIFACT_BUNDLE_ID_PREFIX,
    Arm,
    ArtifactBundle,
    Campaign,
    TaskInstance,
    Telemetry,
    new_record_id,
)
from benchmark.harness.driver import CampaignRun, run_campaign
from benchmark.harness.scoring import LocalScoringBackend
from benchmark.suites.local_fixture import SUITE_SLUG, load_instance

# --- named constants -------------------------------------------------------

#: The arm the demo campaign runs. ``A0`` is the no-plugins, no-gates control
#: arm; the fixture solver ignores the arm's recipe (it emits the goldPatch),
#: so any valid arm slug works — A0 is the honest "control" choice.
DEMO_ARM_SLUG = "A0"

#: The scripted solver mode for the demo campaign (mirrors ``Campaign.solver``).
#: Drives the local run side down the deterministic fixture path.
DEMO_SOLVER = "fixture"

#: The Docker-free run/scoring backend the demo injects into the driver.
DEMO_BACKEND = "local"

#: Repetitions per (arm, instance). A small, deterministic count: enough to
#: show the verdict is stable across repeated trials without slowing the demo.
DEMO_TRIALS_PER_INSTANCE = 3

#: The model recorded on the demo campaign (no model is actually invoked: the
#: fixture solver is scripted). A stable placeholder for the campaign record.
DEMO_MODEL = "claude-opus-4-7"

#: A fixed ``createdAt`` so the demo campaign record is itself reproducible.
DEMO_CREATED_AT = "2026-05-27T00:00:00Z"

#: %Resolved expected with the fixture solver (it emits the resolving goldPatch).
EXPECTED_FIXTURE_RESOLVED_RATE = 1.0

#: %Resolved expected with the no-op solver (its empty patch never resolves).
EXPECTED_NOOP_RESOLVED_RATE = 0.0

#: Telemetry for the no-op solver: like the fixture solver it runs no model, so
#: tokens/cost/turns are zero.
_NOOP_INPUT_TOKENS = 0
_NOOP_OUTPUT_TOKENS = 0
_NOOP_COST_USD = 0.0
_NOOP_WALL_CLOCK_SECONDS = 0.0
_NOOP_AGENT_TURNS = 0


def demo_arm() -> Arm:
    """The control Arm (``A0``) the demo campaign runs over."""
    return Arm(
        slug=DEMO_ARM_SLUG,
        pluginsEnabled=[],
        gatesEnabled=False,
        specProvided=False,
        executionMode="single",
    )


def demo_campaign() -> Campaign:
    """A local ``Campaign``: ``backend: local``, ``solver: fixture``.

    Runs the ``DEMO_ARM_SLUG`` arm over the ``local-fixture`` suite with
    ``DEMO_TRIALS_PER_INSTANCE`` repetitions — the smallest campaign that both
    exercises the full pipeline and demonstrates repetition.
    """
    return Campaign(
        id=new_record_id(domain.CAMPAIGN_ID_PREFIX),
        createdAt=DEMO_CREATED_AT,
        model=DEMO_MODEL,
        arms=[DEMO_ARM_SLUG],
        suites=[SUITE_SLUG],
        trialsPerInstance=DEMO_TRIALS_PER_INSTANCE,
        backend=DEMO_BACKEND,
        solver=DEMO_SOLVER,
    )


@dataclass
class NoOpRunBackend:
    """A ``RunBackend`` that emits the no-op patch (``None``).

    The honest no-op variant: it provisions nothing and returns ``None`` — the
    no-op ``candidatePatch`` per ``backends/interfaces.py`` — so the local
    scorer applies no change and the hidden ``failToPass`` tests never pass.
    Every Trial therefore scores ``resolved: false`` and %Resolved is ``0.0``.
    It is a legitimate ``resolved: false`` (NOT an infra fault): the Trial still
    traverses the lifecycle to ``aggregated`` and enters the metric.
    """

    def __init__(self, trial_id: str | None = None) -> None:
        self._trial_id = trial_id or new_record_id(domain.TRIAL_ID_PREFIX)

    def run(
        self, instance: TaskInstance, arm_or_solver: object
    ) -> tuple[ArtifactBundle, CandidatePatch]:
        """Return an empty bundle and the no-op patch (``None``) for ``instance``."""
        bundle = ArtifactBundle(
            id=new_record_id(ARTIFACT_BUNDLE_ID_PREFIX),
            trial=self._trial_id,
            telemetry=Telemetry(
                inputTokens=_NOOP_INPUT_TOKENS,
                outputTokens=_NOOP_OUTPUT_TOKENS,
                costUsd=_NOOP_COST_USD,
                wallClockSeconds=_NOOP_WALL_CLOCK_SECONDS,
                agentTurns=_NOOP_AGENT_TURNS,
            ),
            transcript=f"no-op solver emitted no patch for {instance.slug}",
        )
        return bundle, None


def run_local_demo(*, noop: bool = False) -> CampaignRun:
    """Drive the local fixture campaign end to end through the task-07 driver.

    Assembles :func:`demo_campaign` over the resolved :func:`demo_arm` and the
    loaded ``local-fixture`` instance, then runs it through
    :func:`run_campaign` with the local backends injected: the task-20
    :class:`LocalScoringBackend` always scores, and the run side is the task-22
    :class:`LocalRunBackend` (fixture solver) by default, or the
    :class:`NoOpRunBackend` when ``noop`` is true.

    Returns the :class:`CampaignRun`; its :attr:`~CampaignRun.raw_resolved_rate`
    is the %Resolved over the fixture trials.
    """
    campaign = demo_campaign()
    arm = demo_arm()
    instance = load_instance()

    run_backend = NoOpRunBackend() if noop else LocalRunBackend()
    scoring_backend = LocalScoringBackend()

    return run_campaign(
        campaign,
        arms=[arm],
        instances=[instance],
        run_backend=run_backend,
        scoring_backend=scoring_backend,
    )


def _format_run(label: str, run: CampaignRun) -> str:
    """Render a CampaignRun's verdict(s) and %Resolved for the console."""
    lines = [f"=== {label} ==="]
    lines.append(
        f"campaign={run.campaign.id} backend={run.campaign.backend} "
        f"solver={run.campaign.solver} "
        f"trialsPerInstance={run.campaign.trialsPerInstance}"
    )
    for result in run.results:
        trial = result.trial
        report = result.report
        verdict = (
            f"resolved={report.resolved} regressed={report.regressed}"
            if report is not None
            else f"fault={result.fault!r}"
        )
        lines.append(
            f"  trial arm={trial.arm} instance={trial.taskInstance} "
            f"seed={trial.seed} status={trial.status} {verdict}"
        )
    lines.append(
        f"  scored={len(run.scored_results)} failed={len(run.failed_results)} "
        f"%Resolved={run.raw_resolved_rate}"
    )
    return "\n".join(lines)


def main() -> None:
    """Run the fixture and no-op variants and print verdicts + %Resolved.

    A reviewer reads, for the fixture solver, every Trial ``resolved=True`` and
    ``%Resolved=1.0``; for the no-op variant, every Trial ``resolved=False`` and
    ``%Resolved=0.0`` — the whole run -> score -> aggregate pipeline, no Docker.
    """
    fixture_run = run_local_demo()
    noop_run = run_local_demo(noop=True)

    print(_format_run("local-fixture campaign (fixture solver)", fixture_run))
    print()
    print(_format_run("local-fixture campaign (no-op solver)", noop_run))
    print()
    print(
        f"fixture %Resolved={fixture_run.raw_resolved_rate} "
        f"(expected {EXPECTED_FIXTURE_RESOLVED_RATE}); "
        f"no-op %Resolved={noop_run.raw_resolved_rate} "
        f"(expected {EXPECTED_NOOP_RESOLVED_RATE})"
    )


if __name__ == "__main__":
    main()
