"""The A5 — Lighter pre-canned arm recipe (a single, non-recursive scripted call).

Implements ``docs/benchmark/specs/02-arms.md`` §A5 — Lighter pre-canned: a lighter
arm that produces the same OBSERVABLE artifacts a gated workflow arm does — a
candidate code patch AND at least one discharged done-certificate carrying a real
``VERDICT:`` line — but WITHOUT running the full recursive ``spec-planner`` +
``spec-builder`` build (which can exceed the run timeout, see
``benchmark/harness/backends/container.py`` → ``A1_RUN_TIMEOUT_SECONDS``).

Why A5 exists (the two operational needs)
-----------------------------------------
1. **A fast, reliable gate-emission witness.** Verifying that
   :func:`benchmark.harness.arms.a2_a3.extract_gate_events` maps a discharged
   ``VERDICT:`` line in a captured certificate onto a typed
   :class:`~benchmark.harness.domain.GateEvent` does not require a full recursive
   build — only a captured certificate carrying a real verdict. The recursive
   arms (A1/A2) produce that only at the END of a long, costly run that may time
   out first; A5 produces it deterministically in one bounded call.
2. **A cheaper cost-curve point.** A5 sits between the plain A0 baseline and the
   full A1 workflow at a fraction of the budget while still emitting gate events.

A5 is NOT a pairwise-delta arm: it does not isolate a single workflow stage
against another arm the way A0–A4 do (the canonical *Six arms* Decision says so
explicitly). It is a verification / cost-curve instrument.

The pre-canned (non-recursive) flow
------------------------------------
The :data:`A5` :class:`~benchmark.harness.domain.Arm` record captures the config:
NO ``spec-*`` plugins, gates ON (so it emits gate events), NO spec provided, plain
``single`` execution mode (the ``executionMode`` enum is NOT extended). The
provisioning constants here are the recipe the ``container`` RunBackend reads to
run ONE bounded ``claude -p`` call with a FIXED prompt (:data:`A5_INSTRUCTION`)
that directly implements the feature AND writes one done-certificate (with a real
``VERDICT:`` line) under ``docs/plans/.../certificates/`` — so the existing
``_capture_artifacts`` walk captures it and ``extract_gate_events`` finds ``>= 1``
GateEvent. Everything is a named constant so the A5 invocation is auditable,
reproducible, and HARD-BOUNDED by a SMALL budget cap + a SHORT timeout (the whole
point is a fast, bounded run, unlike the recursive arms).
"""

from __future__ import annotations

from benchmark.harness.arms.a0 import A0_MODEL
from benchmark.harness.domain import Arm

# --- the A5 arm record ------------------------------------------------------

#: The fixed A5 slug (one of the closed ``ARM_SLUGS`` set).
A5_SLUG = "A5"

#: A5 — Lighter pre-canned: NO ``spec-*`` plugins, gates ON (so it emits gate
#: events), NO spec provided, plain ``single`` execution. The pre-canned flow
#: scripts the observable certificate the gate machinery reads rather than
#: running a recursive gate sub-agent; ``gatesEnabled=True`` records that the arm
#: is meant to surface gate events.
A5 = Arm(
    slug=A5_SLUG,
    pluginsEnabled=[],
    gatesEnabled=True,
    specProvided=False,
    executionMode="single",
)

# --- provisioning recipe constants (read by the container RunBackend) -------

#: The model A5 runs on. Reused from A0 — A5 is a plain (no-plugin) single agent
#: like A0, just with a fixed prompt that also writes a certificate.
A5_MODEL = A0_MODEL

#: HARD per-run budget ceiling (USD) handed to ``claude --max-budget-usd``. SMALL
#: on purpose: A5 is a single non-recursive call, so it needs only a fraction of
#: the recursive arms' cap (``A1_MAX_BUDGET_USD == 20.0``). A named constant so
#: the lighter A5 run can never exceed it.
A5_MAX_BUDGET_USD = 5.0

#: Wall-clock ceiling (seconds) for the single pre-canned A5 ``claude -p`` call.
#: SHORT (10 min) because A5 does NOT recurse — it is one scripted call, so it
#: completes well inside this bound. This is the very property A5 exists for: the
#: recursive arms' ~20-minute timeout is a poor fixture for a fast gate-emission
#: check.
A5_RUN_TIMEOUT_SECONDS = 600

#: Container-relative path the pre-canned prompt is told to write its single
#: done-certificate to. Under ``docs/plans/.../certificates/`` so the existing
#: ``_capture_artifacts`` walk classifies it as a certificate (the ``cert_marker``
#: ``/certificates/`` test in ``container._classify_artifacts``), and so it is
#: EXCLUDED from the scored CODE diff (``docs/`` exclusion) exactly like a
#: workflow arm's certificate.
A5_CERTIFICATE_RELPATH = "docs/plans/a5-precanned/certificates/01-feature.md"

#: The FIXED, pre-canned prompt. It instructs the single agent to (a) implement
#: the feature in place AND (b) write ONE done-certificate carrying a real
#: ``VERDICT:`` line — in the shape
#: :func:`benchmark.harness.arms.a2_a3.extract_gate_events` parses (a
#: validate-done ``DONE|PARTIAL|NOT_DONE`` verdict) — so the captured certificate
#: yields ``>= 1`` GateEvent. It deliberately does NOT invoke ``spec-planner`` /
#: ``spec-builder`` recursively or stand up an isolated workspace: A5 is scripted,
#: not a recursive workflow.
A5_INSTRUCTION = (
    "Implement the following feature in this repository, then write ONE "
    "done-certificate recording your own verdict. This is a single scripted "
    "pass: do NOT run spec-planner or spec-builder, do NOT spawn sub-agents, and "
    "do NOT set up an isolated workspace — just implement the feature directly "
    "and write the certificate yourself.\n\n"
    "Step 1 — implement. The repository at /workspace is a skeleton with stub "
    "modules; edit the files in place so the public API works end to end. Do not "
    "ask questions; this is a batch run with no user to prompt — make every "
    "default decision yourself and proceed.\n\n"
    "Step 2 — write the done-certificate. Write a markdown file at "
    f"{A5_CERTIFICATE_RELPATH} that records, in your own assessment, whether the "
    "feature is fully implemented. The file MUST contain, on its own line, a "
    "verdict line of EXACTLY this shape:\n\n"
    "    VERDICT: DONE\n\n"
    "Use ``VERDICT: DONE`` if every stub is implemented and the public API works "
    "end to end; ``VERDICT: PARTIAL`` if you implemented some but not all of it; "
    "``VERDICT: NOT_DONE`` if you could not implement it. The verdict line is "
    "REQUIRED — it is read back by the benchmark from the captured certificate, "
    "so do not omit it or change its shape.\n\n"
    "The feature to build:\n\n"
    "{problem_statement}"
)


def a5_prompt(problem_statement: str) -> str:
    """Return the full A5 pre-canned prompt for ``problem_statement``.

    The single fixed prompt directs the agent to implement the feature AND write
    one done-certificate with a real ``VERDICT:`` line (the observable artifact
    the gate machinery reads), with no recursive ``spec-*`` workflow.
    """
    return A5_INSTRUCTION.format(problem_statement=problem_statement)
