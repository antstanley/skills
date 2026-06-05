"""Intra-trial workflow timing — captured-cert parsing + parallel-speedup math.

Covers Task 02 — capture intra-trial workflow timing
(``.specs/plans/2026-05-28-close_group_a_spec_code_gaps/02-capture_intra_trial_workflow_timing.md``):

* :func:`extract_task_wall_clocks` reads ``Elapsed: <seconds>s`` lines from the
  captured ``"<relpath>\\n<contents>"`` certificate entries and returns
  ``{certificate stem: seconds}``.
* :class:`ArtifactBundle` round-trips with and without the new optional
  ``taskWallClocks`` field (the schema delta — the field is optional and the
  schema's ``additionalProperties: false`` would reject a misspelt name).
* :func:`parallel_speedup_for_arm` computes the spec-defined per-trial
  ``sum(taskWallClocks) / wallClockSeconds`` and averages across the arm when
  the series is present; it falls back to the legacy intra-campaign
  ``sum / max`` estimate (with a logged warning) when no scored bundle carries
  the series, so existing saved evidence still scores.
* Negative-space: a single-task plan yields ``speedup == 1.0`` (not a divide-
  by-zero or a nonsensical >1).
"""

from __future__ import annotations

import logging
import math

import pytest

from benchmark.harness.arms.a2_a3 import extract_task_wall_clocks
from benchmark.harness.domain import (
    ARTIFACT_BUNDLE_ID_PREFIX,
    SCORE_REPORT_ID_PREFIX,
    TRIAL_ID_PREFIX,
    ArtifactBundle,
    DomainValidationError,
    ScoreReport,
    Telemetry,
    Trial,
    new_record_id,
)
from benchmark.harness.driver import STATUS_AGGREGATED, TrialResult
from benchmark.harness.stats import parallel_speedup_for_arm

_TOL = 1e-9


# --- shared builders --------------------------------------------------------


def _trial(arm: str = "A1", instance: str = "inst-1") -> Trial:
    return Trial(
        id=new_record_id(TRIAL_ID_PREFIX),
        campaign=new_record_id("camp"),
        arm=arm,
        taskInstance=instance,
        seed=0,
        createdAt="2026-05-28T00:00:00Z",
        status=STATUS_AGGREGATED,
    )


def _telemetry(*, wall: float) -> Telemetry:
    return Telemetry(
        inputTokens=10,
        outputTokens=20,
        costUsd=0.5,
        wallClockSeconds=wall,
        agentTurns=3,
    )


def _bundle_with_timing(
    *,
    trial_id: str,
    wall: float,
    task_wall_clocks: dict[str, float] | None,
) -> ArtifactBundle:
    """Build an ArtifactBundle with the optional ``taskWallClocks`` set or unset.

    Passing ``None`` for ``task_wall_clocks`` omits the field — the schema's
    additionalProperties: false still validates, exercising the "no per-task
    timing" fallback path.
    """
    if task_wall_clocks is None:
        return ArtifactBundle(
            id=new_record_id(ARTIFACT_BUNDLE_ID_PREFIX),
            trial=trial_id,
            telemetry=_telemetry(wall=wall),
        )
    return ArtifactBundle(
        id=new_record_id(ARTIFACT_BUNDLE_ID_PREFIX),
        trial=trial_id,
        telemetry=_telemetry(wall=wall),
        taskWallClocks=task_wall_clocks,
    )


def _scored(
    *,
    arm: str = "A1",
    instance: str = "inst-1",
    wall: float = 200.0,
    task_wall_clocks: dict[str, float] | None = None,
) -> TrialResult:
    trial = _trial(arm, instance)
    bundle = _bundle_with_timing(
        trial_id=trial.id, wall=wall, task_wall_clocks=task_wall_clocks
    )
    report = ScoreReport(
        id=new_record_id(SCORE_REPORT_ID_PREFIX),
        trial=trial.id,
        resolved=True,
        regressed=False,
    )
    return TrialResult(trial=trial, bundle=bundle, report=report, gate_events=())


def _capture_entry(relpath: str, body: str) -> str:
    """Mirror the ``"<relpath>\\n<contents>"`` shape ``_classify_artifacts`` emits."""
    return f"{relpath}\n{body}"


# --- extract_task_wall_clocks parser ---------------------------------------


