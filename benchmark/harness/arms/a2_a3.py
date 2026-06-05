"""The A2 / A3 arm recipes — plan + build from a HANDED-IN spec.

Implements ``.specs/benchmark/specs/02-arms.md`` §A2 — Plan + build (spec handed
in) and §A3 — Build without gates. Both arms are configuration variants of A1
(``benchmark/harness/arms/a1.py``): they share A1's plugin mount set, model,
budget cap, artifact layout, and workflow driver, and differ ONLY in the two
controlled variables the arm set exists to isolate.

- **A2 — Plan + build (spec handed in).** Identical to A1 except ``spec-creator``
  does NOT run; a ready-made spec is provided as input. ``spec-planner`` +
  ``spec-builder`` run with BOTH gates on. ``A1 − A2`` isolates the value of the
  workflow AUTHORING the spec versus starting from one someone already wrote.
- **A3 — Build without gates.** Identical to A2 except ``spec-builder``'s two
  gates — ``semi-formal-review`` (correctness) and ``validate-done-certificate``
  (completeness) — are disabled; the implementer's self-report decides task
  completion. ``A2 − A3`` isolates the value of the gates. The ONLY behavioural
  difference from A2 is the gates.

Given-spec provenance (the resolved Open question)
--------------------------------------------------
``02-arms.md`` left open how the handed-in spec is sourced. The decision shipped
here: **a frozen authored spec asset, one per instance, checked into the suite
under ``<instance>/given_spec/given_spec.md`` and consumed IDENTICALLY by A2 and
A3.** It is authored ONCE to the fixed quality bar in
:data:`GIVEN_SPEC_QUALITY_BAR` and never regenerated per run.

Rationale: the spec must be produced "once per instance to a fixed quality bar,
so that variance in the handed-in spec does not leak into those arms' results"
(``02-arms.md`` Assumptions). Re-authoring it with ``spec-creator`` on every run
would (a) make A2 partly measure ``spec-creator`` again — defeating the point of
``A1 − A2`` — and (b) introduce run-to-run spec variance that confounds the
``A2 − A3`` gate delta. A human-frozen asset removes both confounds: A2 and A3
read the SAME bytes, so the delta between them is attributable to the gates
alone, and the delta between A1 and A2 is attributable to spec authoring alone.
The loader is :func:`benchmark.suites.greenfield.load_given_spec`.

Gate observability (A2 emits gate events, A3 emits none)
--------------------------------------------------------
The gate difference is made observable from the CAPTURED done-certificates.
When the gates run (A2), ``spec-builder``'s ``validate-done-certificate`` gate
DISCHARGES each task's certificate: it fills the obligation statuses, writes a
``VERDICT: DONE|PARTIAL|NOT_DONE`` line and sets ``State: Validated …`` /
``Status:`` away from the authored ``Pending validation`` placeholder (see
``plugins/spec-builder/skills/validate-done-certificate``); the
``semi-formal-review`` gate writes a ``VERDICT: CORRECT|LIKELY_CORRECT|CONCERNS|
BUGGY`` line. When the gates are disabled (A3) the certificates are never
discharged — they keep the authored blank ``Verdict:`` placeholder, so no gate
verdict appears.

:func:`extract_gate_events` parses the captured certificate artifacts into typed
:class:`~benchmark.harness.domain.GateEvent` records (one per discharged gate
verdict found), mapping each certificate verdict onto the closed
:data:`~benchmark.harness.domain.GATE_VERDICTS` enum. A gates-on (A2) capture
yields ``>= 1`` GateEvent; a gates-off (A3) capture yields none. This is REAL
structural GateEvent extraction, not a mere presence flag.

Everything is a named constant so the A2/A3 invocations are auditable,
reproducible, and HARD-BOUNDED — these arms spawn ``spec-builder`` sub-agents
recursively, so the budget cap and wall-clock timeout (reused from A1) are the
safety rail against an open-ended spend.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

# A2/A3 reuse A1's mount set, model, budget caps, artifact layout, and timeouts;
# only the arm records, the orchestrating prompts, the given-spec, and the gate
# observability are new here.
from benchmark.harness.arms.a1 import (
    A1_ARTIFACT_DIR,
    A1_MAX_BUDGET_USD,
    A1_MODEL,
)
from benchmark.harness.domain import (
    GATE_EVENT_ID_PREFIX,
    Arm,
    GateEvent,
    new_record_id,
)

# --- the A2 / A3 arm records ------------------------------------------------

#: The fixed A2 / A3 slugs (members of the closed ``ARM_SLUGS`` set).
A2_SLUG = "A2"
A3_SLUG = "A3"

#: The plugin slugs A2/A3 enable, in pipeline order. NO ``spec-creator`` (the
#: spec is handed in): only ``spec-planner`` + ``spec-builder``. This is the arm
#: record's DECLARED stages; the full container mount set (which also carries
#: ``reasoning-semiformally`` for the gate's reasoning skill) is
#: :data:`A2_A3_PLUGIN_DIR_NAMES` below.
A2_A3_PLUGINS_ENABLED: list[str] = ["spec-planner", "spec-builder"]

#: A2 — Plan + build (spec handed in): planner + builder, BOTH gates ON, spec
#: PROVIDED, structured parallel execution. Differs from A1 only in dropping
#: spec-creator and providing the spec.
A2 = Arm(
    slug=A2_SLUG,
    pluginsEnabled=A2_A3_PLUGINS_ENABLED,
    gatesEnabled=True,
    specProvided=True,
    executionMode="parallel-structured",
)

#: A3 — Build without gates: IDENTICAL to A2 except ``gatesEnabled=False`` (the
#: implementer's self-report decides completion). The only behavioural
#: difference from A2 is the absence of the two gates.
A3 = Arm(
    slug=A3_SLUG,
    pluginsEnabled=A2_A3_PLUGINS_ENABLED,
    gatesEnabled=False,
    specProvided=True,
    executionMode="parallel-structured",
)

# --- plugin mount recipe (read by the container RunBackend) -----------------

#: The plugin directories A2/A3 mount + load: planner + builder PLUS the
#: ``reasoning-semiformally`` skill the semi-formal gate leans on. NO
#: ``spec-creator`` — the spec is handed in, not authored. Each is mounted
#: read-only with ``--plugin-dir`` (session-only). A3 still MOUNTS the gate's
#: reasoning skill (cheap, and keeps the mount set identical to A2); the gates
#: are disabled by the A3 PROMPT, not by withholding a plugin, so A2 and A3
#: differ in exactly one variable.
A2_A3_PLUGIN_DIR_NAMES: tuple[str, ...] = (
    "spec-planner",
    "spec-builder",
    "reasoning-semiformally",
)

# --- given-spec provenance (the resolved Open question) ---------------------

#: The path, INSIDE the run container under :data:`A1_ARTIFACT_DIR`, the frozen
#: given-spec is written to BEFORE the workflow runs — the ``.specs/``
#: location ``spec-creator`` would have written to. ``spec-planner`` reads the
#: spec from here, so dropping ``spec-creator`` is transparent to the rest of
#: the pipeline. Kept under the artifact dir so it is captured into the bundle's
#: ``specArtifacts`` and EXCLUDED from the scored code diff, exactly like A1.
GIVEN_SPEC_CONTAINER_RELPATH = f"{A1_ARTIFACT_DIR}/given_spec.md"

#: The DOCUMENTED quality bar the frozen given-spec asset is authored to. Both
#: A2 and A3 read the SAME asset, so this bar is shared and spec variance cannot
#: leak into the A1−A2 or A2−A3 deltas. The asset lives at
#: ``benchmark/suites/greenfield-features/<slug>/given_spec/given_spec.md`` and
#: is loaded by ``benchmark.suites.greenfield.load_given_spec``.
GIVEN_SPEC_QUALITY_BAR = (
    "A frozen, human-authored single-file spec per instance, authored ONCE and "
    "consumed identically by A2 and A3. The bar, fixed for every instance:\n"
    "  1. Overview — the library, its components, and the dependency graph.\n"
    "  2. Domain model + invariants — the named data types and the cross-"
    "component invariants that must hold.\n"
    "  3. Components (contracts) — one section per public component with its "
    "exact signature and >= 2 worked input/output examples.\n"
    "  4. Definition of done — the acceptance bar (every stub implemented, "
    "stdlib only, __init__ re-exports, smoke test still passes, withheld suite "
    "decides resolution).\n"
    "It restates the problem statement's contracts at spec depth WITHOUT adding "
    "design decisions a spec-creator pass would invent, so A1−A2 measures spec "
    "AUTHORING and not spec CONTENT divergence."
)

# --- provisioning recipe constants ------------------------------------------

#: The model A2/A3 run on (reused from A1 so the only variables are the ones the
#: arm set isolates).
A2_A3_MODEL = A1_MODEL

#: HARD per-run budget ceiling (USD). Reused from A1's named cap: A2/A3 are the
#: same recursive workflow minus spec-creator (A2) and minus the gates (A3), so
#: they are no MORE expensive than A1 — the A1 cap is a safe, conservative
#: ceiling for both. The live run reports honestly if it hits the cap.
A2_A3_MAX_BUDGET_USD = A1_MAX_BUDGET_USD

# --- orchestrating prompts --------------------------------------------------

#: Per-task timing directive appended to A1/A2/A3 orchestrating prompts so the
#: workflow records intra-trial wall-clocks the benchmark can read back from
#: the captured certificates. spec-builder is told to write ONE line of the
#: form ``Elapsed: <seconds>s`` into each task's certificate before the gates
#: discharge it (so the line survives the merged-certificate capture path,
#: keyed by the same certificate stem ``extract_gate_events`` keys gate events
#: by). The shape and key are matched by
#: :func:`extract_task_wall_clocks`; the parser silently skips certificates
#: that do not carry the line, so bundles produced before this directive
#: shipped still validate and merely fall back to the old sum/max parallel-
#: speedup estimate.
TIMING_DIRECTIVE = (
    "Per-task timing — REQUIRED for the benchmark. For each plan task, "
    "measure the WALL-CLOCK seconds the task's implementation took from when "
    "spec-builder dispatches its implementer sub-agent to when the task is "
    "merged, and BEFORE the gates discharge the task's done-certificate "
    "write ONE line of the form ``Elapsed: <seconds>s`` into the certificate "
    "(e.g. ``Elapsed: 92.3s``). The number is a non-negative decimal; one "
    "line per certificate; no rounding to integer required. This is read back "
    "by the benchmark from the captured certificates and drives the parallel-"
    "speedup metric — omitting it makes the metric fall back to a coarser "
    "estimate, so do not omit it."
)


#: Shared preamble: the batch-run framing identical to A1's, minus the
#: spec-creator stage (the spec is already on disk).
_A2_A3_PREAMBLE = (
    "You are driving the spec-driven workflow to implement a feature in this "
    "repository non-interactively. The repository at /workspace is a skeleton "
    "with stub modules; the finished CODE must make the public API work end to "
    "end. Do not ask questions; this is a batch run with no user to prompt — "
    "make every default decision yourself and proceed.\n\n"
    "A ready-made specification has ALREADY been written for you at "
    f"{GIVEN_SPEC_CONTAINER_RELPATH} (under .specs/). Do NOT author a new "
    "spec and do NOT run spec-creator — the spec authoring stage is "
    "deliberately skipped for this run. Treat that file as the authoritative "
    "spec.\n\n"
)

#: A2 stages: plan the GIVEN spec, then build every task behind BOTH gates.
A2_INSTRUCTION = (
    _A2_A3_PREAMBLE + "Carry out these two stages in order, using the named "
    "skills:\n"
    "1. Use the spec-planner skill to decompose the GIVEN spec at "
    f"{GIVEN_SPEC_CONTAINER_RELPATH} into a dependency-ordered plan of task "
    "packages, each with a definition of done, and author one done-certificate "
    "per task. Write the plan folder under .specs/plans/.\n"
    "2. Use the spec-builder skill to build every task in the plan in an "
    "isolated workspace, gating EACH task through BOTH gates — the semi-formal "
    "correctness review AND the validate-done-certificate completeness gate — "
    "before merging it. Each gate is run by an agent other than the task's "
    "implementer, and discharges the task's done-certificate (writing the gate "
    "VERDICT into certificates/NN-<task>.md). Merge every completed task into "
    "the /workspace working tree — that working tree is the integration tip "
    "whose CODE will be scored.\n\n"
    "When you finish, the package stubs under /workspace must be fully "
    "implemented and the plan/certificate artifacts must exist under .specs/."
)

#: A3 stages: identical to A2 EXCEPT spec-builder runs WITHOUT its two gates —
#: the implementer's self-report decides completion. This is the single
#: behavioural difference from A2.
A3_INSTRUCTION = (
    _A2_A3_PREAMBLE + "Carry out these two stages in order, using the named "
    "skills:\n"
    "1. Use the spec-planner skill to decompose the GIVEN spec at "
    f"{GIVEN_SPEC_CONTAINER_RELPATH} into a dependency-ordered plan of task "
    "packages, each with a definition of done. Write the plan folder under "
    ".specs/plans/.\n"
    "2. Use the spec-builder skill to build every task in the plan in an "
    "isolated workspace, but DISABLE spec-builder's two gates for this run: do "
    "NOT run the semi-formal-review correctness gate and do NOT run the "
    "validate-done-certificate completeness gate. The implementer sub-agent's "
    "own self-report decides whether each task is complete; merge each task on "
    "that self-report alone, WITHOUT a separate reviewing or validating agent "
    "and WITHOUT discharging any done-certificate. Merge every completed task "
    "into the /workspace working tree — that working tree is the integration "
    "tip whose CODE will be scored.\n\n"
    "When you finish, the package stubs under /workspace must be fully "
    "implemented and the plan artifacts must exist under .specs/."
)


def a2_prompt(problem_statement: str) -> str:
    """Return the A2 orchestrating prompt (gates ON; spec already on disk).

    The ``problem_statement`` is appended as context, but the authoritative
    contract is the given-spec file already written into the container. The
    :data:`TIMING_DIRECTIVE` is appended so spec-builder writes a per-task
    ``Elapsed:`` line into each certificate.
    """
    return (
        f"{A2_INSTRUCTION}\n\n{TIMING_DIRECTIVE}\n\n"
        f"For context, the feature is:\n\n{problem_statement}"
    )


def a3_prompt(problem_statement: str) -> str:
    """Return the A3 orchestrating prompt (gates OFF; spec already on disk).

    The :data:`TIMING_DIRECTIVE` is appended so spec-builder writes a per-task
    ``Elapsed:`` line into each certificate even on the gates-off path (the
    certificates are written and captured regardless of whether the gates
    discharge them).
    """
    return (
        f"{A3_INSTRUCTION}\n\n{TIMING_DIRECTIVE}\n\n"
        f"For context, the feature is:\n\n{problem_statement}"
    )


# --- gate-event extraction from captured certificates -----------------------

#: GateKind enum members (mirror ``benchmark.harness.domain.GATE_KINDS``), used
#: to tag extracted events. ``review`` = semi-formal-review (correctness);
#: ``validate`` = validate-done-certificate (completeness).
GATE_KIND_REVIEW = "semi-formal-review"
GATE_KIND_VALIDATE = "validate-done-certificate"

#: The authored (UNdischarged) verdict placeholder a done-certificate carries
#: before any gate runs. A3 leaves this in place (no gate runs); a gates-on (A2)
#: discharge REPLACES it with a real ``VERDICT:`` line. A certificate that still
#: matches this is treated as ungated and yields NO GateEvent.
_BLANK_VERDICT_MARKER = re.compile(r"\*\*Verdict:\*\*\s*\(blank", re.IGNORECASE)

#: A discharged validate-done verdict line:
#: ``VERDICT: DONE|PARTIAL|NOT_DONE|UNVERIFIED``. Written by the
#: validate-done-certificate gate into the certificate's Conclusion block (see
#: the plugin's validation-protocol). ``UNVERIFIED`` is the parked-for-human
#: outcome — the gate ran but could not confirm done-ness without a human
#: sign-off (a UI-bound / non-``headlessVerifiable`` task, ``00-overview.md`` →
#: Open questions). It is the signal the manual-pause-rate metric counts
#: (``04-metrics.md`` → Bucket 4, ``benchmark/harness/stats/cost_robustness.py``).
#:
#: The ``VERDICT:`` label is matched TOLERANT of markdown emphasis: the live
#: ``spec-builder`` / ``validate-done-certificate`` gate writes the label
#: BOLD (``**VERDICT:** DONE``) under a ``## Verdict`` heading, and italic
#: (``*VERDICT:*``) / underscore-bold (``__VERDICT:__``) shapes are equally
#: valid markdown. The ``[*_]*`` runs absorb the emphasis markers around the
#: label and BETWEEN the colon and the verdict token, so both the bold live
#: shape and the bare ``VERDICT: DONE`` register — without this, a live
#: bolded certificate parses to NO gate event and A2 falsely looks ungated.
_VALIDATE_VERDICT_RE = re.compile(
    r"VERDICT[*_]*:\s*[*_]*\s*(DONE|PARTIAL|NOT_DONE|UNVERIFIED)\b", re.IGNORECASE
)

#: A discharged semi-formal-review verdict line:
#: ``VERDICT: CORRECT|LIKELY_CORRECT|CONCERNS|BUGGY``. Written by the
#: semi-formal-review gate. Like :data:`_VALIDATE_VERDICT_RE`, the label is
#: matched tolerant of markdown emphasis (bold/italic/underscore-bold around
#: the label and between the colon and the verdict token), because the live
#: gate bolds the label (``**VERDICT:** CORRECT``).
_REVIEW_VERDICT_RE = re.compile(
    r"VERDICT[*_]*:\s*[*_]*\s*(CORRECT|LIKELY_CORRECT|CONCERNS|BUGGY)\b", re.IGNORECASE
)

#: Per-task wall-clock line written by spec-builder into each certificate when
#: the orchestrating prompt requested it (added by Task 02 — capture intra-
#: trial workflow timing). Format: ``Elapsed: <seconds>s`` (or ``Elapsed:
#: <seconds> seconds``), on its own line. The number must be a non-negative
#: integer or decimal; a missing or unparseable line yields no per-task entry
#: (the consumer falls back to the old sum/max estimate).
_ELAPSED_LINE_RE = re.compile(
    r"^\s*Elapsed:\s*([0-9]+(?:\.[0-9]+)?)\s*(?:s|seconds)\b",
    re.IGNORECASE | re.MULTILINE,
)

#: Map each validate-done certificate verdict onto the closed ``GATE_VERDICTS``
#: enum (``PASS|FAIL|PARTIAL|UNVERIFIED``). DONE -> PASS (complete), PARTIAL ->
#: PARTIAL, NOT_DONE -> FAIL, UNVERIFIED -> UNVERIFIED (the gate parked for a
#: human sign-off; surfaced as the manual-pause signal, not a pass/fail). The
#: review map below has no UNVERIFIED member, so a ``VERDICT: UNVERIFIED`` line
#: yields exactly one (validate) event, never a double count.
_VALIDATE_VERDICT_MAP = {
    "DONE": "PASS",
    "PARTIAL": "PARTIAL",
    "NOT_DONE": "FAIL",
    "UNVERIFIED": "UNVERIFIED",
}

#: Map each semi-formal-review verdict onto the closed ``GATE_VERDICTS`` enum.
#: CORRECT/LIKELY_CORRECT pass the correctness gate -> PASS; CONCERNS is a soft
#: fail the build loop treats as not-passing -> PARTIAL; BUGGY -> FAIL.
_REVIEW_VERDICT_MAP = {
    "CORRECT": "PASS",
    "LIKELY_CORRECT": "PASS",
    "CONCERNS": "PARTIAL",
    "BUGGY": "FAIL",
}

#: Separator the artifact-capture step puts between a captured file's relpath
#: and its contents (mirrors ``container._classify_artifacts`` entry shape:
#: ``"<relpath>\n<contents>"``).
_CAPTURE_PATH_BODY_SEP = "\n"


def _split_capture_entry(entry: str) -> tuple[str, str]:
    """Split a captured ``"<relpath>\\n<contents>"`` bundle entry into its parts."""
    relpath, _, body = entry.partition(_CAPTURE_PATH_BODY_SEP)
    return relpath.strip(), body


def extract_gate_events(
    certificate_entries: Iterable[str], *, trial_id: str
) -> list[GateEvent]:
    """Parse captured done-certificates into typed :class:`GateEvent` records.

    ``certificate_entries`` are the bundle's ``certificateArtifacts`` — each a
    ``"<relpath>\\n<contents>"`` string (the shape
    ``container._classify_artifacts`` produces). For each certificate that has
    been DISCHARGED by a gate (carries a real ``VERDICT:`` line rather than the
    authored ``(blank …)`` placeholder), emit one GateEvent per gate verdict
    found, tagged with the discharging gate's kind and the verdict mapped onto
    the closed ``GATE_VERDICTS`` enum. The ``task`` field is the certificate's
    file stem (e.g. ``01-tokenizer``), the plan task id being gated.

    A gates-on capture (A2) yields ``>= 1`` GateEvent; a gates-off capture (A3),
    whose certificates are never discharged, yields none — making the gate
    difference observable and testable WITHOUT re-running the workflow.

    ``retryIndex`` is ``0``: the captured certificate reflects the FINAL
    discharge (the gate's last verdict before merge); per-retry history is not
    recoverable from the merged artifact and is recorded as the carried-over
    Open question.
    """
    events: list[GateEvent] = []
    for entry in certificate_entries:
        relpath, body = _split_capture_entry(entry)
        if not relpath:
            continue
        # An undischarged certificate (A3 / no gate ran) keeps the blank
        # placeholder and contributes no gate verdict.
        if _BLANK_VERDICT_MARKER.search(body):
            continue
        task = _certificate_task_id(relpath)
        for gate_kind, regex, verdict_map in (
            (GATE_KIND_VALIDATE, _VALIDATE_VERDICT_RE, _VALIDATE_VERDICT_MAP),
            (GATE_KIND_REVIEW, _REVIEW_VERDICT_RE, _REVIEW_VERDICT_MAP),
        ):
            match = regex.search(body)
            if match is None:
                continue
            verdict = verdict_map[match.group(1).upper()]
            events.append(
                GateEvent(
                    id=new_record_id(GATE_EVENT_ID_PREFIX),
                    trial=trial_id,
                    task=task,
                    gateKind=gate_kind,
                    verdict=verdict,
                    retryIndex=0,
                )
            )
    return events


def extract_task_wall_clocks(
    certificate_entries: Iterable[str],
) -> dict[str, float]:
    """Parse per-task wall-clock seconds from captured done-certificates.

    ``certificate_entries`` are the bundle's ``certificateArtifacts`` — each a
    ``"<relpath>\\n<contents>"`` string (the shape
    ``container._classify_artifacts`` produces). For each certificate that
    carries an ``Elapsed: <seconds>s`` line (written by spec-builder when the
    orchestrating prompt asks it to — see :data:`A1_TIMING_DIRECTIVE` and the
    A2/A3 preamble), emit ``{certificate stem: seconds}``. Certificates without
    an Elapsed line are silently skipped — the consumer falls back to the
    intra-campaign ``sum / max`` estimate on bundles whose certificates do not
    carry timing.

    The reused parser pattern (and the certificate stem ``task`` key) mirrors
    :func:`extract_gate_events` so both timing and gate-event extraction share
    one captured-certificate convention. Returns ``{}`` on an empty input or
    when no certificate carries an Elapsed line.
    """
    timings: dict[str, float] = {}
    for entry in certificate_entries:
        relpath, body = _split_capture_entry(entry)
        if not relpath:
            continue
        match = _ELAPSED_LINE_RE.search(body)
        if match is None:
            continue
        try:
            seconds = float(match.group(1))
        except ValueError:  # pragma: no cover — the regex already matches a number
            continue
        if seconds < 0:  # pragma: no cover — the regex's prefix forbids a minus sign
            continue
        task = _certificate_task_id(relpath)
        timings[task] = seconds
    return timings


def _certificate_task_id(relpath: str) -> str:
    """The plan task id a certificate gates = its file stem (e.g. ``01-task``)."""
    name = relpath.rsplit("/", 1)[-1]
    if name.endswith(".md"):
        name = name[: -len(".md")]
    return name or relpath
