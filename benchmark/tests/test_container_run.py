"""Tests for the ``container`` RunBackend (agent run container + A0 arm).

The container backend is the containerised mirror of
:mod:`benchmark.harness.backends.local`, implementing the path ``local``
refuses: the ``agent`` solver / the A0 arm. It provisions the agent run image,
runs the plain A0 agent to completion, and extracts the ``candidatePatch`` (diff
vs the base commit) + an ``ArtifactBundle`` with a transcript + real telemetry.
These tests assert:

- protocol conformance (``isinstance`` of the runtime-checkable ``RunBackend``);
- the fixture solver is out of scope here (``NotImplementedError``);
- the integrity rule — the agent run image carries NO ``hidden/`` content, and
  the run-side inputs carry no hidden selectors;
- [LIVE, gated on Docker+creds] an A0 run on the ``text_toolkit`` seed instance
  yields a NON-EMPTY candidate patch that APPLIES cleanly against a fresh base
  checkout, plus a bundle with a transcript and populated telemetry.

The LIVE test spends real (user-authorized) API budget: ONE run, model
``sonnet``, hard ``--max-budget-usd`` cap. It is skipped when Docker is
unreachable OR the host creds are absent, so the suite stays green in CI.
"""

from __future__ import annotations

import subprocess

import pytest

from benchmark.harness.arms.a0 import A0, A0_MAX_BUDGET_USD, a0_prompt
from benchmark.harness.backends import (
    FIXTURE_SOLVER,
    ContainerRunBackend,
    RunBackend,
)
from benchmark.harness.backends.container import HOST_CREDENTIALS_PATH
from benchmark.harness.backends.interfaces import HIDDEN_TEST_FIELDS
from benchmark.harness.domain import ArtifactBundle, Telemetry
from benchmark.suites import greenfield_images as images
from benchmark.suites.greenfield import (
    TEXT_TOOLKIT_SLUG,
    load_instance,
)

_DOCKER_UP = images.docker_available()
_CREDS_PRESENT = HOST_CREDENTIALS_PATH.is_file()

_skip_no_docker = pytest.mark.skipif(
    not _DOCKER_UP, reason="Docker daemon not reachable (docker info failed)"
)
_skip_no_live = pytest.mark.skipif(
    not (_DOCKER_UP and _CREDS_PRESENT),
    reason="LIVE A0 run needs Docker + host claude credentials",
)


# --- non-gated: conformance + arm record + scope ---------------------------


def test_backend_satisfies_run_protocol() -> None:
    assert isinstance(ContainerRunBackend(), RunBackend)


def test_a0_arm_is_a_plain_floor_arm() -> None:
    """A0 is a plain agent: no plugins, gates off, no spec, single execution."""
    assert A0.slug == "A0"
    assert A0.pluginsEnabled == []
    assert A0.gatesEnabled is False
    assert A0.specProvided is False
    assert A0.executionMode == "single"


def test_a0_prompt_carries_the_problem_statement() -> None:
    instance = load_instance(TEXT_TOOLKIT_SLUG)
    prompt = a0_prompt(instance.problemStatement)
    assert instance.problemStatement in prompt


def test_fixture_solver_is_out_of_scope() -> None:
    """The fixture solver belongs to the local backend, not this one."""
    instance = load_instance(TEXT_TOOLKIT_SLUG)
    backend = ContainerRunBackend()
    with pytest.raises(NotImplementedError):
        backend.run(instance, FIXTURE_SOLVER)


# --- integrity rule: hidden tests absent from the run side ------------------


def test_run_side_inputs_carry_no_hidden_selectors() -> None:
    """The run-side inputs a RunBackend reads carry no hidden test selectors."""
    instance = load_instance(TEXT_TOOLKIT_SLUG)
    hidden_selectors = [*instance.failToPass, *instance.passToPass]
    run_visible_blob = "\n".join(
        [
            instance.slug,
            instance.suite,
            instance.problemStatement,
            str(instance.dockerImage),
            str(instance.baseCommit),
            a0_prompt(instance.problemStatement),
        ]
    )
    for selector in hidden_selectors:
        assert selector not in run_visible_blob
    for hidden_field in HIDDEN_TEST_FIELDS:
        assert hidden_field not in run_visible_blob