def test_extract_task_wall_clocks_reads_elapsed_lines() -> None:
    """Each certificate's ``Elapsed: <seconds>s`` line surfaces as one entry."""
    entries = [
        _capture_entry(
            ".specs/plans/2026-05-28-feature/certificates/01-tokenizer.md",
            "# Done Certificate — 01\n\nState: Validated …\n"
            "Elapsed: 90.0s\n\nVERDICT: DONE\n",
        ),
        _capture_entry(
            ".specs/plans/2026-05-28-feature/certificates/02-normalizer.md",
            "# Done Certificate — 02\n\nElapsed: 110s\n\nVERDICT: DONE\n",
        ),
        _capture_entry(
            ".specs/plans/2026-05-28-feature/certificates/03-frequency.md",
            "# 03\nElapsed: 50.5 seconds\nVERDICT: DONE\n",
        ),
    ]
    timings = extract_task_wall_clocks(entries)
    assert timings == {
        "01-tokenizer": pytest.approx(90.0, abs=_TOL),
        "02-normalizer": pytest.approx(110.0, abs=_TOL),
        "03-frequency": pytest.approx(50.5, abs=_TOL),
    }


def test_extract_task_wall_clocks_skips_certs_without_elapsed() -> None:
    """A certificate without an Elapsed line silently contributes no entry."""
    entries = [
        _capture_entry(
            ".specs/plans/p/certificates/01-a.md",
            "# 01\n\nVERDICT: DONE\n",  # no Elapsed: line
        ),
        _capture_entry(
            ".specs/plans/p/certificates/02-b.md",
            "# 02\n\nElapsed: 42s\n",
        ),
    ]
    timings = extract_task_wall_clocks(entries)
    assert timings == {"02-b": pytest.approx(42.0, abs=_TOL)}


def test_extract_task_wall_clocks_empty_input_is_empty() -> None:
    assert extract_task_wall_clocks([]) == {}


def test_extract_task_wall_clocks_ignores_empty_relpath() -> None:
    # A capture record with an empty relpath (defensive) is silently dropped.
    entries = [_capture_entry("", "Elapsed: 1s\n")]
    assert extract_task_wall_clocks(entries) == {}


# --- ArtifactBundle schema round-trip with the new optional field ----------


def test_artifact_bundle_round_trip_with_task_wall_clocks() -> None:
    """A bundle carrying ``taskWallClocks`` dumps and loads back equal."""
    trial = _trial()
    bundle = ArtifactBundle(
        id=new_record_id(ARTIFACT_BUNDLE_ID_PREFIX),
        trial=trial.id,
        telemetry=_telemetry(wall=200.0),
        taskWallClocks={"01-a": 90.0, "02-b": 110.0},
    )
    dumped = bundle.to_dict()
    assert "taskWallClocks" in dumped
    assert dumped["taskWallClocks"] == {"01-a": 90.0, "02-b": 110.0}
    reloaded = ArtifactBundle.from_dict(dumped)
    assert reloaded == bundle


def test_artifact_bundle_round_trip_without_task_wall_clocks() -> None:
    """A bundle WITHOUT ``taskWallClocks`` still validates and round-trips."""
    trial = _trial()
    bundle = ArtifactBundle(
        id=new_record_id(ARTIFACT_BUNDLE_ID_PREFIX),
        trial=trial.id,
        telemetry=_telemetry(wall=200.0),
    )
    dumped = bundle.to_dict()
    # Optional, unset -> not present in the dump (schema-clean).
    assert "taskWallClocks" not in dumped
    reloaded = ArtifactBundle.from_dict(dumped)
    assert reloaded == bundle


def test_artifact_bundle_rejects_negative_task_wall_clock() -> None:
    """The schema's ``minimum: 0`` rejects a negative seconds value."""
    trial = _trial()
    with pytest.raises(DomainValidationError):
        ArtifactBundle(
            id=new_record_id(ARTIFACT_BUNDLE_ID_PREFIX),
            trial=trial.id,
            telemetry=_telemetry(wall=200.0),
            taskWallClocks={"01-a": -1.0},
        )


# --- parallel_speedup_for_arm — spec-defined ratio + fallback --------------


def test_parallel_speedup_spec_defined_ratio() -> None:
    """taskWallClocks {01:90, 02:110, 03:50, 04:50}, wall=200 -> speedup=1.5."""
    result = _scored(
        wall=200.0,
        task_wall_clocks={"01-a": 90.0, "02-b": 110.0, "03-c": 50.0, "04-d": 50.0},
    )
    sp = parallel_speedup_for_arm("A1", [result], graph_width=4)
    assert sp.used_per_task_timing is True
    assert sp.n_trials == 1
    assert math.isclose(sp.sequential_estimate_seconds, 300.0, abs_tol=_TOL)
    assert math.isclose(sp.observed_parallel_wall_seconds, 200.0, abs_tol=_TOL)
    assert math.isclose(sp.speedup, 1.5, abs_tol=_TOL)
    assert sp.graph_width == 4


