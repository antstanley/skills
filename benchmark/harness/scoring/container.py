"""The ``container`` ScoringBackend: score a candidate patch in a clean container.

This is the containerised mirror of :mod:`benchmark.harness.scoring.local`
(``05-harness-architecture.md`` §Scoring isolation; ``06-scoring-and-statistics.md``
→ The test oracle, the ``greenfield-hidden-tests`` convention). Where the
``local`` backend uses a temp checkout + local ``pytest``, this backend uses a
FRESH scoring container — DISTINCT from any run container (the integrity rule) —
built from the greenfield SCORING image, which already carries the withheld
hidden suite at ``<WORKDIR>/hidden`` and a baked-in ``pytest`` (no per-run
network). For each :meth:`score`:

1. Resolve (and, if absent, build) the scoring image for the instance.
2. For each hidden ``failToPass`` / ``passToPass`` selector, run a fresh
   ``docker run --rm`` container that: ``git init``s the baked tree, applies the
   candidate patch on stdin (``None`` == no-op), and runs ``pytest`` for that one
   selector. The hidden suite is ALREADY in the image — it is never fetched from
   the run side.
3. Derive ``resolved`` / ``regressed`` through the SAME
   :mod:`benchmark.harness.scoring.resolution` rule the ``local`` backend uses
   (single-sourced verdict), and return a populated ``ScoreReport``.

``greenfield-hidden-tests`` convention
--------------------------------------
The scoring image bakes the run-visible ``base/`` tree at ``<WORKDIR>`` and the
withheld suite at ``<WORKDIR>/hidden`` (see
:mod:`benchmark.suites.greenfield_images`). Each hidden selector is therefore a
pytest node id of the form ``hidden/<file>::<test>`` that resolves verbatim in a
container started from that image — identical to how the same selector resolves
in the ``local`` backend's injected ``hidden/`` tree. The scoring container is
started independently of any run container, so the hidden tests/selectors are
never present in the run-side inputs.
"""

from __future__ import annotations

import subprocess

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
from benchmark.suites.greenfield_images import (
    IMAGE_WORKDIR,
    build_scoring_image,
    docker_available,
    get_spec,
    scoring_image_tag,
)

# --- named constants -------------------------------------------------------

#: Wall-clock ceiling for one scoring container (build the tree, apply the
#: patch, run one selector), in seconds. Named so a hung or pathological suite
#: cannot stall the harness indefinitely. Mirrors ``local`` but allows for the
#: container start-up overhead on top of the pytest run.
SCORE_CONTAINER_TIMEOUT_SECONDS = 300

#: pytest exit code meaning "tests ran, all selected passed". Same code the
#: ``local`` backend keys on (``_PYTEST_EXIT_OK``); selectors map to ``True``
#: iff the container's pytest exits with this.
_PYTEST_EXIT_OK = 0

#: Shell run inside the scoring container for one ``selector``. The hidden suite
#: is already baked at ``<WORKDIR>/hidden``; we only git-init the baked tree,
#: apply the candidate patch from stdin, and run that one selector. Mirrors the
#: ``local`` backend's ``_apply_patch`` (``git init -q . && git apply
#: --whitespace=nowarn -``) and ``_selector_passes`` (one pytest node id).
_SCORE_WITH_PATCH_TEMPLATE = (
    "set -e; cd {workdir}; "
    "git init -q .; "
    "git apply --whitespace=nowarn -; "
    "python -m pytest -q -p no:cacheprovider {selector}"
)

#: Same as above for the no-op patch (``candidate_patch is None``): no
#: ``git apply``, just run the selector against the baked, unpatched tree.
_SCORE_NOOP_TEMPLATE = (
    "set -e; cd {workdir}; python -m pytest -q -p no:cacheprovider {selector}"
)


class ContainerScoringError(RuntimeError):
    """Raised when the container scoring environment cannot be prepared."""


