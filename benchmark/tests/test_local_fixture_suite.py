"""Tests for the bundled ``local-fixture`` suite (task 21).

These drive the SHIPPED fixture (not an inline throwaway repo) through the
task-20 ``LocalScoringBackend`` to assert the change-spec contract:

- the fixture ``TaskInstance`` loads and validates against the canonical schema;
- the local ScoringBackend scores its ``goldPatch`` as ``resolved: true`` and a
  no-op (``None``) patch as ``resolved: false``;
- the suite needs no Docker and no network (the bundled ``base/`` + ``hidden/``
  trees are present on disk and the backend touches neither).
"""

from __future__ import annotations

from pathlib import Path

from benchmark.harness.domain import TaskInstance
from benchmark.harness.scoring import LocalScoringBackend
from benchmark.harness.scoring.local import (
    REPO_BASE_SUBDIR,
    REPO_HIDDEN_SUBDIR,
)
from benchmark.suites.local_fixture import (
    BASE_COMMIT,
    FAIL_TO_PASS,
    PASS_TO_PASS,
    REPO_SOURCE_DIR,
    SUITE_SLUG,
    load_instance,
)


def test_fixture_loads_and_validates() -> None:
    instance = load_instance()

    # A validated TaskInstance (construction would have raised otherwise).
    assert isinstance(instance, TaskInstance)
    assert instance.suite == SUITE_SLUG
    assert instance.contaminationTier == "authored-private"
    assert instance.headlessVerifiable is True
    assert instance.baseCommit == BASE_COMMIT
    # local backend uses no image.
    assert instance.dockerImage is None
    assert instance.goldPatch is not None
    assert list(instance.failToPass) == list(FAIL_TO_PASS)
    assert list(instance.passToPass) == list(PASS_TO_PASS)

    # The instance also survives a schema round-trip.
    assert TaskInstance.from_dict(instance.to_dict()) == instance


def test_fixture_repo_layout_is_bundled_no_docker_no_network() -> None:
    """The fixture is self-contained on disk: base/ + hidden/ trees exist and
    the hidden suite is NOT present in the run-visible base/ tree."""
    base = REPO_SOURCE_DIR / REPO_BASE_SUBDIR
    hidden = REPO_SOURCE_DIR / REPO_HIDDEN_SUBDIR
    assert base.is_dir()
    assert hidden.is_dir()
    assert (base / "calculator.py").is_file()

    # The hidden selectors resolve to files that live ONLY under hidden/.
    base_blob = "\n".join(
        p.read_text(encoding="utf-8") for p in base.rglob("*") if p.is_file()
    )
    assert "def test_add_sums" not in base_blob
    assert "def test_identity_round_trips" not in base_blob
    for selector in (*FAIL_TO_PASS, *PASS_TO_PASS):
        rel = selector.split("::", 1)[0]
        assert (REPO_SOURCE_DIR / rel).is_file()


def test_gold_patch_resolves() -> None:
    instance = load_instance()

    report = LocalScoringBackend().score(instance, instance.goldPatch)

    assert report.resolved is True
    assert report.regressed is False
    assert all(report.failToPassResults.values())
    assert all(report.passToPassResults.values())


def test_noop_patch_does_not_resolve() -> None:
    instance = load_instance()

    report = LocalScoringBackend().score(instance, None)

    assert report.resolved is False
    # The failToPass tests never pass on the unpatched base tree.
    assert not all(report.failToPassResults.values())
    # The smoke passToPass test still holds, so this is not a regression.
    assert report.regressed is False


def test_repo_path_is_absolute_and_inside_suite() -> None:
    instance = load_instance()
    repo = Path(instance.repo)
    assert repo.is_absolute()
    assert repo == REPO_SOURCE_DIR
