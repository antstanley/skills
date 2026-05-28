"""OPT-IN live runtime verification of the ``container`` two-container split.

Implements ``benchmark/specs/changes/2026-05-28-add_live_container_verification.md``
→ §Proposed changes → ``05-harness-architecture.md`` §Runtime verification (the
*provisioning + capture*, *integrity rule observed*, and *two-container scoring*
bullets; Implementation notes steps 1-3). This is the containerised sibling of
:mod:`benchmark.harness.run_local_demo`: where the local demo drives the
Docker-free pipeline, this entrypoint exercises the REAL ``container``
``RunBackend`` -> ``ScoringBackend`` round-trip on Docker and witnesses, at
runtime, the three things the integrity rule promises:

1. **Round-trip.** Provision the greenfield ``text_toolkit`` AGENT RUN container,
   run the plain A0 arm through
   :class:`~benchmark.harness.backends.ContainerRunBackend`, then score the
   captured patch in a SEPARATE scoring container via
   :class:`~benchmark.harness.scoring.ContainerScoringBackend`.
2. **Resolved-parity.** Score the SAME patch through the Docker-free
   :class:`~benchmark.harness.scoring.LocalScoringBackend` and assert both
   backends agree on ``resolved``. The verdict is single-sourced through
   :mod:`benchmark.harness.scoring.resolution` (both backends derive it there) —
   this module never re-derives the resolution rule by hand. The check runs at
   BOTH poles: the private reference solution (a known-GOOD pole, expected
   ``resolved: true``) and the no-op ``None`` patch (a known-FALSE pole, expected
   ``resolved: false``), so the witness is not trivially always-true.
3. **Run-image integrity (observed, not inferred).** List ``/workspace`` inside a
   container started from the provisioned RUN image and assert no path under
   ``hidden/`` exists and none of the instance's hidden ``failToPass`` /
   ``passToPass`` test bodies are present — read at runtime from the actual
   image, not inferred from the Dockerfile. The hidden-test field names come from
   :data:`~benchmark.harness.backends.interfaces.HIDDEN_TEST_FIELDS`.

OPT-IN and bounded. The live path runs ONLY when :data:`LIVE_CONTAINER_ENV` is
``"1"`` AND Docker is reachable AND the ``claude`` CLI is on ``PATH``. Without
all three the module SKIPS cleanly: it prints one clear message and returns
:data:`SKIP_EXIT_CODE` (``0``) — no exception, no container started — exactly the
opt-in discipline of the ``BENCHMARK_RUN_GATE_PROBE_LIVE`` live gate probe
(:mod:`benchmark.harness.scoring.probes.live`). A genuine verification failure on
the live path raises :class:`ContainerCheckError`; a clean skip is NOT an error.

A reviewer exercises the skip path with ``uv run python -m
benchmark.harness.run_container_check`` (env unset) and reads this module to
confirm the round-trip, the resolved-parity, and the integrity assertions are
correct for the live path (which runs only on an operator host with Docker + an
authenticated ``claude`` CLI).
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Mapping
from dataclasses import dataclass

from benchmark.harness.arms.a0 import A0
from benchmark.harness.backends.interfaces import HIDDEN_TEST_FIELDS
from benchmark.harness.domain import Arm, GateEvent, ScoreReport, TaskInstance

# --- opt-in / bounding constants -------------------------------------------

#: The opt-in env var gating the live container round-trip. Unset / != "1" ->
#: skip (CI, routine ``check.sh``). Mirrors the sibling live opt-ins
#: (``BENCHMARK_RUN_GATE_PROBE_LIVE``, the ``BENCHMARK_RUN_*_LIVE`` family).
LIVE_CONTAINER_ENV = "BENCHMARK_RUN_CONTAINER_LIVE"

#: The value :data:`LIVE_CONTAINER_ENV` must hold to ENABLE the live path.
LIVE_CONTAINER_ENABLED_VALUE = "1"

#: The ``claude`` CLI executable name probed on ``PATH`` (the agent run side
#: needs it; absent -> clean skip, like the live gate probe's CLI dependency).
CLAUDE_CLI_NAME = "claude"

#: The greenfield self-test instance the round-trip runs over (it ships the
#: private ``reference/solution.patch`` this check uses as its known-GOOD pole).
INSTANCE_SLUG = "greenfield__text_toolkit__0001"

#: Process exit code for a clean skip (the env unset / no Docker / no CLI). A
#: skip is a success, not a failure, so the module exits 0 with a clear message.
SKIP_EXIT_CODE = 0

#: Wall-clock ceiling (seconds) for the one ``docker run`` that lists + dumps the
#: RUN image's ``/workspace`` for the integrity check. Bounded so a wedged daemon
#: cannot stall the verification; generous for a tiny listing.
IMAGE_INSPECT_TIMEOUT_SECONDS = 120

#: Path inside the RUN image whose tree the integrity check inspects (the image
#: ``WORKDIR``; mirrors ``greenfield_images.IMAGE_WORKDIR``, re-stated here so the
#: module imports without the Docker-bound suite package).
RUN_IMAGE_WORKDIR = "/workspace"

#: The forbidden run-side path PREFIX: no file under this prefix may exist in the
#: RUN image (the hidden suite is scoring-side ONLY). Mirrors the ``hidden/``
#: overlay the scoring image — and only the scoring image — carries.
HIDDEN_TREE_PREFIX = "hidden/"

#: Minimum length of a hidden-test body line to treat as a distinctive content
#: fingerprint when scanning the RUN image. Short/blank lines (imports, ``pass``,
#: braces) are too generic to be evidence of leaked hidden tests, so the content
#: check keys on the substantive assertion lines only.
MIN_FINGERPRINT_LENGTH = 24

#: Field/record separators for the single ``find | while read`` walk that returns
#: ``<relpath><FS><contents><RS>`` records from the RUN image — one ``docker run``
#: yields every path+content pair. Match ``container.py``'s artifact-walk choice
#: (ASCII unit/record separators, absent from source text).
_LISTING_FIELD_SEP = "\x1f"  # ASCII unit separator
_LISTING_RECORD_SEP = "\x1e"  # ASCII record separator

#: ``docker``/pytest-style success exit code for the listing ``docker run``.
_DOCKER_EXIT_OK = 0

# --- gate-emission check constants -----------------------------------------

#: Repetitions per (arm, instance) for the gate-emission driver run. ONE trial
#: per arm is enough: the check is qualitative (A2 emits >= 1 event, A3 emits
#: none), and each workflow run is a recursive ``spec-builder`` invocation, so
#: the smallest count keeps the (bounded) live spend down.
GATE_CHECK_TRIALS_PER_INSTANCE = 1

#: Worker-pool size for the gate-emission driver run. MUST be ``1`` (serial):
#: the driver reads the run's events off the SHARED backend's
#: :attr:`~benchmark.harness.backends.ContainerRunBackend.last_gate_events`
#: property — which reflects only the LAST run — immediately after each ``run``.
#: Running A2 and A3 concurrently through one backend would race that read, so
#: the two arms are driven one at a time to keep the re-keying deterministic.
GATE_CHECK_POOL_SIZE = 1

#: The model recorded on the gate-emission campaign. The arms (A2/A3) carry
#: their own model in their recipe; this is the campaign-record placeholder.
GATE_CHECK_MODEL = "claude-opus-4-7"

#: A fixed ``createdAt`` so the gate-emission campaign record is reproducible.
GATE_CHECK_CREATED_AT = "2026-05-28T00:00:00Z"

# --- live gate-probe check constants ---------------------------------------

#: Index into :data:`~benchmark.harness.scoring.probes.defects.DEFECT_MUTATIONS`
#: of the off-by-one mutation the live probe injects. ``[0]`` is the
#: ``text_toolkit`` ``frequency`` off-by-one (``return ranked[:limit]`` ->
#: ``return ranked[: limit + 1]``) — the classic fault a correctness gate must
#: catch. The probe stays bounded by the probe module's existing
#: ``PROBE_MAX_BUDGET_USD`` / ``PROBE_TIMEOUT_SECONDS``; no second budget here.
OFF_BY_ONE_MUTATION_INDEX = 0


class ContainerCheckError(RuntimeError):
    """Raised when the live container round-trip FAILS a verification assertion.

    A genuine witness failure: the ``container`` and ``local`` backends disagree
    on ``resolved``, a pole lands on the wrong verdict, or the RUN image carries
    hidden-test content. NOT raised for the clean skip (env unset / no Docker / no
    ``claude`` CLI) — that path returns :data:`SKIP_EXIT_CODE` with a message.
    """


@dataclass(frozen=True)
class SkipDecision:
    """Whether the live path should run, and the reason when it is skipped.

    ``should_run`` is ``True`` only when the opt-in env is set AND Docker is
    reachable AND the ``claude`` CLI is present; otherwise ``reason`` carries the
    single clear message the entrypoint prints before exiting cleanly.
    """

    #: ``True`` iff all three preconditions hold and the live path may run.
    should_run: bool
    #: The human-facing skip message (empty when ``should_run`` is ``True``).
    reason: str


@dataclass(frozen=True)
class ParityVerdict:
    """One pole's resolved-parity outcome across the two scoring backends.

    A value object recording, for a single scored patch, the ``container`` and
    ``local`` backends' ``resolved`` verdicts and whether they agreed. The poles
    are labelled (``reference`` / ``noop``) so a reviewer reads which patch each
    verdict came from.
    """

    #: The pole label (``"reference"`` known-GOOD, or ``"noop"`` known-FALSE).
    pole: str
    #: ``resolved`` from the ``container`` ScoringBackend on this patch.
    container_resolved: bool
    #: ``resolved`` from the ``local`` ScoringBackend on the SAME patch.
    local_resolved: bool

    @property
    def agree(self) -> bool:
        """``True`` iff both backends derived the SAME ``resolved`` verdict."""
        return self.container_resolved == self.local_resolved


def evaluate_skip(env: Mapping[str, str] | None = None) -> SkipDecision:
    """Decide whether the live container round-trip may run.

    Returns ``should_run=True`` ONLY when :data:`LIVE_CONTAINER_ENV` equals
    :data:`LIVE_CONTAINER_ENABLED_VALUE`, a Docker daemon is reachable, and the
    ``claude`` CLI is on ``PATH``. Any missing precondition yields
    ``should_run=False`` with a clear ``reason`` — never an exception. Docker is
    probed via the suite's :func:`~benchmark.suites.greenfield_images.docker_available`,
    lazily imported here so this module imports cleanly where Docker is absent.

    ``env`` defaults to :data:`os.environ`; it is a parameter so tests can drive
    the decision deterministically without mutating the process environment.
    """
    environ = os.environ if env is None else env
    if environ.get(LIVE_CONTAINER_ENV) != LIVE_CONTAINER_ENABLED_VALUE:
        return SkipDecision(
            should_run=False,
            reason=(
                f"skipping live container check: set "
                f"{LIVE_CONTAINER_ENV}={LIVE_CONTAINER_ENABLED_VALUE} to run the "
                f"real A0 round-trip on Docker."
            ),
        )
    if shutil.which(CLAUDE_CLI_NAME) is None:
        return SkipDecision(
            should_run=False,
            reason=(
                f"skipping live container check: the {CLAUDE_CLI_NAME!r} CLI is "
                f"not on PATH (the agent run side requires it)."
            ),
        )
    # Lazy import: the suite's docker probe lives in a Docker-bound module; keep
    # it out of module import so `import run_container_check` works without Docker.
    from benchmark.suites.greenfield_images import docker_available

    if not docker_available():
        return SkipDecision(
            should_run=False,
            reason=(
                "skipping live container check: no reachable Docker daemon "
                "(docker info failed)."
            ),
        )
    return SkipDecision(should_run=True, reason="")


def hidden_test_fingerprints(instance: TaskInstance) -> tuple[str, ...]:
    """Distinctive hidden-test body lines that MUST NOT appear in the RUN image.

    Reads, on the SCORING side (the host ``hidden/`` tree), the source of every
    hidden test the instance selects across :data:`HIDDEN_TEST_FIELDS`
    (``failToPass`` + ``passToPass``), and returns the substantive lines (those at
    least :data:`MIN_FINGERPRINT_LENGTH` long) as content fingerprints. The
    integrity check asserts none of these appear in the provisioned RUN image, so
    a leak is caught by OBSERVED content, not merely a missing path. Returns a
    de-duplicated, stably-ordered tuple; reading the host source is a scoring-side
    act and never touches the run container.
    """
    from pathlib import Path

    from benchmark.suites.greenfield import REPO_HIDDEN_SUBDIR

    selectors = _hidden_selectors(instance)
    # ``instance.repo`` is already ``.../<slug>/repo`` (``repo_source_dir``), so the
    # hidden tree is ``.../<slug>/repo/hidden`` — append only REPO_HIDDEN_SUBDIR.
    hidden_root = Path(instance.repo) / REPO_HIDDEN_SUBDIR
    fingerprints: list[str] = []
    seen: set[str] = set()
    for relpath in _selector_files(selectors):
        source = hidden_root / relpath
        if not source.is_file():
            continue
        for line in source.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if len(stripped) >= MIN_FINGERPRINT_LENGTH and stripped not in seen:
                seen.add(stripped)
                fingerprints.append(stripped)
    return tuple(fingerprints)


def _hidden_selectors(instance: TaskInstance) -> tuple[str, ...]:
    """Every hidden selector the instance carries across :data:`HIDDEN_TEST_FIELDS`."""
    selectors: list[str] = []
    for field in HIDDEN_TEST_FIELDS:
        value = getattr(instance, field, None)
        if value:
            selectors.extend(value)
    return tuple(selectors)


def _selector_files(selectors: tuple[str, ...]) -> tuple[str, ...]:
    """Map ``hidden/<file>::<test>`` selectors to their ``<file>`` paths.

    Returns the file path relative to the ``hidden/`` tree (the ``hidden/``
    prefix and the ``::<test>`` node id stripped), de-duplicated and stably
    ordered, so each hidden test file is read once for fingerprinting.
    """
    files: list[str] = []
    seen: set[str] = set()
    for selector in selectors:
        path = selector.split("::", 1)[0]
        if path.startswith(HIDDEN_TREE_PREFIX):
            path = path[len(HIDDEN_TREE_PREFIX) :]
        if path and path not in seen:
            seen.add(path)
            files.append(path)
    return tuple(files)


def assert_run_image_clean(run_image_tag: str, instance: TaskInstance) -> None:
    """Assert the provisioned RUN image carries NO hidden-test path or content.

    Starts ONE bounded ``docker run --rm`` from ``run_image_tag`` that walks
    :data:`RUN_IMAGE_WORKDIR` once and emits ``<relpath><FS><contents><RS>``
    records, then asserts — observed at runtime, not inferred from the
    Dockerfile — that (a) no path under :data:`HIDDEN_TREE_PREFIX` exists and (b)
    none of the instance's hidden-test body fingerprints
    (:func:`hidden_test_fingerprints`) appear anywhere in the image's files.
    Raises :class:`ContainerCheckError` on a violation or if the listing run
    fails. The ``docker`` import is local so the module imports without Docker.
    """
    import subprocess

    walk = (
        f"cd {RUN_IMAGE_WORKDIR}; "
        f"find . -type f | sort | while IFS= read -r f; do "
        f"printf '%s{_LISTING_FIELD_SEP}' \"$f\"; "
        f'cat "$f"; '
        f"printf '{_LISTING_RECORD_SEP}'; "
        f"done"
    )
    result = subprocess.run(
        ["docker", "run", "--rm", run_image_tag, "sh", "-c", walk],
        capture_output=True,
        text=True,
        timeout=IMAGE_INSPECT_TIMEOUT_SECONDS,
    )
    if result.returncode != _DOCKER_EXIT_OK:
        raise ContainerCheckError(
            f"failed to list {RUN_IMAGE_WORKDIR} in RUN image {run_image_tag!r} "
            f"(exit {result.returncode}).\nstderr: {result.stderr}"
        )
    listing = result.stdout
    paths, contents = _parse_listing(listing)

    leaked_paths = [p for p in paths if _is_hidden_path(p)]
    if leaked_paths:
        raise ContainerCheckError(
            f"RUN image {run_image_tag!r} carries hidden-test paths under "
            f"{HIDDEN_TREE_PREFIX!r}: {leaked_paths}. The run side must never "
            "see the hidden acceptance suite (the integrity rule)."
        )

    for fingerprint in hidden_test_fingerprints(instance):
        if fingerprint in contents:
            raise ContainerCheckError(
                f"RUN image {run_image_tag!r} carries hidden-test CONTENT "
                f"(matched a hidden test body line: {fingerprint!r}). The hidden "
                "acceptance suite must live ONLY on the scoring side."
            )


def _parse_listing(listing: str) -> tuple[tuple[str, ...], str]:
    """Split a ``find``-walk dump into ``(relative_paths, joined_contents)``.

    Each record is ``<relpath><FS><contents>``; returns the tuple of relative
    paths (``./`` prefix stripped) and a single string joining every file's
    contents (for the fingerprint substring scan).
    """
    paths: list[str] = []
    bodies: list[str] = []
    for record in listing.split(_LISTING_RECORD_SEP):
        if _LISTING_FIELD_SEP not in record:
            continue
        relpath, _, body = record.partition(_LISTING_FIELD_SEP)
        relpath = relpath.strip()
        if relpath.startswith("./"):
            relpath = relpath[2:]
        if relpath:
            paths.append(relpath)
        bodies.append(body)
    return tuple(paths), "\n".join(bodies)


def _is_hidden_path(relpath: str) -> bool:
    """``True`` iff ``relpath`` lies under the forbidden ``hidden/`` tree."""
    return relpath == HIDDEN_TREE_PREFIX.rstrip("/") or relpath.startswith(
        HIDDEN_TREE_PREFIX
    )


def assert_resolved_parity(
    instance: TaskInstance, patch: str | None, *, pole: str
) -> ParityVerdict:
    """Score ``patch`` through BOTH backends and assert they agree on ``resolved``.

    Scores the SAME ``patch`` once through
    :class:`~benchmark.harness.scoring.ContainerScoringBackend` (a fresh scoring
    container) and once through :class:`~benchmark.harness.scoring.LocalScoringBackend`
    (a temp checkout), then asserts the two ``resolved`` verdicts are equal. Both
    backends derive ``resolved`` through the single-sourced
    :mod:`benchmark.harness.scoring.resolution` rule, so this asserts they AGREE —
    it never re-derives the rule here. Returns the :class:`ParityVerdict`; raises
    :class:`ContainerCheckError` on disagreement. The backends are imported
    locally so the module imports without Docker.
    """
    from benchmark.harness.scoring import (
        ContainerScoringBackend,
        LocalScoringBackend,
    )

    container_report: ScoreReport = ContainerScoringBackend().score(instance, patch)
    local_report: ScoreReport = LocalScoringBackend().score(instance, patch)
    verdict = ParityVerdict(
        pole=pole,
        container_resolved=container_report.resolved,
        local_resolved=local_report.resolved,
    )
    if not verdict.agree:
        raise ContainerCheckError(
            f"resolved-parity FAILED on the {pole!r} pole: "
            f"container.resolved={verdict.container_resolved} != "
            f"local.resolved={verdict.local_resolved}. The two backends share the "
            "resolution rule and must agree on the same patch."
        )
    return verdict


def assert_gate_emission(instance: TaskInstance) -> None:
    """Assert A2 surfaces >= 1 ``GateEvent`` and A3 zero — at BOTH layers.

    The gate-difference witness, observed twice over so it proves the whole
    re-keying path, not just one backend attribute:

    1. **Backend layer.** Run A2 then A3 through a SHARED
       :class:`~benchmark.harness.backends.ContainerRunBackend` and read the
       events off its ``last_gate_events`` property right after each run (the
       property reflects the LAST run). A2 (gates ON) must leave ``>= 1`` event;
       A3 (gates OFF) must leave none.
    2. **Driver-threaded layer.** Drive the SAME two arms through the real
       driver (:func:`~benchmark.harness.driver.run_campaign`) — serially
       (:data:`GATE_CHECK_POOL_SIZE` ``== 1``, so the shared backend's
       last-run property is read uninterleaved) — and assert the A2
       :class:`~benchmark.harness.driver.TrialResult.gate_events` is non-empty
       and A3's is empty. This proves the driver re-keys the run's events onto
       the Trial (the tasks-08/10 wiring), not merely that the backend exposed
       them.

    Raises :class:`ContainerCheckError` on any violation at either layer. The
    Docker-bound run/scoring backends and the driver are imported locally so the
    module imports cleanly without Docker.
    """
    from benchmark.harness.arms.a2_a3 import A2, A3
    from benchmark.harness.backends import ContainerRunBackend

    # 1. Backend layer: run each arm on a shared backend and read last_gate_events.
    backend = ContainerRunBackend()
    backend.run(instance, A2)
    a2_backend_events = backend.last_gate_events
    if not a2_backend_events:
        raise ContainerCheckError(
            f"gate-emission FAILED at the backend layer: A2 (gates ON) surfaced "
            f"0 GateEvents on last_gate_events for {instance.slug!r}; a gates-on "
            "arm must discharge >= 1 certificate verdict."
        )
    backend.run(instance, A3)
    a3_backend_events = backend.last_gate_events
    if a3_backend_events:
        raise ContainerCheckError(
            f"gate-emission FAILED at the backend layer: A3 (gates OFF) surfaced "
            f"{len(a3_backend_events)} GateEvent(s) on last_gate_events for "
            f"{instance.slug!r}; a gates-off arm must discharge none."
        )
    print(
        f"gate-emission OK [backend last_gate_events]: A2={len(a2_backend_events)} "
        f"event(s) (>= 1), A3={len(a3_backend_events)} event(s) (== 0)."
    )

    # 2. Driver-threaded layer: drive both arms through run_campaign and assert
    #    the events reached TrialResult.gate_events, proving the re-keying.
    a2_trial_events = _drive_arm_gate_events(instance, A2)
    a3_trial_events = _drive_arm_gate_events(instance, A3)
    if not a2_trial_events:
        raise ContainerCheckError(
            "gate-emission FAILED at the driver layer: A2 (gates ON) carried 0 "
            "GateEvents on TrialResult.gate_events; the driver did not thread the "
            "backend's events onto the Trial."
        )
    if a3_trial_events:
        raise ContainerCheckError(
            f"gate-emission FAILED at the driver layer: A3 (gates OFF) carried "
            f"{len(a3_trial_events)} GateEvent(s) on TrialResult.gate_events; a "
            "gates-off arm must thread none."
        )
    print(
        f"gate-emission OK [driver TrialResult.gate_events]: A2="
        f"{len(a2_trial_events)} event(s) (>= 1), A3={len(a3_trial_events)} "
        f"event(s) (== 0)."
    )


def _drive_arm_gate_events(instance: TaskInstance, arm: Arm) -> tuple[GateEvent, ...]:
    """Drive ONE arm over ``instance`` through the driver; return its threaded events.

    Builds a minimal one-arm, one-instance :class:`~benchmark.harness.domain.Campaign`
    (mirroring :mod:`benchmark.harness.run_local_demo`) and runs it through the
    real :func:`~benchmark.harness.driver.run_campaign` with the ``container``
    run/scoring backends injected, SERIALLY (:data:`GATE_CHECK_POOL_SIZE`), so the
    shared backend's last-run gate events are read uninterleaved. Returns the
    single Trial's :attr:`~benchmark.harness.driver.TrialResult.gate_events` for
    the requested ``arm`` (matched by ``result.trial.arm``).
    """
    from benchmark.harness import domain
    from benchmark.harness.backends import ContainerRunBackend
    from benchmark.harness.domain import Campaign, new_record_id
    from benchmark.harness.driver import run_campaign
    from benchmark.harness.scoring import ContainerScoringBackend
    from benchmark.suites.greenfield import SUITE_SLUG

    campaign = Campaign(
        id=new_record_id(domain.CAMPAIGN_ID_PREFIX),
        createdAt=GATE_CHECK_CREATED_AT,
        model=GATE_CHECK_MODEL,
        arms=[arm.slug],
        suites=[SUITE_SLUG],
        trialsPerInstance=GATE_CHECK_TRIALS_PER_INSTANCE,
    )
    run = run_campaign(
        campaign,
        arms=[arm],
        instances=[instance],
        run_backend=ContainerRunBackend(),
        scoring_backend=ContainerScoringBackend(),
        pool_size=GATE_CHECK_POOL_SIZE,
    )
    for result in run.results:
        if result.trial.arm == arm.slug:
            return tuple(result.gate_events)
    raise ContainerCheckError(
        f"gate-emission FAILED: no TrialResult for arm {arm.slug!r} in the driver "
        f"run over {instance.slug!r}."
    )


def assert_live_gate_probe_catches_off_by_one() -> None:
    """Run the REAL review gate on an injected off-by-one; assert it was CAUGHT.

    Loads the ``text_toolkit`` reference solution, injects the off-by-one
    :data:`~benchmark.harness.scoring.probes.defects.DEFECT_MUTATIONS` entry
    (index :data:`OFF_BY_ONE_MUTATION_INDEX`) as a unified diff, and runs it
    through the live :func:`~benchmark.harness.scoring.probes.live.run_gate_probe`
    with the host-side ``claude -p`` reviewer
    (:func:`~benchmark.harness.scoring.probes.live.cli_review_gate`). Asserts the
    returned :class:`~benchmark.harness.domain.InjectedDefect` was CAUGHT —
    ``caughtBy == GATE_KIND_REVIEW`` — and raises :class:`ContainerCheckError` if
    the defect ESCAPED (``caughtBy is None``).

    The live model is nondeterministic, so this is an operator-run assertion: it
    cannot run in CI and only fires on the gated live path. The probe is bounded
    by the probe module's existing ``PROBE_MAX_BUDGET_USD`` /
    ``PROBE_TIMEOUT_SECONDS`` — no second budget is introduced here. The
    probe-bound imports are local so the module imports cleanly without the CLI.
    """
    from benchmark.harness.scoring.probes.defects import DEFECT_MUTATIONS
    from benchmark.harness.scoring.probes.live import (
        GATE_KIND_REVIEW,
        cli_review_gate,
        run_gate_probe,
    )
    from benchmark.suites.greenfield import load_reference_solution

    # Mirror the proven bad-diff pattern (benchmark/tests/test_gate_probes.py):
    # the off-by-one mutation rendered as a one-hunk unified diff against the
    # reference solution component. Load the reference solution and confirm the
    # mutation truly targets it (a stale mutation table would otherwise inject a
    # no-op diff the gate could not catch).
    reference_patch = load_reference_solution(INSTANCE_SLUG)
    mutation = DEFECT_MUTATIONS[OFF_BY_ONE_MUTATION_INDEX]
    if mutation.before not in reference_patch:
        raise ContainerCheckError(
            f"live gate probe SETUP failed: the off-by-one mutation target "
            f"{mutation.before!r} is absent from the {INSTANCE_SLUG!r} reference "
            "solution; the mutation table is stale and would inject a no-op diff."
        )
    bad_diff = (
        f"--- a/{mutation.component}.py\n+++ b/{mutation.component}.py\n"
        f"-{mutation.before}\n+{mutation.after}\n"
    )
    defect = run_gate_probe(INSTANCE_SLUG, bad_diff, mutation, reviewer=cli_review_gate)
    if defect.caughtBy != GATE_KIND_REVIEW:
        raise ContainerCheckError(
            f"live gate probe FAILED: the {GATE_KIND_REVIEW!r} gate did not catch "
            f"an injected {mutation.defect_kind} defect on {INSTANCE_SLUG!r} "
            f"(caughtBy={defect.caughtBy!r}); a correctness gate must flag a real "
            "off-by-one fault."
        )
    print(
        f"live gate probe OK: the {GATE_KIND_REVIEW!r} gate CAUGHT the injected "
        f"{mutation.defect_kind} defect (caughtBy={defect.caughtBy!r})."
    )


def run_container_check() -> tuple[ParityVerdict, ParityVerdict]:
    """Run the live A0 round-trip + integrity + dual-pole resolved-parity witness.

    ASSUMES the caller has already confirmed the live path may run (see
    :func:`evaluate_skip`); this function does the real Docker work:

    1. Load the ``text_toolkit`` instance and run the plain A0 arm through
       :class:`~benchmark.harness.backends.ContainerRunBackend` to get
       ``(bundle, patch)``, and score that captured patch in a SEPARATE scoring
       container — the two-container round-trip.
    2. Assert the provisioned RUN image carries no hidden-test path or content
       (:func:`assert_run_image_clean`) — observed at runtime.
    3. Assert resolved-parity at BOTH poles (:func:`assert_resolved_parity`): the
       private reference solution (known-GOOD, expected ``resolved: true`` on both
       backends) and the no-op ``None`` patch (known-FALSE, expected
       ``resolved: false`` on both) — the negative space proving the witness is
       not trivially always-true.
    4. Assert gate-emission (:func:`assert_gate_emission`): A2 surfaces ``>= 1``
       ``GateEvent`` and A3 zero, observed at BOTH the backend
       (``last_gate_events``) and the driver-threaded
       (``TrialResult.gate_events``) layers.
    5. Assert the live ``claude -p`` review gate CAUGHT an injected off-by-one
       defect (:func:`assert_live_gate_probe_catches_off_by_one`).

    Returns ``(reference_verdict, noop_verdict)``. Raises
    :class:`ContainerCheckError` on any verification failure. All Docker-bound
    imports are local so the module imports cleanly without Docker.
    """
    from benchmark.harness.backends import ContainerRunBackend
    from benchmark.suites.greenfield import (
        load_instance,
        load_reference_solution,
    )
    from benchmark.suites.greenfield_images import agent_run_image_tag

    instance = load_instance(INSTANCE_SLUG)

    # 1. The A0 container round-trip: provision the run container, run A0, capture
    #    the (bundle, patch), then score that patch in a SEPARATE scoring
    #    container. The run backend resolves/builds the agent run image on demand.
    run_backend = ContainerRunBackend()
    _bundle, captured_patch = run_backend.run(instance, A0)

    # 3a. Round-trip parity on the patch the agent actually produced: whatever the
    #     agent emitted, the container and local scorers must agree on resolved.
    round_trip_verdict = assert_resolved_parity(
        instance, captured_patch, pole="round_trip"
    )
    print(_format_verdict("A0 round-trip patch", round_trip_verdict))

    # 2. Run-image integrity, observed at runtime on the provisioned RUN image.
    run_image_tag = agent_run_image_tag(instance.slug)
    assert_run_image_clean(run_image_tag, instance)
    print(
        f"run-image integrity OK: {run_image_tag!r} carries no "
        f"{HIDDEN_TREE_PREFIX!r} path and no hidden-test content."
    )

    # 3b. The two poles: a known-GOOD reference patch and the known-FALSE no-op.
    reference_patch = load_reference_solution(INSTANCE_SLUG)
    reference_verdict = assert_resolved_parity(
        instance, reference_patch, pole="reference"
    )
    _assert_pole_verdict(reference_verdict, expected_resolved=True)
    print(_format_verdict("reference solution (known-GOOD pole)", reference_verdict))

    noop_verdict = assert_resolved_parity(instance, None, pole="noop")
    _assert_pole_verdict(noop_verdict, expected_resolved=False)
    print(_format_verdict("no-op patch (known-FALSE pole)", noop_verdict))

    # 4. Gate-emission: A2 emits >= 1 GateEvent and A3 none, at the backend and
    #    the driver-threaded layers (the paired gate-difference witness).
    assert_gate_emission(instance)

    # 5. Live claude -p review gate: catch an injected off-by-one defect.
    assert_live_gate_probe_catches_off_by_one()

    return reference_verdict, noop_verdict


def _assert_pole_verdict(verdict: ParityVerdict, *, expected_resolved: bool) -> None:
    """Assert a pole landed on its expected ``resolved`` value on BOTH backends.

    :func:`assert_resolved_parity` already proved the two backends AGREE; this
    additionally pins the pole to its known verdict (the reference pole resolves,
    the no-op pole does not), so a witness that flipped both backends the same
    wrong way is still caught.
    """
    if verdict.container_resolved != expected_resolved:
        raise ContainerCheckError(
            f"the {verdict.pole!r} pole expected resolved={expected_resolved} but "
            f"both backends derived resolved={verdict.container_resolved}; the "
            "witness's poles are wrong."
        )


def _format_verdict(label: str, verdict: ParityVerdict) -> str:
    """Render a :class:`ParityVerdict` for the console."""
    return (
        f"resolved-parity OK [{label}]: "
        f"container.resolved={verdict.container_resolved} == "
        f"local.resolved={verdict.local_resolved} (pole={verdict.pole})"
    )


def main() -> int:
    """Entrypoint: skip cleanly when opted out, else run the live witness.

    Consults :func:`evaluate_skip`; on a skip it prints the single clear reason
    and returns :data:`SKIP_EXIT_CODE` (``0``) — no container is started, no
    exception is raised. Otherwise it runs :func:`run_container_check`, prints the
    dual-pole verdicts, and returns ``0`` on success (a :class:`ContainerCheckError`
    propagates on a genuine verification failure).
    """
    decision = evaluate_skip()
    if not decision.should_run:
        print(decision.reason)
        return SKIP_EXIT_CODE
    print(
        f"running live container check ({LIVE_CONTAINER_ENV}="
        f"{LIVE_CONTAINER_ENABLED_VALUE}) on {INSTANCE_SLUG}..."
    )
    reference_verdict, noop_verdict = run_container_check()
    print(
        "live container check PASSED: A0 round-trip + run-image integrity + "
        f"resolved-parity at both poles "
        f"(reference={reference_verdict.container_resolved}, "
        f"noop={noop_verdict.container_resolved})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
