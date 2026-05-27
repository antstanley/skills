"""Conformance tests for the ``RunBackend`` / ``ScoringBackend`` interfaces.

An in-memory test-double implements BOTH protocols. The tests drive it through
the driver-facing calls (run -> get bundle + patch -> score -> get ScoreReport)
and assert the two contract invariants from ``05-harness-architecture.md``:

- the shared resolution rule — resolved iff all ``failToPass`` pass and all
  ``passToPass`` hold;
- the integrity rule — the run output (``ArtifactBundle`` + ``candidatePatch``)
  carries NO hidden test content.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from benchmark.harness import domain
from benchmark.harness.backends import (
    HIDDEN_TEST_FIELDS,
    CandidatePatch,
    RunBackend,
    ScoringBackend,
)
from benchmark.harness.domain import (
    ArtifactBundle,
    ScoreReport,
    TaskInstance,
    Telemetry,
    new_record_id,
)

_TRIAL_ID = new_record_id(domain.TRIAL_ID_PREFIX)

#: The patch the fixture solver emits to resolve the instance below.
_GOLD_PATCH = "--- a/mod.py\n+++ b/mod.py\n@@\n+def f():\n+    return 1\n"


def _instance() -> TaskInstance:
    return TaskInstance(
        slug="localfix__demo__0001",
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


@dataclass
class InMemoryBackend:
    """An in-memory double implementing BOTH ``RunBackend`` and ``ScoringBackend``.

    The run side is a scripted "fixture solver": it returns whatever patch it was
    seeded with and an ``ArtifactBundle`` built only from non-test inputs, so it
    structurally cannot leak the hidden suite. The scoring side holds the hidden
    tests (injected only here) and applies the shared resolution rule: a patch
    equal to the instance ``goldPatch`` makes every ``failToPass`` pass while the
    ``passToPass`` smoke tests keep holding.
    """

    patch_to_emit: CandidatePatch = _GOLD_PATCH
    #: Captures every selector the run side was exposed to, for the leak check.
    run_inputs_seen: list[str] = field(default_factory=list)

    def run(
        self, instance: TaskInstance, arm_or_solver: object
    ) -> tuple[ArtifactBundle, CandidatePatch]:
        # The run side reads only non-oracle fields of the instance. It never
        # touches failToPass / passToPass, so nothing about the hidden suite can
        # reach the bundle or the patch.
        self.run_inputs_seen.extend(
            [instance.slug, instance.problemStatement, str(arm_or_solver)]
        )
        bundle = ArtifactBundle(
            id=new_record_id(domain.ARTIFACT_BUNDLE_ID_PREFIX),
            trial=_TRIAL_ID,
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
        # Hidden tests are injected ONLY here. A correct patch passes every
        # failToPass; the smoke passToPass tests hold unless the patch is broken.
        resolves = candidate_patch == instance.goldPatch
        fail_to_pass = {sel: resolves for sel in instance.failToPass}
        pass_to_pass = {sel: candidate_patch is not None for sel in instance.passToPass}
        # Resolution rule: all failToPass pass AND all passToPass hold.
        resolved = all(fail_to_pass.values()) and all(pass_to_pass.values())
        regressed = bool(pass_to_pass) and not all(pass_to_pass.values())
        return ScoreReport(
            id=new_record_id(domain.SCORE_REPORT_ID_PREFIX),
            trial=_TRIAL_ID,
            resolved=resolved,
            regressed=regressed,
            failToPassResults=fail_to_pass,
            passToPassResults=pass_to_pass,
        )


def test_double_satisfies_both_protocols() -> None:
    backend = InMemoryBackend()
    assert isinstance(backend, RunBackend)
    assert isinstance(backend, ScoringBackend)


def test_round_trip_run_then_score_resolves() -> None:
    backend = InMemoryBackend(patch_to_emit=_GOLD_PATCH)
    instance = _instance()

    # Driver-facing calls: run -> (bundle, patch) -> score -> ScoreReport.
    bundle, patch = backend.run(instance, "fixture")
    report = backend.score(instance, patch)

    assert isinstance(bundle, ArtifactBundle)
    assert patch == _GOLD_PATCH
    assert isinstance(report, ScoreReport)
    assert report.resolved is True
    assert report.regressed is False
    assert all(report.failToPassResults.values())
    assert all(report.passToPassResults.values())


def test_noop_patch_does_not_resolve() -> None:
    backend = InMemoryBackend(patch_to_emit=None)
    instance = _instance()

    _bundle, patch = backend.run(instance, "fixture")
    report = backend.score(instance, patch)

    assert patch is None
    assert report.resolved is False
    # A failToPass test that never passes means unresolved by the shared rule.
    assert not all(report.failToPassResults.values())


def test_run_output_carries_no_hidden_tests() -> None:
    """The run side (bundle + patch) must not leak the hidden suite."""
    backend = InMemoryBackend()
    instance = _instance()

    bundle, patch = backend.run(instance, "fixture")

    # The concrete hidden selectors and the field names must appear nowhere in
    # the serialised run output.
    hidden_selectors = [*instance.failToPass, *instance.passToPass]
    run_blob = repr(bundle.to_dict()) + repr(patch)
    for selector in hidden_selectors:
        assert selector not in run_blob
    for hidden_field in HIDDEN_TEST_FIELDS:
        assert hidden_field not in run_blob

    # And the run side never read the oracle fields off the instance.
    for selector in hidden_selectors:
        assert selector not in backend.run_inputs_seen
