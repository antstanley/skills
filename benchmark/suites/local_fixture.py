"""The bundled ``local-fixture`` suite: a Docker-free, hermetic instance.

See ``.specs/benchmark/specs/03-task-suites.md`` §Suite: ``local-fixture`` and
``changes/2026-05-27-local_backends.md``. The fixture is a tiny repository at a
fixed commit, a hidden ``pytest`` suite, and a known ``goldPatch`` that makes
the hidden tests pass. It exists to exercise the run -> score -> aggregate
pipeline deterministically, with no Docker, no network, and no LLM agent.

Layout (the contract the ``local`` ScoringBackend, task 20, expects):

    repo/
      base/     # the run-visible working tree as of baseCommit
      hidden/   # the hidden pytest files, injected ONLY on the scoring side

:func:`load_instance` returns the validated :class:`TaskInstance` whose ``repo``
points at the bundled ``repo/`` source directory, so the local ScoringBackend
scores it directly: the ``goldPatch`` resolves it, a no-op patch does not.
"""

from __future__ import annotations

from pathlib import Path

from benchmark.harness.domain import TaskInstance
from benchmark.harness.scoring.local import (
    REPO_HIDDEN_SUBDIR,
)

# --- named constants -------------------------------------------------------

#: Directory of the ``benchmark/suites`` package this loader lives in.
SUITES_DIR = Path(__file__).resolve().parent

#: Directory holding the bundled fixture (kept hyphenated to match the suite
#: slug and the change-spec path ``benchmark/suites/local-fixture/``).
FIXTURE_DIR = SUITES_DIR / "local-fixture"

#: The repo source directory holding the ``base/`` and ``hidden/`` trees the
#: local ScoringBackend models (``LocalRepoSource``).
REPO_SOURCE_DIR = FIXTURE_DIR / "repo"

#: Stable slug for the single bundled instance (matches the Slug pattern).
INSTANCE_SLUG = "localfix__calculator__0001"

#: Suite slug, mirrored from ``Suite.slug`` / the change spec.
SUITE_SLUG = "local-fixture"

#: A fixed, synthetic commit id. The fixture repo is content-addressed by the
#: bundled ``base/`` tree, not a real git history, so this is a stable
#: placeholder that satisfies the ``baseCommit`` pattern (7-40 hex chars).
BASE_COMMIT = "0000000"

#: Hidden ``failToPass`` selectors: pytest node ids under the ``hidden/`` tree,
#: resolved verbatim once the backend injects that tree into the checkout.
FAIL_TO_PASS: tuple[str, ...] = (
    f"{REPO_HIDDEN_SUBDIR}/test_add.py::test_add_sums",
    f"{REPO_HIDDEN_SUBDIR}/test_add.py::test_add_zero",
)

#: Hidden ``passToPass`` smoke selector: must keep passing after any patch.
PASS_TO_PASS: tuple[str, ...] = (
    f"{REPO_HIDDEN_SUBDIR}/test_identity.py::test_identity_round_trips",
)

#: Short prose description of the fixture task.
PROBLEM_STATEMENT = (
    "calculator.add subtracts instead of adding. Fix it so add(a, b) returns "
    "the sum, keeping identity() unchanged."
)

#: The known reference solution: a unified diff against ``base/calculator.py``
#: that makes ``add`` return a true sum. Applied at the checkout root, where
#: ``calculator.py`` sits, so the ``a/``-``b/`` prefixes strip cleanly.
GOLD_PATCH = (
    "--- a/calculator.py\n"
    "+++ b/calculator.py\n"
    "@@ -11,7 +11,7 @@\n"
    " \n"
    " def add(left: int, right: int) -> int:\n"
    '     """Return the sum of ``left`` and ``right`` (broken on the base tree)."""\n'
    "-    return left - right\n"
    "+    return left + right\n"
    " \n"
    " \n"
    " def identity(value: int) -> int:\n"
)


def load_instance() -> TaskInstance:
    """Return the validated ``local-fixture`` :class:`TaskInstance`.

    The returned instance's ``repo`` points at the bundled :data:`REPO_SOURCE_DIR`
    (a ``base/`` + ``hidden/`` source the local ScoringBackend understands), its
    ``dockerImage`` is ``None`` (the local backend uses no image), and its
    ``goldPatch`` is the known reference solution. Validates against the
    canonical schema on construction.
    """
    return TaskInstance(
        slug=INSTANCE_SLUG,
        suite=SUITE_SLUG,
        repo=str(REPO_SOURCE_DIR),
        baseCommit=BASE_COMMIT,
        problemStatement=PROBLEM_STATEMENT,
        failToPass=list(FAIL_TO_PASS),
        passToPass=list(PASS_TO_PASS),
        contaminationTier="authored-private",
        headlessVerifiable=True,
        goldPatch=GOLD_PATCH,
        dockerImage=None,
    )
