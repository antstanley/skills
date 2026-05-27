"""The ``local`` ScoringBackend: score a candidate patch with local ``pytest``.

This is the Docker-free scoring path from
``changes/2026-05-27-local_backends.md`` (``05-harness-architecture.md``
§Scoring isolation: ``local``; ``06-scoring-and-statistics.md`` →
The test oracle: ``local``). It implements the ``ScoringBackend`` protocol
(``benchmark/harness/backends/interfaces.py``) without Docker:

1. Make a FRESH temp checkout of the instance's repo at ``baseCommit`` in a
   directory DISTINCT from any run directory.
2. Apply the ``candidatePatch`` to that checkout.
3. INJECT the hidden ``failToPass`` / ``passToPass`` tests — they live ONLY on
   the scoring side, never in the repo a ``RunBackend`` provisions.
4. Run ``pytest`` as a subprocess in the temp checkout.
5. Derive ``resolved`` / ``regressed`` with the shared resolution rule and
   return a populated ``ScoreReport``.

The temp checkout is created under a named-constant base directory, kept
DISTINCT from any run working directory, and cleaned up afterwards.

How a ``local`` instance carries its repo and hidden tests
----------------------------------------------------------
The domain ``TaskInstance`` carries the repo source (``repo``), the
``baseCommit``, the ``goldPatch``, and the hidden test *selectors*
(``failToPass`` / ``passToPass``) — but not the hidden test *source*, which by
the integrity rule must never sit in the run-side repo. The ``local`` backend
therefore models ``instance.repo`` as a path to a **local repo source
directory** with a fixed, documented layout (``LocalRepoSource``):

    <repo>/
      base/      # the working tree as of baseCommit (what the run side sees)
      hidden/    # the hidden pytest files (scoring-side ONLY, injected here)

Each hidden selector is a pytest node id resolved against the injected
``hidden/`` tree (e.g. ``hidden/test_x.py::test_y``). This is a reasonable,
documented choice that satisfies the protocol and the integrity rule: the
``base/`` tree is all a ``RunBackend`` would ever check out, and ``hidden/`` is
copied in only on the scoring side, in a separate temp directory. Suites whose
tests need the production image's system dependencies remain ``container``-only.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from benchmark.harness.backends.interfaces import CandidatePatch
from benchmark.harness.domain import (
    SCORE_REPORT_ID_PREFIX,
    ScoreReport,
    TaskInstance,
    new_record_id,
)
from benchmark.harness.scoring.resolution import (
    derive_regressed,
    derive_resolved,
)

# --- named constants -------------------------------------------------------

#: Base directory under which every scoring temp checkout is created. Kept as a
#: name so the integrity rule (scoring dir DISTINCT from the run dir) is
#: auditable: a run backend never creates a working directory under this base.
SCORING_TEMP_BASE = Path(tempfile.gettempdir()) / "benchmark-scoring"

#: Prefix for each per-score temp directory under :data:`SCORING_TEMP_BASE`.
SCORING_DIR_PREFIX = "score-"

#: Subdirectory of an ``instance.repo`` source holding the run-visible working
#: tree as of ``baseCommit`` (all a ``RunBackend`` ever checks out).
REPO_BASE_SUBDIR = "base"

#: Subdirectory of an ``instance.repo`` source holding the hidden pytest files.
#: Injected ONLY on the scoring side; never copied into a run environment.
REPO_HIDDEN_SUBDIR = "hidden"

#: Where the hidden tests are injected inside the scoring checkout. Matches the
#: ``hidden/...`` prefix the selectors use, so a selector resolves verbatim.
INJECTED_HIDDEN_DIR = REPO_HIDDEN_SUBDIR

#: Wall-clock ceiling for one scoring ``pytest`` subprocess, in seconds. Named
#: so a hung or pathological suite cannot stall the harness indefinitely.
PYTEST_TIMEOUT_SECONDS = 120

#: pytest exit code meaning "tests ran, all selected passed".
_PYTEST_EXIT_OK = 0


class LocalScoringError(RuntimeError):
    """Raised when the local scoring environment cannot be prepared."""


class LocalScoringBackend:
    """``ScoringBackend`` that scores via a temp checkout + a local pytest run.

    Implements the ``ScoringBackend`` protocol (see
    ``benchmark/harness/backends/interfaces.py``) with no Docker. Each
    :meth:`score` builds a fresh temp checkout under
    :data:`SCORING_TEMP_BASE` — DISTINCT from any run directory — applies the
    candidate patch, injects the hidden suite, and runs ``pytest`` there.
    """

    def __init__(self, trial_id: str | None = None) -> None:
        #: The trial these reports belong to; a fresh id if unset.
        self._trial_id = trial_id or new_record_id("trial")

    def score(
        self, instance: TaskInstance, candidate_patch: CandidatePatch
    ) -> ScoreReport:
        """Score ``candidate_patch`` against ``instance``; return a ScoreReport.

        Builds a fresh temp checkout at ``baseCommit`` (distinct from any run
        dir), applies the patch, injects the hidden ``failToPass`` /
        ``passToPass`` suite, runs ``pytest`` per selector, and sets
        ``resolved`` / ``regressed`` by the shared resolution rule.
        """
        SCORING_TEMP_BASE.mkdir(parents=True, exist_ok=True)
        checkout = Path(
            tempfile.mkdtemp(prefix=SCORING_DIR_PREFIX, dir=SCORING_TEMP_BASE)
        )
        try:
            self._prepare_checkout(instance, candidate_patch, checkout)
            fail_to_pass = {
                sel: self._selector_passes(checkout, sel) for sel in instance.failToPass
            }
            pass_to_pass = {
                sel: self._selector_passes(checkout, sel) for sel in instance.passToPass
            }
        finally:
            shutil.rmtree(checkout, ignore_errors=True)

        return ScoreReport(
            id=new_record_id(SCORE_REPORT_ID_PREFIX),
            trial=self._trial_id,
            resolved=derive_resolved(fail_to_pass, pass_to_pass),
            regressed=derive_regressed(pass_to_pass),
            failToPassResults=fail_to_pass,
            passToPassResults=pass_to_pass,
        )

    # --- internals ---------------------------------------------------------

    def _prepare_checkout(
        self,
        instance: TaskInstance,
        candidate_patch: CandidatePatch,
        checkout: Path,
    ) -> None:
        """Materialise the base tree at ``baseCommit``, patch it, inject tests."""
        source = Path(instance.repo)
        base = source / REPO_BASE_SUBDIR
        if not base.is_dir():
            raise LocalScoringError(
                f"instance repo {source} has no {REPO_BASE_SUBDIR}/ tree "
                f"to check out at {instance.baseCommit}"
            )
        # 1. FRESH checkout of the run-visible base tree (no hidden tests yet).
        shutil.copytree(base, checkout, dirs_exist_ok=True)

        # 2. Apply the candidate patch (None == no-op).
        if candidate_patch is not None:
            self._apply_patch(checkout, candidate_patch)

        # 3. INJECT the hidden suite — scoring side ONLY.
        hidden = source / REPO_HIDDEN_SUBDIR
        if hidden.is_dir():
            shutil.copytree(hidden, checkout / INJECTED_HIDDEN_DIR, dirs_exist_ok=True)

    def _apply_patch(self, checkout: Path, patch: str) -> None:
        """Apply a unified-diff ``patch`` inside ``checkout`` via ``git apply``.

        Uses a throwaway git repo so ``git apply`` works without the upstream
        history; the candidate patch is a diff against ``baseCommit``.
        """
        run = subprocess.run  # noqa: S603 - controlled args below
        init = run(
            ["git", "init", "-q", str(checkout)],
            capture_output=True,
            text=True,
        )
        if init.returncode != 0:
            raise LocalScoringError(f"git init failed: {init.stderr.strip()}")
        applied = run(
            ["git", "-C", str(checkout), "apply", "--whitespace=nowarn", "-"],
            input=patch,
            capture_output=True,
            text=True,
        )
        if applied.returncode != 0:
            raise LocalScoringError(
                f"candidate patch did not apply: {applied.stderr.strip()}"
            )

    def _selector_passes(self, checkout: Path, selector: str) -> bool:
        """Run one pytest ``selector`` in ``checkout``; True iff it passed."""
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", selector],
            cwd=str(checkout),
            capture_output=True,
            text=True,
            timeout=PYTEST_TIMEOUT_SECONDS,
        )
        return result.returncode == _PYTEST_EXIT_OK
