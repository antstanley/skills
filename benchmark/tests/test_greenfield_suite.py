"""Tests for the bundled ``greenfield-features`` suite (task 12).

Asserts the spec contract from ``.specs/benchmark/specs/03-task-suites.md`` and
``05-harness-architecture.md``:

- every instance loads as a validated ``TaskInstance`` with ``goldPatch=None``,
  ``contaminationTier="authored-private"``, and ``testTags`` covering every
  hidden ``failToPass`` selector;
- instances are multi-component (graph width + depth);
- the self-test instance ships a private reference solution OUTSIDE the
  arms-visible fields, and that solution resolves it while a no-op does not;
- [Docker-gated] the RUN image excludes the hidden tests and the SCORING image
  includes them, and the reference solution resolves the instance in the
  scoring image while a no-op does not.

Docker-free assertions (layout, schema, testTags coverage, reference presence,
local resolution) run ALWAYS. Docker-dependent assertions skip when no daemon
answers.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

# Import the backends package first to warm the scoring/backends import graph
# (the two packages reference each other's module-level constants).
import benchmark.harness.backends  # noqa: F401
from benchmark.harness.domain import TaskInstance
from benchmark.harness.scoring import LocalScoringBackend
from benchmark.harness.scoring.local import REPO_BASE_SUBDIR as SCORER_BASE_SUBDIR
from benchmark.harness.scoring.local import REPO_HIDDEN_SUBDIR as SCORER_HIDDEN_SUBDIR
from benchmark.suites import greenfield_images as images
from benchmark.suites.greenfield import (
    BASE_COMMIT,
    CONTAMINATION_TIER,
    INSTANCE_SPECS,
    REPO_HIDDEN_SUBDIR,
    SUITE_SLUG,
    TEXT_TOOLKIT_SLUG,
    GreenfieldInstanceSpec,
    load_instance,
    load_instances,
    load_reference_solution,
    reference_solution_path,
)

# --- named constants -------------------------------------------------------

#: Minimum components for an instance to count as "multi-component".
MIN_COMPONENTS = 2

#: A no-op candidate patch (the local/container backends treat None as no-op).
NOOP_PATCH = None


# --- Docker-free: layout, schema, tags, reference --------------------------


def test_constants_mirror_the_scorer() -> None:
    """The literal subdir the loader/images use must match the scorer's."""
    assert REPO_HIDDEN_SUBDIR == SCORER_HIDDEN_SUBDIR
    assert images.REPO_BASE_SUBDIR == SCORER_BASE_SUBDIR
    assert images.REPO_HIDDEN_SUBDIR == SCORER_HIDDEN_SUBDIR


@pytest.mark.parametrize("spec", INSTANCE_SPECS, ids=lambda s: s.slug)
def test_instance_loads_and_validates(spec: GreenfieldInstanceSpec) -> None:
    instance = load_instance(spec.slug)

    assert isinstance(instance, TaskInstance)
    assert instance.suite == SUITE_SLUG
    assert instance.baseCommit == BASE_COMMIT
    assert instance.contaminationTier == CONTAMINATION_TIER == "authored-private"
    assert instance.headlessVerifiable is True
    # Greenfield: no single arms-visible reference solution.
    assert instance.goldPatch is None
    # dockerImage is the RUN image tag the two-image build produces.
    assert instance.dockerImage == images.run_image_tag(spec.slug)
    assert instance.dockerImage.endswith(":run")
    # A schema round-trip preserves the record.
    assert TaskInstance.from_dict(instance.to_dict()) == instance


@pytest.mark.parametrize("spec", INSTANCE_SPECS, ids=lambda s: s.slug)
def test_instances_are_multi_component(spec: GreenfieldInstanceSpec) -> None:
    """Each instance names several components (graph width + depth)."""
    assert len(spec.components) >= MIN_COMPONENTS
    instance = load_instance(spec.slug)
    # Width: hidden tests tag more than one distinct component.
    tagged_components = set(instance.testTags.values())
    assert tagged_components == set(spec.components)
    assert len(tagged_components) >= MIN_COMPONENTS


@pytest.mark.parametrize("spec", INSTANCE_SPECS, ids=lambda s: s.slug)
def test_testTags_cover_every_hidden_selector(spec: GreenfieldInstanceSpec) -> None:
    instance = load_instance(spec.slug)
    assert instance.testTags is not None
    # Every failToPass selector has a tag, and there are no stray tags.
    assert set(instance.testTags) == set(instance.failToPass)
    # Each tag names a real component of this instance.
    assert set(instance.testTags.values()) <= set(spec.components)


