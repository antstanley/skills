"""The ``RunBackend`` and ``ScoringBackend`` interfaces.

These are the two contracts the driver and the concrete backends code against,
per ``changes/2026-05-27-local_backends.md`` (the ``05-harness-architecture.md``
Backends section, §Run container, and §Scoring isolation). The driver, the
scorer's resolution rule, and the statistics are agnostic to *how* a Trial is
run and scored; ``container`` and ``local`` are two implementations of the same
two protocols.

The integrity rule (``05-harness-architecture.md`` §Scoring isolation) is the
backbone these interfaces exist to enforce, and it is part of the contract:

- The **run** environment and the **scoring** environment are DISTINCT (separate
  containers, or separate temp directories / processes). Nothing from the
  scoring side is ever mounted into the run side.
- The hidden ``failToPass`` / ``passToPass`` suite lives ONLY on the scoring
  side. A ``RunBackend`` never sees it; the workflow's gates therefore cannot
  discharge themselves against the very tests they are later scored on.
- A candidate **resolves** iff every ``failToPass`` test passes AND every
  ``passToPass`` test still holds (the shared resolution rule, identical across
  backends — see ``ScoringBackend.score``).

A ``candidatePatch`` is a unified-diff string (the diff of the working state
against the instance ``baseCommit``); ``None`` denotes the no-op patch.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from benchmark.harness.domain import (
    ArtifactBundle,
    ScoreReport,
    TaskInstance,
)

# --- named contract constants ---------------------------------------------

#: A ``candidatePatch`` is a unified-diff string; ``None`` means a no-op patch.
CandidatePatch = str | None

#: The two ablation-input shapes a ``RunBackend`` may run against: a full
#: ``Arm`` record (a real arm A0-A4) or a solver-mode slug (e.g. ``"fixture"``
#: from ``Campaign.solver``). Kept as a name so the run signature reads clearly.
#: ``object`` because an ``Arm`` is a domain record and a solver mode is a slug.
ArmOrSolver = object

#: The hidden-test field names that live ONLY on the scoring side. A run
#: backend's output (the ``ArtifactBundle`` and the ``candidatePatch``) must
#: never carry their content; the conformance test asserts this.
HIDDEN_TEST_FIELDS: tuple[str, ...] = ("failToPass", "passToPass")


@runtime_checkable
class RunBackend(Protocol):
    """Provision an environment, run an arm/solver, return a patch + bundle.

    The driver calls :meth:`run` once per Trial. A ``RunBackend`` provisions an
    environment (a ``container`` from the instance ``dockerImage``, or a
    ``local`` temp working directory checked out at ``baseCommit``), installs the
    arm's plugins (or runs the fixture solver), runs to completion, and extracts
    the ``candidatePatch`` (the diff against ``baseCommit``) plus the
    ``ArtifactBundle`` (specs, plans, certificates, transcript, telemetry).

    INTEGRITY RULE — the RUN side NEVER sees the hidden tests. The instance's
    ``failToPass`` / ``passToPass`` selectors are the oracle; a ``RunBackend``
    must not place their test content into its run environment, the
    ``candidatePatch``, or the ``ArtifactBundle``. The run environment is a
    DISTINCT filesystem/process from the scoring environment. This is what keeps
    the workflow's gates from overfitting the oracle.
    """

    def run(
        self, instance: TaskInstance, arm_or_solver: ArmOrSolver
    ) -> tuple[ArtifactBundle, CandidatePatch]:
        """Run ``arm_or_solver`` against ``instance``; return ``(bundle, patch)``.

        Returns the captured ``ArtifactBundle`` and the ``candidatePatch`` (a
        unified diff against ``instance.baseCommit``, or ``None`` for a no-op).
        Carries NO hidden test content across to the caller.
        """
        ...


@runtime_checkable
class ScoringBackend(Protocol):
    """Apply a candidate patch in a clean environment and return a ScoreReport.

    The driver calls :meth:`score` after the run side is gone. A
    ``ScoringBackend`` applies the ``candidatePatch`` to a fresh clean copy of
    the instance base (a fresh scoring ``container``, or a fresh ``local`` temp
    checkout — DISTINCT from the run environment), injects the hidden tests,
    runs them, and returns a ``ScoreReport``.

    INTEGRITY RULE — the hidden ``failToPass`` / ``passToPass`` suite is injected
    ONLY here, on the scoring side. It never reaches a ``RunBackend``.

    RESOLUTION RULE (shared, backend-agnostic) — a candidate **resolves** iff
    every ``failToPass`` test passes AND every ``passToPass`` test still holds.
    ``ScoreReport.resolved`` is set by exactly this rule, identical across the
    ``container`` and ``local`` backends.
    """

    def score(
        self, instance: TaskInstance, candidate_patch: CandidatePatch
    ) -> ScoreReport:
        """Score ``candidate_patch`` against ``instance``; return a ScoreReport.

        Injects the hidden ``failToPass`` / ``passToPass`` suite (scoring side
        only), runs it against a clean checkout with the patch applied, and sets
        ``resolved`` iff all ``failToPass`` pass and all ``passToPass`` hold.
        """
        ...
