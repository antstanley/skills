"""Tests for the M0 local pipeline demonstration (task 23).

These drive the SHIPPED local demo (:mod:`benchmark.harness.run_local_demo`)
through the *real* task-07 driver and the *real* local backends — no Docker, no
test-double — to assert the task's definition of done:

- the driver runs the local campaign (``backend: local``, ``solver: fixture``)
  over the ``local-fixture`` suite end to end and every fixture Trial resolves;
- the fixture verdict is DETERMINISTIC: the same verdict on every repeated run;
- %Resolved over the fixture trials is ``1.0`` with the fixture solver and
  ``0.0`` with the no-op variant;
- every scored Trial traversed the lifecycle to ``aggregated`` (entered metrics)
  with no infra faults.
"""

from __future__ import annotations

from benchmark.harness.driver import STATUS_AGGREGATED
from benchmark.harness.run_local_demo import (
    DEMO_ARM_SLUG,
    DEMO_BACKEND,
    DEMO_SOLVER,
    DEMO_TRIALS_PER_INSTANCE,
    EXPECTED_FIXTURE_RESOLVED_RATE,
    EXPECTED_NOOP_RESOLVED_RATE,
    run_local_demo,
)
from benchmark.suites.local_fixture import INSTANCE_SLUG


def test_fixture_campaign_runs_end_to_end_and_resolves() -> None:
    """The driver runs the local fixture campaign and every Trial resolves."""
    run = run_local_demo()

    # One Trial per repetition, all scored (no infra faults), all aggregated.
    assert len(run.results) == DEMO_TRIALS_PER_INSTANCE
    assert len(run.scored_results) == DEMO_TRIALS_PER_INSTANCE
    assert not run.failed_results
    for result in run.results:
        assert result.trial.status == STATUS_AGGREGATED
        assert result.trial.arm == DEMO_ARM_SLUG
        assert result.trial.taskInstance == INSTANCE_SLUG
        assert result.report is not None
        assert result.report.resolved is True
        assert result.report.regressed is False

    # It really is the local pipeline.
    assert run.campaign.backend == DEMO_BACKEND
    assert run.campaign.solver == DEMO_SOLVER


def test_fixture_verdict_is_deterministic_across_repeated_runs() -> None:
    """Repeated runs of the same local campaign yield the same verdict."""
    verdicts = [
        tuple(
            (r.trial.seed, r.report.resolved, r.report.regressed)
            for r in run_local_demo().results
            if r.report is not None
        )
        for _ in range(3)
    ]

    # Every run produced the identical (seed, resolved, regressed) tuple-set,
    # in the driver's stable order — the fixture trial resolves deterministically.
    first = verdicts[0]
    assert all(v == first for v in verdicts)
    assert all(resolved is True for _, resolved, _ in first)


def test_fixture_resolved_rate_is_one() -> None:
    """%Resolved over the fixture trials is 1.0 with the fixture solver."""
    run = run_local_demo()
    assert run.raw_resolved_rate == EXPECTED_FIXTURE_RESOLVED_RATE


def test_noop_variant_resolved_rate_is_zero() -> None:
    """%Resolved is 0.0 with the no-op solver, as a legitimate resolved:false.

    The no-op trials still score (no infra fault) and reach ``aggregated``; they
    simply never resolve, so they enter the metric at 0.0 — distinct from a
    ``failed`` Trial excluded from metrics.
    """
    run = run_local_demo(noop=True)

    assert len(run.scored_results) == DEMO_TRIALS_PER_INSTANCE
    assert not run.failed_results
    for result in run.results:
        assert result.trial.status == STATUS_AGGREGATED
        assert result.report is not None
        assert result.report.resolved is False
    assert run.raw_resolved_rate == EXPECTED_NOOP_RESOLVED_RATE