@pytest.mark.parametrize("spec", INSTANCE_SPECS, ids=lambda s: s.slug)
def test_repo_layout_splits_base_and_hidden(spec: GreenfieldInstanceSpec) -> None:
    repo = spec.repo_source_dir
    base = repo / SCORER_BASE_SUBDIR
    hidden = repo / SCORER_HIDDEN_SUBDIR
    assert base.is_dir()
    assert hidden.is_dir()

    instance = load_instance(spec.slug)

    # Hidden failToPass selector files live ONLY under hidden/.
    base_blob = "\n".join(
        p.read_text(encoding="utf-8") for p in base.rglob("*") if p.is_file()
    )
    for selector in instance.failToPass:
        prefix, _, _ = selector.partition("::")
        assert prefix.startswith(f"{SCORER_HIDDEN_SUBDIR}/")
        assert (repo / prefix).is_file()
        test_name = selector.rsplit("::", 1)[1]
        assert f"def {test_name}" not in base_blob

    # passToPass smoke selectors resolve against files in the run-visible base/.
    for selector in instance.passToPass:
        prefix, _, _ = selector.partition("::")
        assert (base / prefix).is_file()


def test_self_test_instance_ships_private_reference_outside_arms_fields() -> None:
    spec = next(s for s in INSTANCE_SPECS if s.slug == TEXT_TOOLKIT_SLUG)
    assert spec.has_reference_solution is True

    # The reference lives under reference/ — never in the arms-visible goldPatch.
    instance = load_instance(spec.slug)
    assert instance.goldPatch is None
    assert "goldPatch" not in (instance.testTags or {})

    path = reference_solution_path(spec.slug)
    assert path.is_file()
    assert path.parent.name == "reference"
    patch = load_reference_solution(spec.slug)
    assert patch.strip() != ""
    # A genuine multi-file diff (not a stub): touches several component modules.
    assert patch.count("diff --git") >= MIN_COMPONENTS


def test_load_instances_returns_all_specs() -> None:
    loaded = {inst.slug for inst in load_instances()}
    assert loaded == {spec.slug for spec in INSTANCE_SPECS}


def test_reference_solution_resolves_locally_and_noop_does_not() -> None:
    """Docker-free oracle: the private reference resolves the self-test instance
    via the local ScoringBackend, and a no-op patch does not."""
    instance = load_instance(TEXT_TOOLKIT_SLUG)

    resolved = LocalScoringBackend().score(
        instance, load_reference_solution(TEXT_TOOLKIT_SLUG)
    )
    assert resolved.resolved is True
    assert resolved.regressed is False
    assert all(resolved.failToPassResults.values())
    assert all(resolved.passToPassResults.values())

    noop = LocalScoringBackend().score(instance, NOOP_PATCH)
    assert noop.resolved is False
    assert noop.regressed is False  # smoke passToPass still holds on the skeleton


# --- Docker-gated: the two-image split and image-side resolution -----------

_DOCKER_UP = images.docker_available()
_skip_no_docker = pytest.mark.skipif(
    not _DOCKER_UP, reason="Docker daemon not reachable (docker info failed)"
)


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
def test_run_image_excludes_hidden_scoring_image_includes() -> None:
    spec = next(s for s in INSTANCE_SPECS if s.slug == TEXT_TOOLKIT_SLUG)
    run_tag = images.build_run_image(spec)
    scoring_tag = images.build_scoring_image(spec)

    run_hidden = _files_in_image(run_tag, SCORER_HIDDEN_SUBDIR)
    scoring_hidden = _files_in_image(scoring_tag, SCORER_HIDDEN_SUBDIR)

    # Integrity rule: the run image carries NO hidden test files.
    assert run_hidden == []
    # The scoring image DOES carry the hidden acceptance suite.
    instance = load_instance(spec.slug)
    hidden_files = {
        sel.partition("::")[0].split("/", 1)[1] for sel in instance.failToPass
    }
    scoring_names = {Path(p).name for p in scoring_hidden}
    assert hidden_files <= scoring_names


@_skip_no_docker
def test_reference_resolves_in_scoring_image_and_noop_does_not() -> None:
    """Apply the reference patch inside the scoring image, run the hidden suite;
    it resolves. The unpatched skeleton (no-op) does not."""
    spec = next(s for s in INSTANCE_SPECS if s.slug == TEXT_TOOLKIT_SLUG)
    scoring_tag = images.build_scoring_image(spec)
    patch = load_reference_solution(spec.slug)
    instance = load_instance(spec.slug)
    selectors = " ".join(instance.failToPass)

    # No-op: hidden failToPass suite must FAIL on the unpatched skeleton.
    noop = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            scoring_tag,
            "sh",
            "-c",
            f"cd {images.IMAGE_WORKDIR} && pip install -q pytest >/dev/null 2>&1; "
            f"python -m pytest -q {selectors}",
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert noop.returncode != 0, noop.stdout + noop.stderr

    # Reference: apply the patch, then the hidden suite (+ smoke) passes.
    smoke = " ".join(instance.passToPass)
    resolve = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-i",
            scoring_tag,
            "sh",
            "-c",
            f"cd {images.IMAGE_WORKDIR} && pip install -q pytest >/dev/null 2>&1; "
            "git init -q . && git apply --whitespace=nowarn - && "
            f"python -m pytest -q {selectors} {smoke}",
        ],
        input=patch,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert resolve.returncode == 0, resolve.stdout + resolve.stderr
