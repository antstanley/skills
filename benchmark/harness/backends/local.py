"""The ``local`` RunBackend: run an arm/solver in a temp working directory.

This is the Docker-free run path from
``changes/2026-05-27-local_backends.md`` (``05-harness-architecture.md``
§Backends and §Run container: the ``local`` ``RunBackend`` "does the same in an
isolated temp working directory checked out at ``baseCommit`` — no container —
for arms whose execution does not require one and for the fixture solver").
It implements the ``RunBackend`` protocol
(``benchmark/harness/backends/interfaces.py``) without Docker:

1. Make a temp working directory checked out at ``baseCommit`` from the
   instance's RUN-VISIBLE tree (``base/`` only — NEVER ``hidden/``), under a
   named-constant base directory DISTINCT from the scoring one
   (:data:`benchmark.harness.scoring.local.SCORING_TEMP_BASE`).
2. Produce the ``candidatePatch`` for the selected solver. The ``fixture``
   solver is scripted and deterministic: it emits the instance ``goldPatch``
   verbatim (the unified diff against ``baseCommit``), with no LLM/API call.
3. Build an ``ArtifactBundle`` with a minimal ``Telemetry`` record (real
   ``wallClockSeconds``; tokens/cost/turns zero for the fixture solver).
4. Clean the working directory up afterwards.

INTEGRITY RULE — the RUN side NEVER sees the hidden tests. The working
directory is checked out from ``base/`` ONLY; ``hidden/`` is never copied in,
and the run output (the ``candidatePatch`` and the ``ArtifactBundle``) carries
no hidden test content. The run working directory lives under
:data:`RUN_TEMP_BASE`, a base directory DISTINCT from the scoring backend's
:data:`benchmark.harness.scoring.local.SCORING_TEMP_BASE`, so the run and
scoring environments are different filesystems by construction.

Solver selection
----------------
``arm_or_solver`` is either a solver-mode slug (a string from
``Campaign.solver``, e.g. ``"fixture"``) or a full ``Arm`` record. Only the
``fixture`` solver is implemented here: it is the scripted, deterministic
pipeline-verification path. Any other solver (the ``agent`` solver, or a real
``Arm``) needs the LLM/plugin execution that is out of scope for this backend
and raises :class:`NotImplementedError`.
"""

from __future__ import annotations

import shutil
import tempfile
import time
from pathlib import Path

from benchmark.harness.backends.interfaces import CandidatePatch
from benchmark.harness.domain import (
    ARTIFACT_BUNDLE_ID_PREFIX,
    ArtifactBundle,
    TaskInstance,
    Telemetry,
    new_record_id,
)
from benchmark.harness.scoring.local import REPO_BASE_SUBDIR

# --- named constants -------------------------------------------------------

#: Base directory under which every run temp working directory is created.
#: Kept as a name so the integrity rule (run dir DISTINCT from the scoring dir)
#: is auditable: it is intentionally NOT
#: :data:`benchmark.harness.scoring.local.SCORING_TEMP_BASE`.
RUN_TEMP_BASE = Path(tempfile.gettempdir()) / "benchmark-run"

#: Prefix for each per-run temp working directory under :data:`RUN_TEMP_BASE`.
RUN_DIR_PREFIX = "run-"

#: The scripted solver mode slug (mirrors ``Campaign.solver == "fixture"``):
#: emits the instance ``goldPatch`` deterministically, no LLM/API.
FIXTURE_SOLVER = "fixture"

#: Telemetry for the fixture solver: it runs no model, so tokens/cost/turns are
#: zero; only the measured ``wallClockSeconds`` is non-trivial.
_FIXTURE_INPUT_TOKENS = 0
_FIXTURE_OUTPUT_TOKENS = 0
_FIXTURE_COST_USD = 0.0
_FIXTURE_AGENT_TURNS = 0


class LocalRunError(RuntimeError):
    """Raised when the local run environment cannot be prepared."""