def test_parallel_speedup_single_task_plan_is_unity() -> None:
    """A single-task plan: sum == that one task's wall, ratio == 1.0 by design."""
    result = _scored(wall=80.0, task_wall_clocks={"01-only": 80.0})
    sp = parallel_speedup_for_arm("A1", [result])
    assert sp.used_per_task_timing is True
    assert sp.n_trials == 1
    # A single task whose elapsed equals the orchestrator wall yields 1.0 — not
    # a divide-by-zero, not a nonsensical >1.
    assert math.isclose(sp.speedup, 1.0, abs_tol=_TOL)


def test_parallel_speedup_averages_per_trial_ratios() -> None:
    """The arm's speedup is the MEAN of per-trial ratios."""
    # Trial 1: sum 300, wall 200 -> ratio 1.5
    # Trial 2: sum 100, wall 100 -> ratio 1.0
    # Mean = 1.25
    r1 = _scored(
        instance="i1",
        wall=200.0,
        task_wall_clocks={"01": 150.0, "02": 150.0},
    )
    r2 = _scored(
        instance="i2",
        wall=100.0,
        task_wall_clocks={"01-a": 100.0},
    )
    sp = parallel_speedup_for_arm("A1", [r1, r2])
    assert sp.used_per_task_timing is True
    assert sp.n_trials == 2
    assert math.isclose(sp.speedup, 1.25, abs_tol=_TOL)
    # Sanity: sequential/parallel are SUMS of the per-trial sums and walls.
    assert math.isclose(sp.sequential_estimate_seconds, 400.0, abs_tol=_TOL)
    assert math.isclose(sp.observed_parallel_wall_seconds, 300.0, abs_tol=_TOL)


def test_parallel_speedup_falls_back_when_no_timing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Bundles without ``taskWallClocks`` fall back to sum/max + log a warning."""
    # Per-trial walls 100, 200, 300; legacy: sum 600 / max 300 = 2.0.
    results = [
        _scored(instance=f"i{i}", wall=w, task_wall_clocks=None)
        for i, w in enumerate([100.0, 200.0, 300.0])
    ]
    with caplog.at_level(
        logging.WARNING, logger="benchmark.harness.stats.cost_robustness"
    ):
        sp = parallel_speedup_for_arm("A1", results, graph_width=3)
    assert sp.used_per_task_timing is False
    assert sp.n_trials == 3
    assert math.isclose(sp.sequential_estimate_seconds, 600.0, abs_tol=_TOL)
    assert math.isclose(sp.observed_parallel_wall_seconds, 300.0, abs_tol=_TOL)
    assert math.isclose(sp.speedup, 2.0, abs_tol=_TOL)
    assert sp.graph_width == 3
    # The fallback was announced for the arm.
    assert any(
        "taskWallClocks" in rec.getMessage() and "A1" in rec.getMessage()
        for rec in caplog.records
    )


def test_parallel_speedup_mixed_timed_and_untimed_uses_timed_only() -> None:
    """Mixed arm: when ANY bundle carries timing, the timed path wins.

    The fallback warning is reserved for the all-untimed case — once a single
    bundle carries the series, the spec-defined ratio is computable from it.
    Untimed bundles are skipped (they cannot contribute a per-trial ratio).
    """
    timed = _scored(
        instance="i1",
        wall=200.0,
        task_wall_clocks={"01": 100.0, "02": 200.0},
    )
    untimed = _scored(instance="i2", wall=100.0, task_wall_clocks=None)
    sp = parallel_speedup_for_arm("A1", [timed, untimed])
    assert sp.used_per_task_timing is True
    # Only the timed trial contributes: 300 / 200 = 1.5.
    assert math.isclose(sp.speedup, 1.5, abs_tol=_TOL)


def test_parallel_speedup_no_trials_is_unity() -> None:
    """Zero trials: no parallelism observable -> speedup 1.0, baseline 0."""
    sp = parallel_speedup_for_arm("A1", [])
    assert sp.n_trials == 0
    assert sp.speedup == 1.0
    assert sp.used_per_task_timing is False


def test_parallel_speedup_zero_orchestrator_wall_falls_back_to_unity() -> None:
    """A timed bundle with wallClockSeconds == 0 contributes no ratio."""
    # One timed bundle; wall=0 -> no per-trial ratio computable; speedup 1.0.
    result = _scored(wall=0.0, task_wall_clocks={"01": 5.0})
    sp = parallel_speedup_for_arm("A1", [result])
    assert sp.used_per_task_timing is True
    assert sp.speedup == 1.0