class ContainerScoringBackend:
    """``ScoringBackend`` that scores via a fresh container + baked hidden suite.

    Implements the ``ScoringBackend`` protocol (see
    ``benchmark/harness/backends/interfaces.py``) with Docker. Each
    :meth:`score` resolves the instance's SCORING image (building it on demand
    when missing), then for every hidden selector starts a FRESH
    ``docker run --rm`` container — DISTINCT from any run container — applies the
    candidate patch, and runs that one selector. ``resolved`` / ``regressed`` are
    set by the shared :mod:`benchmark.harness.scoring.resolution` rule, identical
    to the ``local`` backend.
    """

    def __init__(
        self, trial_id: str | None = None, *, build_if_missing: bool = True
    ) -> None:
        #: The trial these reports belong to; a fresh id if unset.
        self._trial_id = trial_id or new_record_id("trial")
        #: When ``True`` (default), build the scoring image on demand if it is
        #: not already present; when ``False``, require it pre-built.
        self._build_if_missing = build_if_missing

    def score(
        self, instance: TaskInstance, candidate_patch: CandidatePatch
    ) -> ScoreReport:
        """Score ``candidate_patch`` against ``instance``; return a ScoreReport.

        Resolves the scoring image, then runs each hidden ``failToPass`` /
        ``passToPass`` selector in a fresh container with the patch applied, and
        sets ``resolved`` / ``regressed`` by the shared resolution rule.
        """
        if not docker_available():
            raise ContainerScoringError(
                "Docker daemon not reachable (docker info failed); the "
                "container ScoringBackend requires Docker"
            )
        image = self._resolve_image(instance)
        fail_to_pass = {
            sel: self._selector_passes(image, candidate_patch, sel)
            for sel in instance.failToPass
        }
        pass_to_pass = {
            sel: self._selector_passes(image, candidate_patch, sel)
            for sel in instance.passToPass
        }
        return ScoreReport(
            id=new_record_id(SCORE_REPORT_ID_PREFIX),
            trial=self._trial_id,
            resolved=derive_resolved(fail_to_pass, pass_to_pass),
            regressed=derive_regressed(pass_to_pass),
            failToPassResults=fail_to_pass,
            passToPassResults=pass_to_pass,
        )

    # --- internals ---------------------------------------------------------

    def _resolve_image(self, instance: TaskInstance) -> str:
        """Return the SCORING image tag for ``instance``, building it if needed.

        The instance's ``slug`` maps to a greenfield spec via ``get_spec``; the
        scoring image bakes the hidden suite. When ``build_if_missing`` is set,
        an absent image is built via ``build_scoring_image``; otherwise the
        pre-built tag is returned and a missing image surfaces as a run error.
        """
        spec = get_spec(instance.slug)
        tag = scoring_image_tag(spec.slug)
        if self._build_if_missing and not self._image_exists(tag):
            build_scoring_image(spec)
        return tag

    @staticmethod
    def _image_exists(tag: str) -> bool:
        """Whether a local Docker image named ``tag`` is already present."""
        result = subprocess.run(
            ["docker", "image", "inspect", tag],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.returncode == 0

    def _selector_passes(
        self, image: str, candidate_patch: CandidatePatch, selector: str
    ) -> bool:
        """Run one hidden ``selector`` in a fresh scoring container; True iff pass.

        Starts a FRESH ``docker run --rm`` container from the scoring ``image``
        (DISTINCT from any run container — the integrity rule), applies the
        candidate patch (``None`` == no-op), and runs that one pytest selector.
        The hidden suite is already baked into the image; nothing is read from a
        run environment.
        """
        if candidate_patch is None:
            command = _SCORE_NOOP_TEMPLATE.format(
                workdir=IMAGE_WORKDIR, selector=selector
            )
            stdin: str | None = None
        else:
            command = _SCORE_WITH_PATCH_TEMPLATE.format(
                workdir=IMAGE_WORKDIR, selector=selector
            )
            stdin = candidate_patch
        result = subprocess.run(
            ["docker", "run", "--rm", "-i", image, "sh", "-c", command],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=SCORE_CONTAINER_TIMEOUT_SECONDS,
        )
        return result.returncode == _PYTEST_EXIT_OK
