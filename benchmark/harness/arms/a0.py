"""The A0 — Baseline arm recipe (a plain agent on the fixed model).

Implements ``docs/benchmark/specs/02-arms.md`` §A0 — Baseline: *"A plain Claude
Code agent on the fixed model, no ``spec-*`` plugins. It receives the
TaskInstance's ``problemStatement`` and produces a patch."* A0 is the floor
against which every workflow arm's pairwise delta is read.

The :data:`A0` :class:`~benchmark.harness.domain.Arm` record captures exactly
that: NO plugins, gates OFF, NO spec provided, plain single execution. The
provisioning constants here are the recipe the ``container`` RunBackend
(``benchmark/harness/backends/container.py``) reads to invoke the plain agent —
the model, the headless flags, and the instruction wrapped around the
``problemStatement``. Everything is a named constant so the A0 invocation is
auditable and reproducible.
"""

from __future__ import annotations

from benchmark.harness.domain import Arm

# --- the A0 arm record ------------------------------------------------------

#: The fixed A0 slug (one of the closed ``ARM_SLUGS`` set).
A0_SLUG = "A0"

#: The A0 — Baseline arm: a PLAIN agent. No ``spec-*`` plugins, gates disabled,
#: no spec provided, plain ``single`` execution mode. This is the floor arm.
A0 = Arm(
    slug=A0_SLUG,
    pluginsEnabled=[],
    gatesEnabled=False,
    specProvided=False,
    executionMode="single",
)

# --- provisioning recipe constants (read by the container RunBackend) -------

#: The fixed model A0 runs on. ``sonnet`` is the model alias the headless
#: ``claude`` CLI resolves; the campaign's ``model`` would override this in a
#: full run, but A0's self-test/seed invocation pins it here.
A0_MODEL = "sonnet"

#: Hard per-run budget ceiling (USD) handed to ``claude --max-budget-usd``. A
#: named constant so the live A0 run can never exceed it; kept small because the
#: seed instance is a tiny multi-component library.
A0_MAX_BUDGET_USD = 3.0

#: Cheap budget ceiling (USD) for the fail-fast auth probe that runs BEFORE the
#: real A0 invocation, so a broken token surfaces without spending the full cap.
AUTH_PROBE_MAX_BUDGET_USD = 1.0

#: The instruction wrapped around the instance ``problemStatement`` for A0. A0
#: gets the problem statement and a plain "implement it here" directive — no
#: spec/plan/gate scaffolding (that is what the workflow arms add).
A0_INSTRUCTION = (
    "Implement the following feature in this repository. The repository is a "
    "skeleton with stub modules at /workspace; edit the files in place so the "
    "public API works end to end. Do not ask questions; make your best "
    "implementation.\n\n"
    "{problem_statement}"
)


def a0_prompt(problem_statement: str) -> str:
    """Return the full A0 prompt for ``problem_statement`` (problem + directive)."""
    return A0_INSTRUCTION.format(problem_statement=problem_statement)
