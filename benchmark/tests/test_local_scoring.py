"""Tests for the ``local`` ScoringBackend (temp checkout + local pytest).

These build an INLINE throwaway repo source and its hidden suite inside the
test (NOT the shipped ``local-fixture`` suite, which is a separate task), then
drive ``LocalScoringBackend.score`` to assert:

- a gold patch yields ``resolved: true`` and ``regressed: false``;
- a no-op patch yields ``resolved: false`` (a ``failToPass`` never passes);
- a regression-inducing patch yields ``regressed: true``;
- the integrity rule — the scoring temp dir is DISTINCT from the run dir, and
  the hidden tests are introduced ONLY on the scoring side (never in the
  run-visible ``base/`` tree).
"""

from __future__ import annotations

from pathlib import Path

from benchmark.harness.domain import ScoreReport, TaskInstance
from benchmark.harness.scoring import (
    SCORING_TEMP_BASE,
    LocalScoringBackend,
)
from benchmark.harness.scoring.local import (
    REPO_BASE_SUBDIR,
    REPO_HIDDEN_SUBDIR,
)

# --- inline throwaway repo source ------------------------------------------

#: The base module before the gold patch: ``f()`` returns the wrong value, so
#: the failToPass test fails while the passToPass smoke test already holds.
_BASE_MOD = "def f():\n    return 0\n\n\ndef smoke():\n    return True\n"

#: Hidden failToPass test: passes only once ``f()`` returns 1.
_HIDDEN_FAIL_TO_PASS = (
    "from mod import f\n\n\ndef test_f_returns_one():\n    assert f() == 1\n"
)

#: Hidden passToPass smoke test: holds as long as ``smoke()`` stays truthy.
_HIDDEN_PASS_TO_PASS = (
    "from mod import smoke\n\n\ndef test_smoke():\n    assert smoke() is True\n"
)

#: Gold patch: rewrite the whole file so ``f()`` returns 1 (smoke unchanged).
_GOLD_PATCH = (
    "--- a/mod.py\n"
    "+++ b/mod.py\n"
    "@@ -1,5 +1,5 @@\n"
    "-def f():\n"
    "-    return 0\n"
    "+def f():\n"
    "+    return 1\n"
    " \n"
    " \n"
    " def smoke():\n"
)

#: A patch that breaks the passToPass smoke test (regression) without fixing f.
_REGRESSION_PATCH = (
    "--- a/mod.py\n"
    "+++ b/mod.py\n"
    "@@ -4,3 +4,3 @@\n"
    " \n"
    " def smoke():\n"
    "-    return True\n"
    "+    return False\n"
)

_FAIL_TO_PASS = f"{REPO_HIDDEN_SUBDIR}/test_feature.py::test_f_returns_one"
_PASS_TO_PASS = f"{REPO_HIDDEN_SUBDIR}/test_smoke.py::test_smoke"


def _build_repo_source(root: Path) -> Path:
    """Write the inline repo source layout (base/ + hidden/) under ``root``."""
    base = root / REPO_BASE_SUBDIR
    hidden = root / REPO_HIDDEN_SUBDIR
    base.mkdir(parents=True)
    hidden.mkdir(parents=True)
    (base / "mod.py").write_text(_BASE_MOD, encoding="utf-8")
    (hidden / "test_feature.py").write_text(_HIDDEN_FAIL_TO_PASS, encoding="utf-8")
    (hidden / "test_smoke.py").write_text(_HIDDEN_PASS_TO_PASS, encoding="utf-8")
    return root


def _instance(repo: Path) -> TaskInstance:
    return TaskInstance(
        slug="localfix__demo__0001",
        suite="local-fixture",
        repo=str(repo),
        baseCommit="0000000",
        problemStatement="Make f() return 1.",
        failToPass=[_FAIL_TO_PASS],
        passToPass=[_PASS_TO_PASS],
        contaminationTier="authored-private",
        headlessVerifiable=True,
        goldPatch=_GOLD_PATCH,
    )


def test_gold_patch_resolves(tmp_path: Path) -> None:
    repo = _build_repo_source(tmp_path / "repo")
    instance = _instance(repo)

    report = LocalScoringBackend().score(instance, instance.goldPatch)

    assert isinstance(report, ScoreReport)
    assert report.resolved is True
    assert report.regressed is False
    assert all(report.failToPassResults.values())
    assert all(report.passToPassResults.values())


def test_noop_patch_does_not_resolve(tmp_path: Path) -> None:
    repo = _build_repo_source(tmp_path / "repo")
    instance = _instance(repo)

    report = LocalScoringBackend().score(instance, None)

    assert report.resolved is False
    # The failToPass test never passes on the unpatched base.
    assert not all(report.failToPassResults.values())
    # The smoke passToPass test still holds, so this is not a regression.
    assert report.regressed is False


def test_regression_patch_sets_regressed(tmp_path: Path) -> None:
    repo = _build_repo_source(tmp_path / "repo")
    instance = _instance(repo)

    report = LocalScoringBackend().score(instance, _REGRESSION_PATCH)

    assert report.resolved is False
    assert report.regressed is True
    assert report.passToPassResults[_PASS_TO_PASS] is False


def test_scoring_dir_is_distinct_and_hidden_tests_only_on_scoring_side(
    tmp_path: Path,
) -> None:
    """Integrity rule: scoring temp dir is separate from the run dir, and the
    hidden suite is injected only on the scoring side (absent from base/)."""
    repo = _build_repo_source(tmp_path / "repo")
    instance = _instance(repo)

    # Stand in for a RunBackend's working directory: a checkout of the
    # run-visible base/ tree only. The hidden suite must NOT be present here.
    run_dir = tmp_path / "run-workdir"
    run_dir.mkdir()
    for item in (repo / REPO_BASE_SUBDIR).iterdir():
        (run_dir / item.name).write_text(item.read_text(), encoding="utf-8")

    run_blob = "\n".join(
        p.read_text(encoding="utf-8") for p in run_dir.rglob("*") if p.is_file()
    )
    assert "test_f_returns_one" not in run_blob
    assert "test_smoke" not in run_blob

    # The scoring side runs under SCORING_TEMP_BASE, a directory that is not the
    # run dir and not under the run dir.
    assert SCORING_TEMP_BASE != run_dir
    assert run_dir not in SCORING_TEMP_BASE.parents
    assert SCORING_TEMP_BASE not in run_dir.parents

    # And scoring still works against this distinct location.
    report = LocalScoringBackend().score(instance, instance.goldPatch)
    assert report.resolved is True