def test_agent_dockerfile_adds_no_hidden_content() -> None:
    """The agent run image derives FROM the run image and copies no hidden/.

    The agent Dockerfile only layers Node + the claude CLI; it never copies the
    hidden suite, so the run-side integrity guarantee carries through.
    """
    dockerfile = images._AGENT_RUN_DOCKERFILE_TEMPLATE
    assert images.REPO_HIDDEN_SUBDIR not in dockerfile
    assert "COPY" not in dockerfile


def _files_in_image(tag: str, subdir: str) -> list[str]:
    """List files under ``<WORKDIR>/<subdir>`` inside built image ``tag``."""
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            tag,
            "sh",
            "-c",
            f"find {images.IMAGE_WORKDIR}/{subdir} -type f 2>/dev/null || true",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


@_skip_no_docker
def test_agent_run_image_carries_no_hidden_tests() -> None:
    """Integrity rule (image side): the AGENT RUN image has no ``hidden/`` files."""
    spec = images.get_spec(TEXT_TOOLKIT_SLUG)
    tag = images.build_agent_run_image(spec)
    assert _files_in_image(tag, images.REPO_HIDDEN_SUBDIR) == []


# --- LIVE: one A0 run on the seed instance (Docker + creds gated) -----------


def _apply_check(patch: str, run_image_tag: str) -> subprocess.CompletedProcess[str]:
    """``git apply --check`` the patch against a FRESH base checkout.

    Starts a throwaway container from the clean run image (the same base tree the
    agent started from, NO hidden tests), git-inits it as the base commit, and
    verifies the candidate patch applies cleanly.
    """
    command = (
        f"set -e; cd {images.IMAGE_WORKDIR}; "
        "git init -q; git add -A; "
        "git -c user.email=t@t -c user.name=t commit -q -m base; "
        "git apply --check -"
    )
    return subprocess.run(
        ["docker", "run", "--rm", "-i", run_image_tag, "sh", "-c", command],
        input=patch,
        capture_output=True,
        text=True,
        timeout=120,
    )


@_skip_no_live
def test_live_a0_run_yields_applicable_patch_and_bundle() -> None:
    """LIVE: ONE A0 run on the seed instance produces a genuine, applicable patch.

    Spends real budget (capped at ``A0_MAX_BUDGET_USD``). Asserts the candidate
    patch is non-empty, applies cleanly against a fresh base checkout, and the
    bundle carries a transcript + populated telemetry.
    """
    instance = load_instance(TEXT_TOOLKIT_SLUG)
    backend = ContainerRunBackend()

    bundle, patch = backend.run(instance, A0)

    # A genuine, non-empty candidate patch.
    assert isinstance(patch, str)
    assert patch.strip() != ""

    # It applies cleanly against a fresh checkout of the clean run image base.
    run_tag = images.build_run_image(images.get_spec(TEXT_TOOLKIT_SLUG))
    check = _apply_check(patch, run_tag)
    assert check.returncode == 0, (
        f"candidate patch did not apply cleanly:\n{check.stderr}"
    )

    # A schema-valid bundle with a transcript and populated telemetry.
    assert isinstance(bundle, ArtifactBundle)
    assert bundle.transcript is not None and bundle.transcript.strip() != ""
    assert isinstance(bundle.telemetry, Telemetry)
    assert bundle.telemetry.wallClockSeconds > 0.0
    assert bundle.telemetry.inputTokens > 0
    assert bundle.telemetry.outputTokens > 0
    assert bundle.telemetry.costUsd > 0.0
    assert bundle.telemetry.costUsd <= A0_MAX_BUDGET_USD
    assert bundle.telemetry.agentTurns >= 1
    # Round-trips through the schema.
    assert ArtifactBundle.from_dict(bundle.to_dict()) == bundle
