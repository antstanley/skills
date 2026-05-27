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
``arm_or_solver`` selects the path:

- the ``agent`` solver-mode slug (``DEFAULT_SOLVER``) or the A0 ``Arm`` record →
  the PLAIN A0 agent path (no plugins, single ``claude -p``);
- an ``Arm`` with a non-empty ``pluginsEnabled`` (e.g. A1) → the A1 FULL-PIPELINE
  path: the ``spec-*`` plugins are read-only mounted and loaded with
  ``--plugin-dir``, and one orchestrating ``claude -p`` drives
  ``spec-creator → spec-planner → spec-builder`` to an integration tip. The
  candidate patch EXCLUDES the workflow artifacts (``docs/``); the
  spec/plan/certificate files are captured into the ``ArtifactBundle`` instead.

The ``fixture`` solver is the ``local`` backend's job; it is out of scope here
and raises :class:`NotImplementedError`.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
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
    A1_SPEC_SUBDIR,
    HOST_PLUGIN_MARKETPLACE_DIR,
    a1_prompt,
)
from benchmark.harness.backends.interfaces import CandidatePatch
from benchmark.harness.domain import (
    ARTIFACT_BUNDLE_ID_PREFIX,
    DEFAULT_SOLVER,
    Arm,
    ArtifactBundle,
    TaskInstance,
    new_record_id,
)
from benchmark.harness.telemetry import telemetry_from_agent_result
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

    def run(
        self, instance: TaskInstance, arm_or_solver: object
    ) -> tuple[ArtifactBundle, CandidatePatch]:
        """Run ``arm_or_solver`` against ``instance``; return ``(bundle, patch)``.

        Dispatches by arm: the plain A0 agent path (``_selects_agent``) or the A1
        full-pipeline path (``_selects_a1`` — an ``Arm`` with a non-empty
        ``pluginsEnabled``). Both provision a fresh agent run container, make the
        base commit, probe auth, run to completion, and return the
        ``candidatePatch`` (diff against the base commit) with a populated
        ``ArtifactBundle``. Carries NO hidden test content across to the caller.
        """
        if self._selects_a1(arm_or_solver):
            return self._run_a1(instance)
        if self._selects_agent(arm_or_solver):
            return self._run_a0(instance)
        raise NotImplementedError(
            "ContainerRunBackend runs the agent solver "
            f"({AGENT_SOLVER!r}), the A0 arm, or an A1-style plugin arm; got "
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

    def _run_a1(self, instance: TaskInstance) -> tuple[ArtifactBundle, CandidatePatch]:
        """Run the A1 full-pipeline path: mount the ``spec-*`` plugins, drive
        ``spec-creator → spec-planner → spec-builder`` to an integration tip, and
        extract the CODE-only candidate patch (workflow artifacts EXCLUDED) plus a
        bundle carrying the captured spec/plan/certificate artifacts.
        """
        self._require_docker_and_creds()
        self._require_plugins()
        image = self._resolve_image(instance)
        prompt = a1_prompt(instance.problemStatement)

        creds_dir = Path(tempfile.mkdtemp(prefix="benchmark-creds-"))
        container_id: str | None = None
        started = time.monotonic()
        try:
            self._stage_credentials(creds_dir)
            container_id = self._start_container(image, creds_dir, with_plugins=True)
            self._make_base_commit(container_id)
            self._auth_probe(container_id)
            result_json = self._run_a1_workflow(container_id, prompt)
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
        return bundle, candidate_patch

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
    def _require_plugins() -> None:
        """Fail fast if the host ``spec-*`` plugin sources are not present."""
        for name in A1_PLUGIN_DIR_NAMES:
            manifest = (
                HOST_PLUGIN_MARKETPLACE_DIR / name / ".claude-plugin" / "plugin.json"
            )
            if not manifest.is_file():
                raise ContainerRunError(
                    f"spec-* plugin {name!r} not found at "
                    f"{HOST_PLUGIN_MARKETPLACE_DIR / name}; A1 needs the spec-* "
                    "plugins available on the host to mount into the container"
                )

    @staticmethod
    def _selects_agent(arm_or_solver: object) -> bool:
        """Whether ``arm_or_solver`` selects the agent / A0 path."""
        return arm_or_solver == AGENT_SOLVER or arm_or_solver == A0

    @staticmethod
    def _selects_a1(arm_or_solver: object) -> bool:
        """Whether ``arm_or_solver`` selects the A1 full-pipeline path.

        An A1-style arm is an ``Arm`` record with a NON-EMPTY ``pluginsEnabled``
        (the workflow arms install plugins; A0 has none). This keeps the dispatch
        configuration-driven per ``02-arms.md`` §Implementation layout (arms are
        records the driver reads, not code branches).
        """
        return isinstance(arm_or_solver, Arm) and bool(arm_or_solver.pluginsEnabled)

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
        self, image: str, creds_dir: Path, *, with_plugins: bool = False
    ) -> str:
        """Start a detached container; return its id.

        Bind-mounts the writable creds copy at :data:`CONTAINER_CLAUDE_DIR`,
        keeps network (default bridge has outbound), workdir ``/workspace``, and
        keeps the container alive with ``sleep`` so we can ``docker exec`` into
        it for setup, the agent run, and patch extraction. When ``with_plugins``
        is set (the A1 path), it ALSO read-only bind-mounts each host ``spec-*``
        plugin source under :data:`A1_CONTAINER_PLUGIN_ROOT` so the in-container
        ``claude -p --plugin-dir ...`` resolves the workflow skills.
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
        if with_plugins:
            alive = A1_RUN_TIMEOUT_SECONDS + AUTH_PROBE_TIMEOUT_SECONDS + 300
            for name in A1_PLUGIN_DIR_NAMES:
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

    def _run_a1_workflow(self, container_id: str, prompt: str) -> dict[str, object]:
        """Drive the A1 full pipeline to completion; return the parsed result JSON.

        A1 loads the ``spec-*`` plugins for the session with a ``--plugin-dir`` per
        mounted plugin, runs on the A1 model behind the HARD ``--max-budget-usd``
        cap, and is bounded by :data:`A1_RUN_TIMEOUT_SECONDS`. A non-zero exit OR a
        timeout is an HONEST outcome the caller surfaces with partial evidence —
        the recursive workflow may legitimately hit the cap before finishing.
        """
        plugin_flags = " ".join(
            f"--plugin-dir {A1_CONTAINER_PLUGIN_ROOT}/{name}"
            for name in A1_PLUGIN_DIR_NAMES
        )
        command = (
            f"cd {IMAGE_WORKDIR}; "
            f"claude -p {_shell_quote(prompt)} "
            f"{plugin_flags} "
            f"--model {A1_MODEL} --permission-mode bypassPermissions "
            f"--max-budget-usd {A1_MAX_BUDGET_USD} --output-format json"
        )
        result = subprocess.run(
            ["docker", "exec", container_id, "sh", "-c", command],
            capture_output=True,
            text=True,
            timeout=A1_RUN_TIMEOUT_SECONDS,
        )
        if result.returncode != _CLAUDE_EXIT_OK:
            raise ContainerRunError(
                f"A1 workflow run failed (exit {result.returncode}).\n"
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


def _shell_quote(text: str) -> str:
    """Single-quote ``text`` for safe embedding in a ``sh -c`` command."""
    return "'" + text.replace("'", "'\\''") + "'"
