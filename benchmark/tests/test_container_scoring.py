"""Tests for the ``container`` ScoringBackend (fresh container + baked suite).

The container backend mirrors :mod:`benchmark.harness.scoring.local`: it runs
the withheld hidden suite (the ``greenfield-hidden-tests`` convention) per
selector, builds ``fail_to_pass`` / ``pass_to_pass`` bool maps, and derives
``resolved`` / ``regressed`` through the SAME
:mod:`benchmark.harness.scoring.resolution` rule. These tests assert:

- protocol conformance (``isinstance`` of the runtime-checkable ``ScoringBackend``);
- the integrity rule — the scoring side is a container DISTINCT from any run
  container, and the hidden selectors/content are NOT in the run-side inputs
  (the run image carries no ``hidden/`` files; the arms-visible run path never
  reads the oracle fields);
- [Docker-gated] the reference solution RESOLVES on the greenfield self-test
  instance and a no-op patch does NOT (and does not crash);
- [Docker-gated] the container and ``local`` backends agree (single-sourced
  verdict) on the reference solution's ``resolved`` / ``regressed``.
"""

from __future__ import annotations

import subprocess

import pytest

from benchmark.harness.backends import ScoringBackend
from benchmark.harness.backends.interfaces import HIDDEN_TEST_FIELDS
from benchmark.harness.domain import ScoreReport
from benchmark.harness.scoring import (
    ContainerScoringBackend,
    LocalScoringBackend,
)
from benchmark.harness.scoring import container as container_mod
from benchmark.harness.scoring import resolution as scoring_resolution
from benchmark.suites import greenfield_images as images
from benchmark.suites.greenfield import (
    TEXT_TOOLKIT_SLUG,
    load_instance,
    load_reference_solution,
)

#: The no-op (empty) candidate patch: nothing is applied on the scoring side.
NOOP_PATCH = None

_DOCKER_UP = images.docker_available()
_skip_no_docker = pytest.mark.skipif(
    not _DOCKER_UP, reason="Docker daemon not reachable (docker info failed)"
)


# --- non-Docker: conformance + single-sourcing -----------------------------


def test_container_backend_satisfies_scoring_protocol() -> None:
    assert isinstance(ContainerScoringBackend(), ScoringBackend)


def test_container_backend_uses_shared_resolution_rule() -> None:
    """The container backend imports the SAME resolution functions as ``local``.

    Single-sourced verdict: both backends call ``derive_resolved`` /
    ``derive_regressed`` from :mod:`benchmark.harness.scoring.resolution`.
    """
    assert container_mod.derive_resolved is scoring_resolution.derive_resolved
    assert container_mod.derive_regressed is scoring_resolution.derive_regressed


def test_scoring_image_bakes_a_pinned_pytest() -> None:
    """The scoring Dockerfile installs a pinned pytest (deterministic, no net).

    The run image must stay pytest-free; only the scoring image bakes it in.
    """
    assert f"pytest=={images.PYTEST_VERSION}" in images._SCORING_DOCKERFILE
    assert "pip install" not in images._RUN_DOCKERFILE


# --- integrity rule: hidden selectors absent from the run-side inputs -------


def test_run_side_inputs_carry_no_hidden_selectors() -> None:
    """The arms-visible run path never carries the hidden test selectors.

    The hidden ``failToPass`` / ``passToPass`` selectors are the oracle. They
    must not appear in the run-side inputs a ``RunBackend`` is handed (the
    instance fields the run side reads: slug, problem statement, dockerImage).
    """
    instance = load_instance(TEXT_TOOLKIT_SLUG)
    hidden_selectors = [*instance.failToPass, *instance.passToPass]

    # What a RunBackend actually reads off the instance (mirrors
    # LocalRunBackend / the in-memory double): the non-oracle fields only.
    run_visible_blob = "\n".join(
        [
            instance.slug,
            instance.suite,
            instance.problemStatement,
            str(instance.dockerImage),
            str(instance.baseCommit),
        ]
    )
    for selector in hidden_selectors:
        assert selector not in run_visible_blob
    for hidden_field in HIDDEN_TEST_FIELDS:
        # The field NAMES exist on the instance, but their hidden test CONTENT
        # is not what the run path is provisioned from above.
        assert hidden_field not in run_visible_blob


# --- Docker-gated: image integrity, reference resolution, parity ------------


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
def test_run_image_carries_no_hidden_tests() -> None:
    """Integrity rule (image side): the RUN image has no ``hidden/`` files.

    The container scorer reads the hidden suite from the SCORING image only; the
    run side (the run image a RunBackend provisions) carries none of it.
    """
    spec = images.get_spec(TEXT_TOOLKIT_SLUG)
    run_tag = images.build_run_image(spec)
    assert _files_in_image(run_tag, images.REPO_HIDDEN_SUBDIR) == []


@_skip_no_docker
def test_reference_resolves_and_noop_does_not() -> None:
    """Reference-solution sanity, live: the private reference patch RESOLVES on
    the greenfield self-test instance; a no-op patch does NOT (and no crash)."""
    instance = load_instance(TEXT_TOOLKIT_SLUG)
    backend = ContainerScoringBackend()

    reference = backend.score(instance, load_reference_solution(TEXT_TOOLKIT_SLUG))
    assert isinstance(reference, ScoreReport)
    assert reference.resolved is True
    assert reference.regressed is False
    assert all(reference.failToPassResults.values())
    assert all(reference.passToPassResults.values())

    noop = backend.score(instance, NOOP_PATCH)
    assert noop.resolved is False
    # The hidden failToPass suite must NOT pass on the unpatched skeleton.
    assert not all(noop.failToPassResults.values())
    # The smoke passToPass tests still hold on the skeleton, so it is no
    # regression.
    assert noop.regressed is False


@_skip_no_docker
def test_container_and_local_agree_on_reference_solution() -> None:
    """Single-source / verdict-parity: the container and ``local`` backends
    derive the SAME ``resolved`` / ``regressed`` for the reference solution on
    the self-test instance (both via the shared resolution rule)."""
    instance = load_instance(TEXT_TOOLKIT_SLUG)
    patch = load_reference_solution(TEXT_TOOLKIT_SLUG)

    container_report = ContainerScoringBackend().score(instance, patch)
    local_report = LocalScoringBackend().score(instance, patch)

    assert container_report.resolved == local_report.resolved is True
    assert container_report.regressed == local_report.regressed is False
    # Per-selector maps agree key-for-key, value-for-value.
    assert container_report.failToPassResults == local_report.failToPassResults
    assert container_report.passToPassResults == local_report.passToPassResults
