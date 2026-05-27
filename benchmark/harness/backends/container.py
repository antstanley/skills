"""The ``container`` RunBackend: run an arm in a provisioned run container.

This is the containerised mirror of :mod:`benchmark.harness.backends.local`
(``docs/benchmark/specs/05-harness-architecture.md`` §Run container;
``02-arms.md`` §A0 — Baseline). Where the ``local`` backend runs the scripted
fixture solver in a temp directory, this backend runs a REAL agent arm in a
fresh Docker container, and implements exactly the path ``local`` refuses (the
``agent`` solver / the A0 arm).

For each :meth:`run`:

1. Provision a fresh container from the AGENT RUN image (the greenfield run
   image — base skeleton, jj+git, NO hidden tests — PLUS Node + the
   ``@anthropic-ai/claude-code`` CLI; see
   :func:`benchmark.suites.greenfield_images.build_agent_run_image`), with the
   host ``~/.claude/.credentials.json`` bind-mounted WRITABLE at
   ``/root/.claude`` (a temp COPY, so token refresh persists for the run but the
   host creds are never touched), network enabled, workdir ``/workspace``.
2. Make the base commit: ``git init && git add -A && git commit -m base`` inside
   ``/workspace`` — this commit IS ``baseCommit`` for the diff.
3. Fail-fast auth probe: a trivial ``claude -p`` with a $1 cap; on failure,
   surface the auth error WITHOUT spending the full budget.
4. Run the arm to completion non-interactively: A0 is a PLAIN agent —
   ``claude -p "<problemStatement + directive>" --model sonnet
   --permission-mode bypassPermissions --max-budget-usd <CAP>
   --output-format json``. No ``--plugin-dir``, no ``spec-*`` plugins.
5. Extract the ``candidatePatch`` = ``git add -A && git diff --cached`` (unified
   diff against the base commit) and capture the ``claude`` JSON as the
   transcript, populating a real :class:`~benchmark.harness.domain.Telemetry`
   (input/output tokens + cost + turns from the JSON, wall-clock measured).
6. Discard the container.

INTEGRITY RULE — the RUN side NEVER sees the hidden tests. The run container is
provisioned from the agent run image, which derives from the clean run image and
carries the run-visible ``base/`` tree ONLY (no ``hidden/``); the
``candidatePatch`` and ``ArtifactBundle`` carry no hidden test content. The run
container is a DISTINCT environment from the scoring container.

Arm/solver selection
--------------------
``arm_or_solver`` selects the path BY ARM SLUG (configuration, not code
branches):

- the ``agent`` solver-mode slug (``DEFAULT_SOLVER``) or the A0 ``Arm`` record →
  the PLAIN A0 agent path (no plugins, single ``claude -p``);
- the A4 ``Arm`` record (``A4_SLUG``) → the NAIVE N-WAY PARALLEL path
  (``_run_a4``): N plain agents (no plugins) run concurrently on the same problem
  with a coordination-free framing, their per-agent diffs combined by a NAIVE
  merge that RECORDS (not resolves) conflicts. A4 is matched dispatch-FIRST over
  the A0 path because A4, like A0, is a no-plugin/gates-off/no-spec ``Arm``.
- a WORKFLOW arm — A1, A2, or A3 (``_WORKFLOW_ARM_SLUGS``) → ONE parameterized
  ``spec-*`` workflow path (``_run_workflow_arm``) that reads the arm's
  ``_WorkflowArmConfig``: which ``spec-*`` plugins to read-only mount and load
  with ``--plugin-dir``, whether to HAND IN a frozen given-spec (A2/A3 skip
  ``spec-creator``), whether ``spec-builder``'s two gates run (A3 disables
  them), and the orchestrating prompt. The candidate patch EXCLUDES the workflow
  artifacts (``docs/``); the spec/plan/certificate files are captured into the
  ``ArtifactBundle``, and the captured certificates are parsed into
  ``GateEvent``s (A1/A2 discharge them; A3 leaves none). Routing by SLUG — not
  by "any Arm with plugins" — is what keeps A2/A3 (plugin arms too) out of the
  plain-A0 branch.

The ``fixture`` solver is the ``local`` backend's job; it is out of scope here
and raises :class:`NotImplementedError`.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from benchmark.harness.arms.a0 import (
    A0,
    A0_MAX_BUDGET_USD,
    A0_MODEL,
    AUTH_PROBE_MAX_BUDGET_USD,
    a0_prompt,
)
from benchmark.harness.arms.a1 import (
    A1_ARTIFACT_DIR,
    A1_CERTIFICATE_DIR_NAME,
    A1_CONTAINER_PLUGIN_ROOT,
    A1_MAX_BUDGET_USD,
    A1_MODEL,
    A1_PLAN_SUBDIR,
    A1_PLUGIN_DIR_NAMES,
    A1_SLUG,
    A1_SPEC_SUBDIR,
    HOST_PLUGIN_MARKETPLACE_DIR,
    a1_prompt,
)
from benchmark.harness.arms.a2_a3 import (
    A2_A3_MAX_BUDGET_USD,
    A2_A3_MODEL,
    A2_A3_PLUGIN_DIR_NAMES,
    A2_SLUG,
    A3_SLUG,
    GIVEN_SPEC_CONTAINER_RELPATH,
    a2_prompt,
    a3_prompt,
    extract_gate_events,
)
from benchmark.harness.arms.a4 import (
    A4_MODEL,
    A4_N,
    A4_PER_AGENT_MAX_BUDGET_USD,
    A4_SLUG,
    a4_slice_prompt,
)
from benchmark.harness.backends.interfaces import CandidatePatch
from benchmark.harness.domain import (
    ARTIFACT_BUNDLE_ID_PREFIX,
    DEFAULT_SOLVER,
    Arm,
    ArtifactBundle,
    GateEvent,
    TaskInstance,
    Telemetry,
    new_record_id,
)
from benchmark.harness.telemetry import telemetry_from_agent_result
from benchmark.suites.greenfield import load_given_spec
from benchmark.suites.greenfield_images import (
    AGENT_HOME,
    IMAGE_WORKDIR,
    agent_run_image_tag,
    build_agent_run_image,
    docker_available,
    get_spec,
)

# --- named constants -------------------------------------------------------

#: The ``agent`` solver-mode slug (mirrors ``DEFAULT_SOLVER``): selects the real
#: agent path this backend implements (A0).
AGENT_SOLVER = DEFAULT_SOLVER

#: Host path to the OAuth credentials the in-container ``claude`` CLI uses. A
#: temp COPY is bind-mounted (never this file directly) so token refresh inside
#: the run cannot mutate the host creds.
HOST_CREDENTIALS_PATH = Path.home() / ".claude" / ".credentials.json"

#: Mount point for the (copied) ``.claude`` dir inside the container. The agent
#: runs as the unprivileged ``AGENT_USER`` (``claude --permission-mode
#: bypassPermissions`` refuses to run as root), so the creds live at that user's
#: ``~/.claude`` and ``claude`` reads ``<AGENT_HOME>/.claude/.credentials.json``.
CONTAINER_CLAUDE_DIR = f"{AGENT_HOME}/.claude"

#: Wall-clock ceiling (seconds) for the full A0 agent invocation inside the
#: container. Named so a hung agent cannot stall the harness; generous for a
#: multi-component build but bounded.
AGENT_RUN_TIMEOUT_SECONDS = 1200

#: Wall-clock ceiling (seconds) for the cheap auth probe.
AUTH_PROBE_TIMEOUT_SECONDS = 120

#: Wall-clock ceiling (seconds) for the short container-setup ``docker exec``
#: commands (git init/commit, diff extraction, container start/stop).
SETUP_TIMEOUT_SECONDS = 120

#: Git identity used ONLY to make the base commit inside the container (the diff
#: anchor). Not a real author; purely the ``baseCommit`` for ``git diff``.
_GIT_USER_NAME = "benchmark"
_GIT_USER_EMAIL = "benchmark@localhost"

#: The auth-probe prompt: a trivial round-trip that proves the token works.
_AUTH_PROBE_PROMPT = "reply with OK"

#: Patterns written to a ``.gitignore`` committed into the base commit so
#: Python bytecode caches the agent generates at runtime (``__pycache__/*.pyc``)
#: never enter the candidate patch — they are generated artifacts, not the
#: agent's source change, and as binaries they would also break ``git apply``.
#: The ``.gitignore`` is part of the base commit, so it does not show in the diff.
_BASE_GITIGNORE_PATTERNS = ("__pycache__/", "*.pyc")

#: ``claude`` exit code meaning the headless run completed.
_CLAUDE_EXIT_OK = 0

#: Wall-clock ceiling (seconds) for the full A1 workflow invocation inside the
#: container. A1 is a RECURSIVE workflow (the orchestrator spawns spec-builder
#: sub-agents that walk the plan DAG), so this is a HARD bound (~20 min) against a
#: hung/runaway run — paired with the ``--max-budget-usd`` cap. An honest cap: if
#: the workflow cannot finish within it, the run reports that with partial
#: evidence rather than spinning forever.
A1_RUN_TIMEOUT_SECONDS = 1200

#: Wall-clock ceiling (seconds) for the cheap A1 FEASIBILITY PROBE — confirm the
#: plugins load and a spec file starts being produced, before the full run.
A1_FEASIBILITY_PROBE_TIMEOUT_SECONDS = 360

#: Git tag placed on the base commit so the A1 candidate patch can be diffed
#: against it regardless of which branch/worktree spec-builder leaves checked out
#: (it accumulates merged tasks on its own ``spec-builder/integration`` branch).
_BASE_COMMIT_TAG = "benchmark-base"

#: Branch spec-builder accumulates completed, gated tasks onto on the GIT backend
#: (its tip IS the integration point — see the spec-builder ``workspaces.md``
#: reference). The A1 extractor prefers this ref as the integration tip to diff.
_SPEC_BUILDER_INTEGRATION_BRANCH = "spec-builder/integration"

#: ``git pathspec`` magic that EXCLUDES the workflow-artifact subtree from the
#: candidate-patch diff, so the spec/plan/certificate files written under
#: ``docs/`` never enter the scored CODE diff (they are captured into the bundle
#: instead). Built from :data:`A1_ARTIFACT_DIR` so the exclusion and the capture
#: agree on one directory name.
_ARTIFACT_EXCLUDE_PATHSPEC = f":(exclude){A1_ARTIFACT_DIR}/"

#: Sentinel printed by the artifact-listing command between the file path and its
#: contents, and between files, so a single ``docs/`` walk yields path+content
#: pairs without a second ``docs exec`` per file. Chosen to not occur in markdown.
_ARTIFACT_FIELD_SEP = "\x1f"  # ASCII unit separator
_ARTIFACT_RECORD_SEP = "\x1e"  # ASCII record separator


#: The closed set of arm slugs that select a ``spec-*`` WORKFLOW path (A1, A2,
#: A3) — as opposed to the plain A0 agent path. Dispatch routes by slug so A2/A3
#: never fall into the plain-A0 branch even though they, like A0, are ``Arm``
#: records (A2/A3 differ from A1 only in config, not in being plugin arms).
_WORKFLOW_ARM_SLUGS: frozenset[str] = frozenset({A1_SLUG, A2_SLUG, A3_SLUG})

#: Wall-clock ceiling (seconds) for each of A4's N parallel agent runs. Reuses
#: the plain-agent bound (A4 agents are plain ``claude -p`` like A0, just N of
#: them concurrently). The N agents run in parallel, so the arm's wall clock is
#: ~one agent's, not N times it.
A4_AGENT_RUN_TIMEOUT_SECONDS = AGENT_RUN_TIMEOUT_SECONDS

#: The naive merge applies each agent's diff against the SAME base commit in
#: agent-index order with a PLAIN ``git apply`` (atomic — see
#: :meth:`ContainerRunBackend._try_apply_agent_diff` for why NOT ``--3way``). An
#: agent diff that does NOT apply cleanly on top of what is already merged is a
#: CONFLICT: it is RECORDED (which agent, the apply stderr) and SKIPPED — A4 has
#: no structure to resolve it well, and surfacing the conflict is the point. The
#: first agent whose diff applies seeds the merged tree; later conflicting agents
#: are dropped, not force-merged. This header keys the merge-conflict record in
#: the transcript so a reviewer can see the naive-merge outcome without re-running.
_A4_MERGE_CONFLICT_NOTE = "A4 naive-merge conflict record"


@dataclass(frozen=True)
class _A4AgentResult:
    """One A4 parallel agent's outcome: its result JSON and its per-agent diff.

    ``patch`` is the empty string when the agent produced no diff (or failed —
    in which case ``result_json`` carries an ``error`` marker). ``agent_index``
    is 0-based, the agent's slot in the N-way split (used to order the naive merge
    and to label conflicts).
    """

    agent_index: int
    result_json: dict[str, object]
    patch: str


@dataclass(frozen=True)
class _WorkflowArmConfig:
    """The per-arm knobs the parameterized workflow runner reads.

    A1/A2/A3 share ONE code path (:meth:`ContainerRunBackend._run_workflow_arm`);
    they differ only in these fields. A1: creator on, gates on, no given spec.
    A2: creator off (spec handed in), gates on. A3: creator off, gates off.
    """

    #: Plugin directories to mount + load for this arm (read-only ``--plugin-dir``).
    plugin_dir_names: tuple[str, ...]
    #: Build the orchestrating prompt for this arm from the problem statement.
    prompt_builder: Callable[[str], str]
    #: HARD per-run budget cap (USD) handed to ``claude --max-budget-usd``.
    max_budget_usd: float
    #: The model alias the orchestrator + sub-agents run on.
    model: str
    #: When set, the frozen given-spec is written into the container at
    #: :data:`GIVEN_SPEC_CONTAINER_RELPATH` BEFORE the workflow runs (A2/A3 hand
    #: in a spec instead of authoring one). ``None`` for A1 (the workflow authors
    #: its own spec).
    provides_given_spec: bool
    #: Whether spec-builder's two gates run (A1/A2: True; A3: False). Drives the
    #: prompt (the gate instruction) and the gate-event extraction expectation.
    gates_enabled: bool


def _workflow_config_for(arm: Arm) -> _WorkflowArmConfig:
    """Return the :class:`_WorkflowArmConfig` for a workflow arm (A1/A2/A3)."""
    if arm.slug == A1_SLUG:
        return _WorkflowArmConfig(
            plugin_dir_names=A1_PLUGIN_DIR_NAMES,
            prompt_builder=a1_prompt,
            max_budget_usd=A1_MAX_BUDGET_USD,
            model=A1_MODEL,
            provides_given_spec=False,
            gates_enabled=True,
        )
    if arm.slug == A2_SLUG:
        return _WorkflowArmConfig(
            plugin_dir_names=A2_A3_PLUGIN_DIR_NAMES,
            prompt_builder=a2_prompt,
            max_budget_usd=A2_A3_MAX_BUDGET_USD,
            model=A2_A3_MODEL,
            provides_given_spec=True,
            gates_enabled=True,
        )
    if arm.slug == A3_SLUG:
        return _WorkflowArmConfig(
            plugin_dir_names=A2_A3_PLUGIN_DIR_NAMES,
            prompt_builder=a3_prompt,
            max_budget_usd=A2_A3_MAX_BUDGET_USD,
            model=A2_A3_MODEL,
            provides_given_spec=True,
            gates_enabled=False,
        )
    raise ContainerRunError(
        f"no workflow config for arm {arm.slug!r}; "
        f"workflow arms are {sorted(_WORKFLOW_ARM_SLUGS)}"
    )


class ContainerRunError(RuntimeError):
    """Raised when the container run environment cannot be prepared/driven."""


class ContainerAuthError(ContainerRunError):
    """Raised when the in-container ``claude`` CLI cannot authenticate."""


class ContainerRunBackend:
    """``RunBackend`` that runs a real agent arm in a fresh Docker container.

    Implements the ``RunBackend`` protocol (see
    ``benchmark/harness/backends/interfaces.py``) with Docker. Each :meth:`run`
    provisions the agent run image (building it on demand when missing), starts a
    fresh container with the host creds bind-mounted writable, makes the base
    commit, runs a fail-fast auth probe, runs the plain A0 agent to completion,
    and extracts the ``candidatePatch`` + a populated ``ArtifactBundle``, then
    discards the container.

    Only the ``agent`` solver / the A0 arm are supported here; the ``fixture``
    solver belongs to the ``local`` backend and raises ``NotImplementedError``.
    """

    def __init__(
        self, trial_id: str | None = None, *, build_if_missing: bool = True
    ) -> None:
        #: The trial these bundles belong to; a fresh id if unset.
        self._trial_id = trial_id or new_record_id("trial")
        #: When ``True`` (default), build the agent run image on demand if it is
        #: not already present; when ``False``, require it pre-built.
        self._build_if_missing = build_if_missing
        #: GateEvents extracted from the last workflow run's certificates (A1/A2
        #: discharge them; A3 does not). Read via :attr:`last_gate_events`.
        self._last_gate_events: list[GateEvent] = []
        #: Naive-merge conflict records from the LAST A4 run (one per agent whose
        #: diff did not apply cleanly onto the merged tree). Read via
        #: :attr:`last_merge_conflicts`. Empty for non-A4 paths or a clean merge.
        self._last_merge_conflicts: list[dict[str, object]] = []

    def run(
        self, instance: TaskInstance, arm_or_solver: object
    ) -> tuple[ArtifactBundle, CandidatePatch]:
        """Run ``arm_or_solver`` against ``instance``; return ``(bundle, patch)``.

        Dispatches BY ARM SLUG (configuration, not code branches per
        ``02-arms.md`` §Implementation layout):

        - the ``agent`` solver / the A0 ``Arm`` -> the plain A0 agent path
          (``_run_a0``: no plugins, single ``claude -p``);
        - a WORKFLOW arm (A1, A2, or A3 — :data:`_WORKFLOW_ARM_SLUGS`) -> the
          parameterized ``spec-*`` workflow path (``_run_workflow_arm``), which
          reads the arm's :class:`_WorkflowArmConfig` (which plugins to mount,
          whether to hand in a spec, whether the gates run, which prompt).

        Routing by slug — NOT by "any Arm with plugins" — is what keeps A2/A3
        (which are plugin arms) from falling into the plain-A0 branch. Every path
        provisions a fresh container, makes the base commit, probes auth, runs to
        completion, and returns the ``candidatePatch`` (diff vs the base commit)
        with a populated ``ArtifactBundle``. Carries NO hidden test content.
        """
        if self._selects_workflow(arm_or_solver):
            assert isinstance(arm_or_solver, Arm)  # narrowed by _selects_workflow
            return self._run_workflow_arm(instance, _workflow_config_for(arm_or_solver))
        if self._selects_a4(arm_or_solver):
            return self._run_a4(instance)
        if self._selects_agent(arm_or_solver):
            return self._run_a0(instance)
        raise NotImplementedError(
            "ContainerRunBackend runs the agent solver "
            f"({AGENT_SOLVER!r}), the A0 arm, a workflow arm "
            f"({sorted(_WORKFLOW_ARM_SLUGS)}), or the A4 arm ({A4_SLUG}); got "
            f"{arm_or_solver!r}. The fixture solver is the local backend's job."
        )

    def _run_a0(self, instance: TaskInstance) -> tuple[ArtifactBundle, CandidatePatch]:
        """Run the plain A0 agent path (no plugins) and capture the result."""
        self._require_docker_and_creds()
        image = self._resolve_image(instance)
        prompt = a0_prompt(instance.problemStatement)

        creds_dir = Path(tempfile.mkdtemp(prefix="benchmark-creds-"))
        container_id: str | None = None
        started = time.monotonic()
        try:
            self._stage_credentials(creds_dir)
            container_id = self._start_container(image, creds_dir)
            self._make_base_commit(container_id)
            self._auth_probe(container_id)
            result_json = self._run_agent(container_id, prompt)
            candidate_patch = self._extract_patch(container_id)
        finally:
            if container_id is not None:
                self._remove_container(container_id)
            shutil.rmtree(creds_dir, ignore_errors=True)

        wall_clock_seconds = time.monotonic() - started
        telemetry = telemetry_from_agent_result(result_json, wall_clock_seconds)
        bundle = ArtifactBundle(
            id=new_record_id(ARTIFACT_BUNDLE_ID_PREFIX),
            trial=self._trial_id,
            telemetry=telemetry,
            transcript=json.dumps(result_json, sort_keys=True),
        )
        return bundle, candidate_patch

    def _run_a4(self, instance: TaskInstance) -> tuple[ArtifactBundle, CandidatePatch]:
        """Run the A4 naive N-way parallel path and NAIVE-merge the N outputs.

        Provisions :data:`A4_N` INDEPENDENT plain-agent containers (NO plugins,
        like A0), one per parallel agent, each with its OWN writable creds copy and
        its OWN base commit, and runs them CONCURRENTLY (a thread per agent — real
        parallelism). Every agent gets the IDENTICAL problem statement plus the
        fixed coordination-free framing (the pinned naive split) under the matched
        per-agent budget (:data:`A4_PER_AGENT_MAX_BUDGET_USD` == A1 cap / N), so the
        N-way parallelism SPEND is budget-matched to A1's single run.

        Each agent's per-agent diff is extracted, then the N diffs are combined by
        the NAIVE merge (:meth:`_naive_merge_patches`): apply each in agent-index
        order against a fresh base; an agent diff that does not apply cleanly is
        RECORDED as a conflict and SKIPPED (A4 has no structure to resolve it). The
        merged diff is the single ``candidatePatch``. Telemetry is AGGREGATED across
        the N agents (tokens/cost/turns SUMMED; wall clock = the parallel arm's wall
        clock, i.e. the slowest agent ≈ max, NOT the sum — the agents ran at once).
        The conflict record rides in the bundle transcript and on
        :attr:`last_merge_conflicts`.
        """
        self._require_docker_and_creds()
        image = self._resolve_image(instance)

        started = time.monotonic()
        agent_results = self._run_agents_in_parallel(instance, image)
        wall_clock_seconds = time.monotonic() - started

        per_agent_diffs = [r.patch for r in agent_results]
        merged_patch, conflicts = self._naive_merge_patches(image, per_agent_diffs)
        self._last_merge_conflicts = conflicts

        result_jsons = [r.result_json for r in agent_results]
        telemetry = _aggregate_a4_telemetry(result_jsons, wall_clock_seconds)
        transcript = json.dumps(
            {
                "arm": A4_SLUG,
                "agentCount": A4_N,
                "perAgentResults": result_jsons,
                _A4_MERGE_CONFLICT_NOTE: conflicts,
            },
            sort_keys=True,
        )
        bundle = ArtifactBundle(
            id=new_record_id(ARTIFACT_BUNDLE_ID_PREFIX),
            trial=self._trial_id,
            telemetry=telemetry,
            transcript=transcript,
        )
        return bundle, merged_patch

    def _run_agents_in_parallel(
        self, instance: TaskInstance, image: str
    ) -> list[_A4AgentResult]:
        """Run A4's :data:`A4_N` plain agents CONCURRENTLY; return per-agent results.

        Each agent runs in its OWN fresh container with its OWN creds copy and base
        commit, on its OWN slice prompt under the matched per-agent budget. A thread
        per agent gives real parallelism. Returns a list (one :class:`_A4AgentResult`
        per agent, in AGENT-INDEX order). An agent that fails its own run records an
        empty patch + an error marker rather than aborting the whole arm (a
        structure-less arm tolerates partial agents) — the record makes that honest.
        """
        prompt = instance.problemStatement
        results: list[_A4AgentResult | None] = [None] * A4_N

        def run_one(idx: int) -> None:
            results[idx] = self._run_single_a4_agent(image, prompt, idx)

        with ThreadPoolExecutor(max_workers=A4_N) as pool:
            futures = [pool.submit(run_one, i) for i in range(A4_N)]
            for future in futures:
                future.result()
        # All slots filled by run_one (it never returns None into the slot).
        return [r for r in results if r is not None]

    def _run_single_a4_agent(
        self, image: str, problem_statement: str, agent_index: int
    ) -> _A4AgentResult:
        """Provision ONE A4 agent container, run it, and extract its diff.

        Agent ``agent_index`` is 0-based here; the prompt is built 1-based for
        human-facing "agent i of N" framing. On any per-agent failure the result
        carries an empty patch and an ``error`` marker so the arm continues with
        the agents that did finish (honest partial parallelism).
        """
        creds_dir = Path(tempfile.mkdtemp(prefix="benchmark-creds-a4-"))
        container_id: str | None = None
        try:
            self._stage_credentials(creds_dir)
            container_id = self._start_container(image, creds_dir)
            self._make_base_commit(container_id)
            self._auth_probe(container_id)
            prompt = a4_slice_prompt(
                problem_statement, agent_index=agent_index + 1, agent_count=A4_N
            )
            result_json = self._run_a4_agent(container_id, prompt)
            patch = self._extract_patch(container_id) or ""
            return _A4AgentResult(
                agent_index=agent_index, result_json=result_json, patch=patch
            )
        except ContainerRunError as exc:
            return _A4AgentResult(
                agent_index=agent_index,
                result_json={"error": str(exc)},
                patch="",
            )
        finally:
            if container_id is not None:
                self._remove_container(container_id)
            shutil.rmtree(creds_dir, ignore_errors=True)

    def _run_a4_agent(self, container_id: str, prompt: str) -> dict[str, object]:
        """Run ONE plain A4 agent to completion under the per-agent budget.

        Identical to the A0 plain agent (NO ``--plugin-dir``, NO ``spec-*``) except
        the budget is the matched per-agent slice :data:`A4_PER_AGENT_MAX_BUDGET_USD`
        and the timeout is :data:`A4_AGENT_RUN_TIMEOUT_SECONDS`.
        """
        command = (
            f"cd {IMAGE_WORKDIR}; "
            f"claude -p {_shell_quote(prompt)} "
            f"--model {A4_MODEL} --permission-mode bypassPermissions "
            f"--max-budget-usd {A4_PER_AGENT_MAX_BUDGET_USD} --output-format json"
        )
        result = subprocess.run(
            ["docker", "exec", container_id, "sh", "-c", command],
            capture_output=True,
            text=True,
            timeout=A4_AGENT_RUN_TIMEOUT_SECONDS,
        )
        if result.returncode != _CLAUDE_EXIT_OK:
            raise ContainerRunError(
                f"A4 agent run failed (exit {result.returncode}).\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
        try:
            parsed = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise ContainerRunError(
                f"could not parse claude --output-format json result:\n{result.stdout}"
            ) from exc
        if not isinstance(parsed, dict):
            raise ContainerRunError(f"claude result JSON was not an object: {parsed!r}")
        return parsed

    def _naive_merge_patches(
        self, image: str, per_agent_diffs: list[str]
    ) -> tuple[CandidatePatch, list[dict[str, object]]]:
        """NAIVELY merge the N per-agent diffs into one patch; RECORD conflicts.

        Spins up a fresh throwaway container from ``image`` with a base commit, then
        applies each non-empty agent diff in AGENT-INDEX order with a PLAIN ``git
        apply``. A diff that applies cleanly is folded into the merged tree (and
        committed so the next apply sees it). A diff that does NOT apply is a
        CONFLICT: it is RECORDED (agent index, the apply stderr) and SKIPPED — A4
        has no structure to resolve overlapping edits, so it does NOT force-merge or
        cleverly reconcile; the first-applied agent wins the overlap and later
        conflicting agents are dropped. The merged ``candidatePatch`` is the final
        diff of the accumulated tree against the base. Returns ``(patch, conflicts)``;
        ``conflicts`` is empty on a clean merge (no overlap). An all-empty input
        yields a no-op patch (``None``) and no conflicts.
        """
        if not any(d and d.strip() for d in per_agent_diffs):
            return None, []

        creds_dir = Path(tempfile.mkdtemp(prefix="benchmark-creds-a4merge-"))
        container_id: str | None = None
        try:
            self._stage_credentials(creds_dir)
            container_id = self._start_container(image, creds_dir)
            self._make_base_commit(container_id)
            cid = container_id  # narrowed for the closures
            return _run_naive_merge(
                per_agent_diffs,
                apply_diff=lambda diff: self._try_apply_agent_diff(cid, diff),
                commit_step=lambda idx: self._commit_merged_step(cid, idx),
                extract_merged=lambda: self._extract_merged_patch(cid),
            )
        finally:
            if container_id is not None:
                self._remove_container(container_id)
            shutil.rmtree(creds_dir, ignore_errors=True)

    def _try_apply_agent_diff(
        self, container_id: str, diff: str
    ) -> subprocess.CompletedProcess[str]:
        """PLAIN ``git apply`` one agent diff in the merge container (no raise).

        Returns the completed process so the caller decides clean vs conflict.
        Uses a PLAIN ``git apply`` (NOT ``--3way``) ON PURPOSE: a plain apply is
        ATOMIC — on an overlap it fails (non-zero exit) and makes NO change to the
        worktree, so the conflicting agent is cleanly skipped. ``--3way`` would
        instead write ``<<<<<<<``/``>>>>>>>`` CONFLICT MARKERS into the files and
        still exit non-zero, polluting the merged patch with un-applyable markers —
        exactly the bug the first live A4 run surfaced. A clean apply ``--index``
        stages the change so the running merge accumulates; ``--whitespace=nowarn``
        keeps benign whitespace from being treated as a failure.
        """
        command = f"cd {IMAGE_WORKDIR}; git apply --index --whitespace=nowarn -"
        return subprocess.run(
            ["docker", "exec", "-i", container_id, "sh", "-c", command],
            input=diff,
            capture_output=True,
            text=True,
            timeout=SETUP_TIMEOUT_SECONDS,
        )

    def _commit_merged_step(self, container_id: str, agent_index: int) -> None:
        """Stage + commit the cleanly-applied agent diff so the next apply sees it."""
        command = (
            f"set -e; cd {IMAGE_WORKDIR}; git add -A; "
            f"git -c user.email={_GIT_USER_EMAIL} -c user.name={_GIT_USER_NAME} "
            f"commit -q -m _a4_merge_agent_{agent_index} --allow-empty"
        )
        self._exec(container_id, command, SETUP_TIMEOUT_SECONDS, "commit A4 merge step")

    def _extract_merged_patch(self, container_id: str) -> CandidatePatch:
        """The merged A4 candidate patch = diff of the BASE commit tag against HEAD.

        Each cleanly-applied agent diff is COMMITTED by :meth:`_commit_merged_step`,
        so HEAD has moved past the base; the merged patch is therefore the diff
        ``benchmark-base..HEAD`` (NOT the staged index vs HEAD, which is empty after
        the commits). Returns ``None`` for an empty diff (no agent applied).
        """
        command = f"cd {IMAGE_WORKDIR}; git diff {_BASE_COMMIT_TAG} HEAD"
        result = subprocess.run(
            ["docker", "exec", container_id, "sh", "-c", command],
            capture_output=True,
            text=True,
            timeout=SETUP_TIMEOUT_SECONDS,
        )
        if result.returncode != 0:
            raise ContainerRunError(
                f"failed to extract merged A4 patch:\n{result.stderr}"
            )
        diff = result.stdout
        return diff if diff.strip() else None

    @property
    def last_merge_conflicts(self) -> list[dict[str, object]]:
        """Naive-merge conflict records from the LAST A4 run (empty otherwise).

        One entry per agent whose diff did not apply cleanly onto the merged tree,
        ``{"agentIndex", "stderr"}``. Populated by :meth:`_run_a4`; empty for the
        A0/workflow paths, before any A4 run, or on a clean (no-overlap) merge.
        """
        return list(self._last_merge_conflicts)

    def _run_workflow_arm(
        self, instance: TaskInstance, config: _WorkflowArmConfig
    ) -> tuple[ArtifactBundle, CandidatePatch]:
        """Run ANY ``spec-*`` workflow arm (A1/A2/A3) on one parameterized path.

        Provisions a plugin container, optionally hands in the frozen given-spec
        (A2/A3), drives the workflow with the arm's orchestrating prompt to an
        integration tip, extracts the CODE-only candidate patch (workflow
        artifacts EXCLUDED), and captures the spec/plan/certificate artifacts.
        A1 keeps its exact previous behaviour: ``config`` for A1 is creator-on,
        gates-on, NO given spec — the same plugins, prompt, cap, model, and
        artifact handling as before this refactor.

        The captured done-certificates are parsed into :class:`GateEvent`
        records (REAL structural extraction): a gates-on arm (A1/A2) discharges
        its certificates and yields ``>= 1`` event; a gates-off arm (A3) leaves
        them blank and yields none. The events hang off the Trial in the domain
        model; this backend stashes them on :attr:`last_gate_events` for the
        driver/test to read (``run`` returns ``(bundle, patch)`` per the
        ``RunBackend`` protocol, so the events ride alongside the backend).
        """
        self._require_docker_and_creds()
        self._require_plugins(config.plugin_dir_names)
        image = self._resolve_image(instance)
        prompt = config.prompt_builder(instance.problemStatement)
        given_spec = (
            load_given_spec(instance.slug) if config.provides_given_spec else None
        )

        creds_dir = Path(tempfile.mkdtemp(prefix="benchmark-creds-"))
        container_id: str | None = None
        started = time.monotonic()
        try:
            self._stage_credentials(creds_dir)
            container_id = self._start_container(
                image, creds_dir, plugin_dir_names=config.plugin_dir_names
            )
            self._make_base_commit(container_id)
            if given_spec is not None:
                self._write_given_spec(container_id, given_spec)
            self._auth_probe(container_id)
            result_json = self._run_workflow(container_id, prompt, config)
            candidate_patch = self._extract_patch(container_id, exclude_artifacts=True)
            spec_files, plan_files, cert_files = self._capture_artifacts(container_id)
        finally:
            if container_id is not None:
                self._remove_container(container_id)
            shutil.rmtree(creds_dir, ignore_errors=True)

        wall_clock_seconds = time.monotonic() - started
        telemetry = telemetry_from_agent_result(result_json, wall_clock_seconds)
        bundle = ArtifactBundle(
            id=new_record_id(ARTIFACT_BUNDLE_ID_PREFIX),
            trial=self._trial_id,
            telemetry=telemetry,
            specArtifacts=spec_files,
            planArtifacts=plan_files,
            certificateArtifacts=cert_files,
            transcript=json.dumps(result_json, sort_keys=True),
        )
        # REAL GateEvent extraction from the captured certificates (see a2_a3).
        # A gates-on arm (A1/A2) yields >= 1 event; a gates-off arm (A3) none.
        self._last_gate_events = extract_gate_events(
            cert_files, trial_id=self._trial_id
        )
        return bundle, candidate_patch

    @property
    def last_gate_events(self) -> list[GateEvent]:
        """The :class:`GateEvent`s extracted from the LAST workflow run, if any.

        Populated by :meth:`_run_workflow_arm` from the captured certificates.
        Empty for the A0 path or before any workflow run. A gates-on arm
        (A1/A2) leaves ``>= 1`` here; a gates-off arm (A3) leaves none.
        """
        return list(self._last_gate_events)

    # --- internals ---------------------------------------------------------

    @staticmethod
    def _require_docker_and_creds() -> None:
        """Fail fast if Docker is unreachable or the host creds are absent."""
        if not docker_available():
            raise ContainerRunError(
                "Docker daemon not reachable (docker info failed); the "
                "container RunBackend requires Docker"
            )
        if not HOST_CREDENTIALS_PATH.is_file():
            raise ContainerAuthError(
                f"host credentials {HOST_CREDENTIALS_PATH} not found; the "
                "in-container claude CLI cannot authenticate without them"
            )

    @staticmethod
    def _require_plugins(
        plugin_dir_names: tuple[str, ...] = A1_PLUGIN_DIR_NAMES,
    ) -> None:
        """Fail fast if any required host ``spec-*`` plugin source is absent.

        ``plugin_dir_names`` is the arm's mount set (A1 mounts spec-creator too;
        A2/A3 do not). Defaults to A1's set for backward compatibility.
        """
        for name in plugin_dir_names:
            manifest = (
                HOST_PLUGIN_MARKETPLACE_DIR / name / ".claude-plugin" / "plugin.json"
            )
            if not manifest.is_file():
                raise ContainerRunError(
                    f"spec-* plugin {name!r} not found at "
                    f"{HOST_PLUGIN_MARKETPLACE_DIR / name}; the workflow arm needs "
                    "the spec-* plugins available on the host to mount into the "
                    "container"
                )

    @staticmethod
    def _selects_agent(arm_or_solver: object) -> bool:
        """Whether ``arm_or_solver`` selects the agent / A0 path."""
        return arm_or_solver == AGENT_SOLVER or arm_or_solver == A0

    @staticmethod
    def _selects_workflow(arm_or_solver: object) -> bool:
        """Whether ``arm_or_solver`` selects a ``spec-*`` WORKFLOW path (A1/A2/A3).

        Routes BY SLUG against the closed :data:`_WORKFLOW_ARM_SLUGS`, NOT by
        "any Arm with plugins" — A2/A3 are plugin arms too, so the old
        plugins-non-empty test would WRONGLY treat them like A1 (and an A0-style
        record would never reach here regardless). Keeping dispatch
        configuration-driven per ``02-arms.md`` §Implementation layout: arms are
        records the driver reads, not code branches.
        """
        return (
            isinstance(arm_or_solver, Arm) and arm_or_solver.slug in _WORKFLOW_ARM_SLUGS
        )

    @staticmethod
    def _selects_a4(arm_or_solver: object) -> bool:
        """Whether ``arm_or_solver`` selects the A4 naive-parallel path.

        Routes BY SLUG against :data:`A4_SLUG`. A4 is, like A0, a no-plugin /
        gates-off / no-spec ``Arm`` record, so it would otherwise match
        :meth:`_selects_agent` (which accepts the A0 record) — dispatching by the
        A4 slug FIRST is what keeps A4 on its own N-way parallel path instead of
        the single-agent A0 path.
        """
        return isinstance(arm_or_solver, Arm) and arm_or_solver.slug == A4_SLUG

    def _resolve_image(self, instance: TaskInstance) -> str:
        """Return the AGENT RUN image tag for ``instance``, building if needed."""
        spec = get_spec(instance.slug)
        tag = agent_run_image_tag(spec.slug)
        if self._build_if_missing and not self._image_exists(tag):
            build_agent_run_image(spec)
        return tag

    @staticmethod
    def _image_exists(tag: str) -> bool:
        """Whether a local Docker image named ``tag`` is already present."""
        result = subprocess.run(
            ["docker", "image", "inspect", tag],
            capture_output=True,
            text=True,
            timeout=SETUP_TIMEOUT_SECONDS,
        )
        return result.returncode == 0

    @staticmethod
    def _stage_credentials(creds_dir: Path) -> None:
        """Copy the host creds into ``creds_dir`` so the mount is writable.

        The container gets a COPY of ``~/.claude/.credentials.json`` mounted
        writable, so in-run token refresh persists for the container's lifetime
        but the host file is never mutated. The dir is made group/other-writable
        so the unprivileged in-container ``AGENT_USER`` (a different uid than the
        host) can persist refreshed tokens and config into the mount.
        """
        shutil.copy2(HOST_CREDENTIALS_PATH, creds_dir / ".credentials.json")
        creds_dir.chmod(0o777)
        (creds_dir / ".credentials.json").chmod(0o666)

    def _start_container(
        self,
        image: str,
        creds_dir: Path,
        *,
        plugin_dir_names: tuple[str, ...] | None = None,
    ) -> str:
        """Start a detached container; return its id.

        Bind-mounts the writable creds copy at :data:`CONTAINER_CLAUDE_DIR`,
        keeps network (default bridge has outbound), workdir ``/workspace``, and
        keeps the container alive with ``sleep`` so we can ``docker exec`` into
        it for setup, the agent run, and patch extraction. When
        ``plugin_dir_names`` is given (any workflow arm — A1/A2/A3), it ALSO
        read-only bind-mounts each named host ``spec-*`` plugin source under
        :data:`A1_CONTAINER_PLUGIN_ROOT` so the in-container ``claude -p
        --plugin-dir ...`` resolves the workflow skills.
        """
        alive = AGENT_RUN_TIMEOUT_SECONDS + AUTH_PROBE_TIMEOUT_SECONDS + 300
        command = [
            "docker",
            "run",
            "-d",
            "--workdir",
            IMAGE_WORKDIR,
            "-v",
            f"{creds_dir}:{CONTAINER_CLAUDE_DIR}",
        ]
        if plugin_dir_names:
            alive = A1_RUN_TIMEOUT_SECONDS + AUTH_PROBE_TIMEOUT_SECONDS + 300
            for name in plugin_dir_names:
                host_dir = HOST_PLUGIN_MARKETPLACE_DIR / name
                command += [
                    "-v",
                    f"{host_dir}:{A1_CONTAINER_PLUGIN_ROOT}/{name}:ro",
                ]
        command += [image, "sleep", str(alive)]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=SETUP_TIMEOUT_SECONDS,
        )
        if result.returncode != 0:
            raise ContainerRunError(
                f"failed to start run container from {image}:\n{result.stderr}"
            )
        return result.stdout.strip()

    def _make_base_commit(self, container_id: str) -> None:
        """``git init && add -A && commit`` in ``/workspace`` — the baseCommit.

        First writes a ``.gitignore`` (Python bytecode caches) so the runtime
        ``.pyc`` artifacts the agent generates never enter the candidate patch.
        """
        gitignore = "\\n".join(_BASE_GITIGNORE_PATTERNS)
        command = (
            f"set -e; cd {IMAGE_WORKDIR}; "
            f"printf '%b\\n' {_shell_quote(gitignore)} > .gitignore; "
            f"git init -q; "
            f"git add -A; "
            f"git -c user.email={_GIT_USER_EMAIL} -c user.name={_GIT_USER_NAME} "
            f"commit -q -m base; "
            # Tag the base commit so the A1 patch can be diffed against it even
            # after spec-builder switches the working tree onto its own
            # `spec-builder/integration` branch (the integration tip lives in
            # commits on a branch, not necessarily the working-tree state).
            f"git tag {_BASE_COMMIT_TAG}"
        )
        self._exec(container_id, command, SETUP_TIMEOUT_SECONDS, "make base commit")

    def _write_given_spec(self, container_id: str, given_spec: str) -> None:
        """Write the frozen given-spec into the container BEFORE the workflow runs.

        A2/A3 hand in a ready-made spec instead of authoring one. The spec is
        written at :data:`GIVEN_SPEC_CONTAINER_RELPATH` (under ``docs/specs/``,
        where ``spec-creator`` would have written), so it is captured into the
        bundle's ``specArtifacts`` and EXCLUDED from the scored code diff exactly
        like an authored spec, and so dropping ``spec-creator`` is transparent to
        ``spec-planner``. Committed onto the base so the spec file does not show
        up in the candidate patch (it is an input, not the arm's code change).
        """
        rel = GIVEN_SPEC_CONTAINER_RELPATH
        parent = rel.rsplit("/", 1)[0]
        # Write the spec via a heredoc on stdin (no shell-escaping of the body),
        # then fold it into the base commit so it is an INPUT, not a diff change.
        command = (
            f"set -e; cd {IMAGE_WORKDIR}; "
            f"mkdir -p {_shell_quote(parent)}; "
            f"cat > {_shell_quote(rel)} <<'BENCHMARK_GIVEN_SPEC_EOF'\n"
            f"{given_spec}\n"
            f"BENCHMARK_GIVEN_SPEC_EOF\n"
            f"git add -A; "
            f"git -c user.email={_GIT_USER_EMAIL} -c user.name={_GIT_USER_NAME} "
            f"commit -q -m given_spec --allow-empty; "
            # Re-point the base tag so the diff anchor INCLUDES the given spec —
            # the handed-in spec is part of the starting point, not the change.
            f"git tag -f {_BASE_COMMIT_TAG}"
        )
        self._exec(container_id, command, SETUP_TIMEOUT_SECONDS, "write given spec")

    def _auth_probe(self, container_id: str) -> None:
        """Trivial ``claude -p`` with a $1 cap; raise clearly if auth fails."""
        command = (
            f"cd {IMAGE_WORKDIR}; "
            f"claude -p {_shell_quote(_AUTH_PROBE_PROMPT)} "
            f"--model {A0_MODEL} --permission-mode bypassPermissions "
            f"--max-budget-usd {AUTH_PROBE_MAX_BUDGET_USD} --output-format json"
        )
        result = subprocess.run(
            ["docker", "exec", container_id, "sh", "-c", command],
            capture_output=True,
            text=True,
            timeout=AUTH_PROBE_TIMEOUT_SECONDS,
        )
        if result.returncode != _CLAUDE_EXIT_OK:
            raise ContainerAuthError(
                "in-container claude auth probe failed "
                f"(exit {result.returncode}); the OAuth token may be invalid or "
                f"expired, or the container has no network.\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )

    def _run_agent(self, container_id: str, prompt: str) -> dict[str, object]:
        """Run the plain A0 agent to completion; return the parsed result JSON.

        A0 is PLAIN: no ``--plugin-dir``, no ``spec-*`` plugins. The JSON result
        carries usage/cost/turns and the result text.
        """
        command = (
            f"cd {IMAGE_WORKDIR}; "
            f"claude -p {_shell_quote(prompt)} "
            f"--model {A0_MODEL} --permission-mode bypassPermissions "
            f"--max-budget-usd {A0_MAX_BUDGET_USD} --output-format json"
        )
        result = subprocess.run(
            ["docker", "exec", container_id, "sh", "-c", command],
            capture_output=True,
            text=True,
            timeout=AGENT_RUN_TIMEOUT_SECONDS,
        )
        if result.returncode != _CLAUDE_EXIT_OK:
            raise ContainerRunError(
                f"A0 agent run failed (exit {result.returncode}).\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
        try:
            parsed = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise ContainerRunError(
                f"could not parse claude --output-format json result:\n{result.stdout}"
            ) from exc
        if not isinstance(parsed, dict):
            raise ContainerRunError(f"claude result JSON was not an object: {parsed!r}")
        return parsed

    def _run_workflow(
        self, container_id: str, prompt: str, config: _WorkflowArmConfig
    ) -> dict[str, object]:
        """Drive a ``spec-*`` workflow arm (A1/A2/A3) to completion; return the JSON.

        Loads the arm's ``spec-*`` plugins for the session with a ``--plugin-dir``
        per mounted plugin, runs on the arm's model behind its HARD
        ``--max-budget-usd`` cap, and is bounded by :data:`A1_RUN_TIMEOUT_SECONDS`
        (shared — A2/A3 are no longer-running than A1). A non-zero exit OR a
        timeout is an HONEST outcome the caller surfaces with partial evidence —
        the recursive workflow may legitimately hit the cap before finishing.
        """
        plugin_flags = " ".join(
            f"--plugin-dir {A1_CONTAINER_PLUGIN_ROOT}/{name}"
            for name in config.plugin_dir_names
        )
        command = (
            f"cd {IMAGE_WORKDIR}; "
            f"claude -p {_shell_quote(prompt)} "
            f"{plugin_flags} "
            f"--model {config.model} --permission-mode bypassPermissions "
            f"--max-budget-usd {config.max_budget_usd} --output-format json"
        )
        result = subprocess.run(
            ["docker", "exec", container_id, "sh", "-c", command],
            capture_output=True,
            text=True,
            timeout=A1_RUN_TIMEOUT_SECONDS,
        )
        if result.returncode != _CLAUDE_EXIT_OK:
            raise ContainerRunError(
                f"workflow run failed (exit {result.returncode}).\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
        try:
            parsed = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise ContainerRunError(
                f"could not parse claude --output-format json result:\n{result.stdout}"
            ) from exc
        if not isinstance(parsed, dict):
            raise ContainerRunError(f"claude result JSON was not an object: {parsed!r}")
        return parsed

    def _extract_patch(
        self, container_id: str, *, exclude_artifacts: bool = False
    ) -> CandidatePatch:
        """Return the candidate patch (unified diff against the base commit).

        A0 path: ``git add -A && git diff --cached`` — the working-tree change vs
        the base commit. An empty diff -> a no-op patch (``None``).

        A1 path (``exclude_artifacts``): the integration tip is the merged result
        spec-builder accumulates on its ``spec-builder/integration`` branch (its
        tip IS the integration point), NOT necessarily the working tree. So the A1
        patch is the diff of THAT TIP against the base commit tag, staging any
        uncommitted working-tree changes first so a working-tree-only result is
        still captured. Either way the diff EXCLUDES the workflow-artifact subtree
        (``docs/``) via a git exclude pathspec, so the spec/plan/certificate files
        never enter the scored CODE diff — they are captured into the bundle.
        """
        pathspec = (
            f" -- . {_shell_quote(_ARTIFACT_EXCLUDE_PATHSPEC)}"
            if exclude_artifacts
            else ""
        )
        if exclude_artifacts:
            tip = self._resolve_integration_tip(container_id)
            # Stage any uncommitted work, snapshot it as a transient commit on the
            # current tip, then diff the base commit tag against that snapshot — so
            # both spec-builder's MERGED commits and any unmerged working-tree edits
            # are captured. The snapshot commit is throwaway (the container is
            # discarded right after).
            command = (
                f"set -e; cd {IMAGE_WORKDIR}; "
                f"git add -A; "
                f"git -c user.email={_GIT_USER_EMAIL} -c user.name={_GIT_USER_NAME} "
                f"commit -q -m _a1_snapshot --allow-empty >/dev/null 2>&1 || true; "
                f"git diff {_BASE_COMMIT_TAG} {tip}{pathspec}"
            )
        else:
            command = (
                f"set -e; cd {IMAGE_WORKDIR}; git add -A; git diff --cached{pathspec}"
            )
        result = subprocess.run(
            ["docker", "exec", container_id, "sh", "-c", command],
            capture_output=True,
            text=True,
            timeout=SETUP_TIMEOUT_SECONDS,
        )
        if result.returncode != 0:
            raise ContainerRunError(
                f"failed to extract candidate patch:\n{result.stderr}"
            )
        diff = result.stdout
        return diff if diff.strip() else None

    def _resolve_integration_tip(self, container_id: str) -> str:
        """Resolve the A1 integration tip ref to diff against the base.

        Prefers spec-builder's ``spec-builder/integration`` branch (its tip IS the
        integration point on the git backend). If that branch is absent (an
        early-exit run that never reached the first merge), falls back to the
        most-recently-committed ``spec-builder/*`` branch — typically a built task
        branch whose work has not yet merged — so a PARTIAL run still yields the
        code it produced. Failing all of those, falls back to ``HEAD``.
        """
        command = (
            f"cd {IMAGE_WORKDIR}; "
            f"if git rev-parse --verify -q {_SPEC_BUILDER_INTEGRATION_BRANCH} "
            f">/dev/null; then printf '%s' {_SPEC_BUILDER_INTEGRATION_BRANCH}; "
            f"else "
            # Newest spec-builder/* branch by commit date, if any; else HEAD.
            f"b=$(git for-each-ref --sort=-committerdate --count=1 "
            f"--format='%(refname:short)' 'refs/heads/spec-builder/*'); "
            f'if [ -n "$b" ]; then printf \'%s\' "$b"; else printf HEAD; fi; '
            f"fi"
        )
        result = subprocess.run(
            ["docker", "exec", container_id, "sh", "-c", command],
            capture_output=True,
            text=True,
            timeout=SETUP_TIMEOUT_SECONDS,
        )
        tip = result.stdout.strip()
        return tip or "HEAD"

    def _capture_artifacts(
        self, container_id: str
    ) -> tuple[list[str], list[str], list[str]]:
        """Read the workflow artifacts under ``docs/`` into spec/plan/cert lists.

        Walks the ``docs/`` subtree ONCE, emitting ``<path><FS><contents>``
        records separated by a record separator, then classifies each file by its
        path: ``docs/specs/...`` -> spec, ``docs/plans/.../certificates/...`` ->
        certificate, other ``docs/plans/...`` -> plan. Each captured entry is a
        ``"<relpath>\\n<contents>"`` string so a reviewer can inspect both the
        path and the content from the bundle without re-running A1. Returns
        ``(specArtifacts, planArtifacts, certificateArtifacts)``; empty lists when
        the workflow produced none (an honest partial outcome).
        """
        artifact_dir = f"{IMAGE_WORKDIR}/{A1_ARTIFACT_DIR}"
        # find every file under docs/, print "<relpath><FS><contents><RS>".
        command = (
            f"cd {IMAGE_WORKDIR}; "
            f"if [ -d {A1_ARTIFACT_DIR} ]; then "
            f"find {A1_ARTIFACT_DIR} -type f | sort | while IFS= read -r f; do "
            f"printf '%s{_ARTIFACT_FIELD_SEP}' \"$f\"; "
            f'cat "$f"; '
            f"printf '{_ARTIFACT_RECORD_SEP}'; "
            f"done; fi"
        )
        result = subprocess.run(
            ["docker", "exec", container_id, "sh", "-c", command],
            capture_output=True,
            text=True,
            timeout=SETUP_TIMEOUT_SECONDS,
        )
        if result.returncode != 0:
            raise ContainerRunError(
                f"failed to capture A1 artifacts from {artifact_dir}:\n{result.stderr}"
            )
        return self._classify_artifacts(result.stdout)

    @staticmethod
    def _classify_artifacts(
        raw: str,
    ) -> tuple[list[str], list[str], list[str]]:
        """Sort ``find``-walk records into (spec, plan, certificate) buckets."""
        specs: list[str] = []
        plans: list[str] = []
        certs: list[str] = []
        spec_prefix = f"{A1_ARTIFACT_DIR}/{A1_SPEC_SUBDIR}/"
        plan_prefix = f"{A1_ARTIFACT_DIR}/{A1_PLAN_SUBDIR}/"
        cert_marker = f"/{A1_CERTIFICATE_DIR_NAME}/"
        for record in raw.split(_ARTIFACT_RECORD_SEP):
            if _ARTIFACT_FIELD_SEP not in record:
                continue
            relpath, _, contents = record.partition(_ARTIFACT_FIELD_SEP)
            relpath = relpath.strip()
            if not relpath:
                continue
            entry = f"{relpath}\n{contents}"
            if relpath.startswith(plan_prefix) and cert_marker in relpath:
                certs.append(entry)
            elif relpath.startswith(plan_prefix):
                plans.append(entry)
            elif relpath.startswith(spec_prefix):
                specs.append(entry)
            else:
                # Other docs/ files (e.g. docs/README.md) count as plan-adjacent
                # workflow output; keep them with the plan bucket so nothing the
                # workflow wrote under docs/ is silently dropped from the bundle.
                plans.append(entry)
        return specs, plans, certs

    @staticmethod
    def _exec(
        container_id: str, command: str, timeout: int, what: str
    ) -> subprocess.CompletedProcess[str]:
        """Run ``sh -c command`` in the container; raise on failure."""
        result = subprocess.run(
            ["docker", "exec", container_id, "sh", "-c", command],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            raise ContainerRunError(
                f"failed to {what} in run container:\n{result.stderr}"
            )
        return result

    @staticmethod
    def _remove_container(container_id: str) -> None:
        """Force-remove the run container (discard the run environment)."""
        subprocess.run(
            ["docker", "rm", "-f", container_id],
            capture_output=True,
            text=True,
            timeout=SETUP_TIMEOUT_SECONDS,
        )


def _run_naive_merge(
    per_agent_diffs: Sequence[str],
    *,
    apply_diff: Callable[[str], subprocess.CompletedProcess[str]],
    commit_step: Callable[[int], None],
    extract_merged: Callable[[], CandidatePatch],
) -> tuple[CandidatePatch, list[dict[str, object]]]:
    """The PURE naive-merge loop (substrate injected so it is testable off-Docker).

    Applies each non-empty agent diff in AGENT-INDEX order via ``apply_diff``. A
    clean apply (returncode 0) is committed via ``commit_step`` so the next diff
    sees it; a non-clean apply is RECORDED as a conflict (``{"agentIndex",
    "stderr"}``) and SKIPPED — A4 does NOT resolve overlapping edits, the
    first-applied agent wins and later conflicting agents are dropped. The merged
    patch (``extract_merged``) is returned only if at least one diff applied; an
    all-empty input yields ``(None, [])``. The same loop drives the live container
    merge and the off-Docker unit test (which injects a real local-git applier).
    """
    conflicts: list[dict[str, object]] = []
    nonempty = [(i, d) for i, d in enumerate(per_agent_diffs) if d and d.strip()]
    if not nonempty:
        return None, conflicts
    applied_any = False
    for agent_index, diff in nonempty:
        applied = apply_diff(diff)
        if applied.returncode == 0:
            applied_any = True
            commit_step(agent_index)
        else:
            conflicts.append(
                {"agentIndex": agent_index, "stderr": applied.stderr.strip()}
            )
    merged = extract_merged() if applied_any else None
    return merged, conflicts


def _aggregate_a4_telemetry(
    result_jsons: Sequence[Mapping[str, object]], wall_clock_seconds: float
) -> Telemetry:
    """AGGREGATE the N A4 agents' result JSONs into ONE :class:`Telemetry`.

    Tokens, cost, and turns are SUMMED across the N agents (the arm's total spend
    is what is budget-matched to A1). The wall clock is the PARALLEL arm's measured
    wall clock — the agents ran CONCURRENTLY, so the arm took roughly the slowest
    agent's time, not the sum; ``wall_clock_seconds`` is that measured parallel
    elapsed (passed in by :meth:`ContainerRunBackend._run_a4`). This is the
    documented choice: SUM the resource counters, take the PARALLEL wall clock.
    Each per-agent JSON is mapped through the arm-agnostic
    :func:`telemetry_from_agent_result` first (per-agent wall clock is irrelevant
    to the summed counters and is set to 0 before the arm-level clock is applied).
    """
    input_tokens = 0
    output_tokens = 0
    cost_usd = 0.0
    agent_turns = 0
    for result_json in result_jsons:
        per_agent = telemetry_from_agent_result(result_json, 0.0)
        input_tokens += per_agent.inputTokens
        output_tokens += per_agent.outputTokens
        cost_usd += per_agent.costUsd
        agent_turns += per_agent.agentTurns
    return Telemetry(
        inputTokens=input_tokens,
        outputTokens=output_tokens,
        costUsd=cost_usd,
        wallClockSeconds=max(0.0, float(wall_clock_seconds)),
        agentTurns=agent_turns,
    )


def _shell_quote(text: str) -> str:
    """Single-quote ``text`` for safe embedding in a ``sh -c`` command."""
    return "'" + text.replace("'", "'\\''") + "'"