class LocalRunBackend:
    """``RunBackend`` that runs in a temp working directory with no Docker.

    Implements the ``RunBackend`` protocol (see
    ``benchmark/harness/backends/interfaces.py``). Each :meth:`run` checks out
    the instance's run-visible ``base/`` tree at ``baseCommit`` into a fresh
    temp directory under :data:`RUN_TEMP_BASE` — DISTINCT from any scoring
    directory and free of hidden tests — produces the ``candidatePatch`` for the
    selected solver, and returns it with a populated ``ArtifactBundle``.

    Only the ``fixture`` solver is supported; it emits the instance
    ``goldPatch``. Any other solver raises :class:`NotImplementedError`.
    """

    def __init__(self, trial_id: str | None = None) -> None:
        #: The trial these bundles belong to; a fresh id if unset.
        self._trial_id = trial_id or new_record_id("trial")

    def run(
        self, instance: TaskInstance, arm_or_solver: object
    ) -> tuple[ArtifactBundle, CandidatePatch]:
        """Run ``arm_or_solver`` against ``instance``; return ``(bundle, patch)``.

        Checks out the run-visible ``base/`` tree (never ``hidden/``) into a
        fresh temp working directory under :data:`RUN_TEMP_BASE`, runs the
        selected solver, and returns the ``candidatePatch`` (the diff against
        ``baseCommit``) with a populated ``ArtifactBundle``. Carries NO hidden
        test content across to the caller.
        """
        if not self._is_fixture_solver(arm_or_solver):
            raise NotImplementedError(
                "LocalRunBackend only supports the fixture solver "
                f"({FIXTURE_SOLVER!r}); got {arm_or_solver!r}. The agent solver "
                "and real arms require LLM/plugin execution, out of scope here."
            )

        RUN_TEMP_BASE.mkdir(parents=True, exist_ok=True)
        workdir = Path(tempfile.mkdtemp(prefix=RUN_DIR_PREFIX, dir=RUN_TEMP_BASE))
        started = time.monotonic()
        try:
            self._checkout_base(instance, workdir)
            # The fixture solver is scripted: its candidate patch IS the
            # instance goldPatch (the unified diff against baseCommit). No model
            # is invoked, so the run is deterministic and offline.
            candidate_patch: CandidatePatch = instance.goldPatch
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

        wall_clock_seconds = time.monotonic() - started
        bundle = ArtifactBundle(
            id=new_record_id(ARTIFACT_BUNDLE_ID_PREFIX),
            trial=self._trial_id,
            telemetry=Telemetry(
                inputTokens=_FIXTURE_INPUT_TOKENS,
                outputTokens=_FIXTURE_OUTPUT_TOKENS,
                costUsd=_FIXTURE_COST_USD,
                wallClockSeconds=wall_clock_seconds,
                agentTurns=_FIXTURE_AGENT_TURNS,
            ),
            transcript=f"fixture solver emitted goldPatch for {instance.slug}",
        )
        return bundle, candidate_patch

    # --- internals ---------------------------------------------------------

    @staticmethod
    def _is_fixture_solver(arm_or_solver: object) -> bool:
        """Whether ``arm_or_solver`` selects the scripted fixture solver."""
        return arm_or_solver == FIXTURE_SOLVER

    @staticmethod
    def _checkout_base(instance: TaskInstance, workdir: Path) -> None:
        """Materialise the run-visible ``base/`` tree at ``baseCommit``.

        Copies ONLY the ``base/`` subtree of the instance repo source — the
        hidden suite (``hidden/``) is never touched, upholding the integrity
        rule on the run side.
        """
        source = Path(instance.repo)
        base = source / REPO_BASE_SUBDIR
        if not base.is_dir():
            raise LocalRunError(
                f"instance repo {source} has no {REPO_BASE_SUBDIR}/ tree "
                f"to check out at {instance.baseCommit}"
            )
        shutil.copytree(base, workdir, dirs_exist_ok=True)
