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
``arm_or_solver`` is either the ``agent`` solver-mode slug (``DEFAULT_SOLVER``)
or a full A0 :class:`~benchmark.harness.domain.Arm` record. Both select the
plain A0 agent path here. The ``fixture`` solver is the ``local`` backend's job;
it is out of scope here and raises :class:`NotImplementedError`.
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
from benchmark.harness.backends.interfaces import CandidatePatch
from benchmark.harness.domain import (
    ARTIFACT_BUNDLE_ID_PREFIX,
    DEFAULT_SOLVER,
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

        Provisions a fresh container from the agent run image, makes the base
        commit, probes auth, runs the plain A0 agent, and returns the
        ``candidatePatch`` (the diff against the base commit) with a populated
        ``ArtifactBundle``. Carries NO hidden test content across to the caller.
        """
        if not self._selects_agent(arm_or_solver):
            raise NotImplementedError(
                "ContainerRunBackend only runs the agent solver "
                f"({AGENT_SOLVER!r}) or the A0 arm; got {arm_or_solver!r}. The "
                "fixture solver is the local backend's job."
            )
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

    # --- internals ---------------------------------------------------------

    @staticmethod
    def _selects_agent(arm_or_solver: object) -> bool:
        """Whether ``arm_or_solver`` selects the agent / A0 path."""
        return arm_or_solver == AGENT_SOLVER or arm_or_solver == A0

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

    def _start_container(self, image: str, creds_dir: Path) -> str:
        """Start a detached container; return its id.

        Bind-mounts the writable creds copy at :data:`CONTAINER_CLAUDE_DIR`,
        keeps network (default bridge has outbound), workdir ``/workspace``, and
        keeps the container alive with ``sleep`` so we can ``docker exec`` into
        it for setup, the agent run, and patch extraction.
        """
        result = subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--workdir",
                IMAGE_WORKDIR,
                "-v",
                f"{creds_dir}:{CONTAINER_CLAUDE_DIR}",
                image,
                "sleep",
                str(AGENT_RUN_TIMEOUT_SECONDS + AUTH_PROBE_TIMEOUT_SECONDS + 300),
            ],
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
            f"commit -q -m base"
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

    def _extract_patch(self, container_id: str) -> CandidatePatch:
        """Return the unified diff of the working state vs the base commit.

        ``git add -A && git diff --cached`` against the base commit yields the
        candidate patch. An empty diff means the agent changed nothing -> a no-op
        patch (``None``).
        """
        command = f"set -e; cd {IMAGE_WORKDIR}; git add -A; git diff --cached"
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
