"""The A4 — Parallel but unstructured arm recipe (naive N-way split).

Implements ``.specs/benchmark/specs/02-arms.md`` §A4 — Parallel but unstructured:
*"A naive N-way decomposition of the problem across parallel agents, with no
dependency-ordered DAG, no per-task definition of done, and no gates. Controls
for the possibility that any A1 gain is merely the effect of running several
agents at once rather than of the spec-driven structure. N is set to match A1's
typical task count on the same instance so the parallelism budget is
comparable."* The ``A1 − A4`` delta isolates *structured workflow vs equal-budget
raw parallelism*.

The :data:`A4` :class:`~benchmark.harness.domain.Arm` record captures the
configuration: NO plugins, gates OFF, NO spec provided, ``parallel-unstructured``
execution. A4 is a PLAIN agent (like A0 — no ``spec-*`` plugins) replicated N
times concurrently, each agent editing its own copy of the shared repo skeleton,
with the N outputs combined by a NAIVE merge. Everything is a named constant so
the A4 invocation is auditable, reproducible, and HARD-BOUNDED.

The pinned decomposition policy (resolves the A4 Open question)
---------------------------------------------------------------
``02-arms.md`` left open what counts as a fair "naive split" — a fixed
file/region partition or a single unstructured "split this N ways" prompt. The
decision shipped here, chosen so ``A1 − A4`` is a clean *structure-vs-concurrency*
test:

**A FIXED, PROMPT-ONLY N-way split with NO intelligent planning.** All N agents
receive the IDENTICAL full ``problemStatement`` plus a fixed coordination-free
framing — *"you are agent i of N working concurrently with no coordination;
implement your share of this feature in this shared repository"*. There is NO
dependency-ordered DAG, NO per-task definition of done, NO gates, and NO
``spec-*`` plugin (no ``spec-planner`` decides the slices). The "decomposition"
is the trivial, syntactic one the framing induces — each agent self-selects a
share of the SAME problem with no coordinator and no plan — which is exactly the
"naive N-way decomposition … with no dependency-ordered DAG, no per-task
definition of done, and no gates" the spec calls for.

Rationale. A4 must hold the *parallelism budget* equal to A1 while removing ALL
of A1's structure (spec authoring, dependency-ordered planning, definitions of
done, and gates). Two candidate splits were considered:

  1. A *spec-planner-style component partition* — split the problem into N
     well-chosen, dependency-aware components and hand one to each agent. REJECTED:
     producing a sensible component partition IS planning. It would smuggle a
     (cheap, un-gated) planning step into A4 and contaminate the ``A1 − A4`` delta
     with planning value — the opposite of a clean structure-vs-concurrency test.
  2. The *prompt-only identical-statement split* shipped here. CHOSEN: it adds
     zero planning — every agent sees the same bytes and self-divides with no
     coordinator — so the ONLY thing A4 adds over A0 is raw concurrency, and the
     ONLY thing A1 adds over A4 is the spec-driven structure. That is precisely
     the variable ``A1 − A4`` exists to isolate. It is also trivially reproducible:
     the prompt is a fixed template and N is a named constant.

The cost of the choice is honest and is the POINT of the arm: with no plan, no
DoD, and no gates, the N agents' edits routinely overlap and conflict. A4 records
those conflicts rather than resolving them well (see the naive-merge policy
below) — an arm with no structure has no principled way to resolve them, and
making that visible is what the ``A1 − A4`` delta is meant to measure.

N — matched to A1's task count on the seed
------------------------------------------
:data:`A4_N` is set to **4**, matched to A1's typical task count on the
``text_toolkit`` seed instance: A1's live plan for that instance decomposed into
exactly four tasks (``01-tokenizer``, ``02-normalizer``, ``03-frequency``,
``04-pipeline`` — see ``benchmark/tests/_a1_live_evidence``). Matching N to A1's
task count is what equalises the concurrency budget so ``A1 − A4`` tests
*structure*, not *how many agents ran* (``02-arms.md`` §Implementation layout:
"N ≈ A1's task count").

Budget matching to A1
---------------------
A4's TOTAL budget across its N agents is capped at :data:`A4_TOTAL_MAX_BUDGET_USD`
== A1's single-run cap (``A1_MAX_BUDGET_USD``), so the A1−A4 comparison holds the
parallelism *spend* fixed and only the structure varies. Each of the N agents
gets an equal slice, :data:`A4_PER_AGENT_MAX_BUDGET_USD` == total / N, handed to
its ``claude --max-budget-usd``. So the sum of the per-agent caps can never exceed
A1's cap — the budgets are matched by construction, not by hope.
"""

from __future__ import annotations

from benchmark.harness.arms.a0 import A0_MODEL
from benchmark.harness.arms.a1 import A1_MAX_BUDGET_USD
from benchmark.harness.domain import Arm

# --- the A4 arm record ------------------------------------------------------

#: The fixed A4 slug (one of the closed ``ARM_SLUGS`` set).
A4_SLUG = "A4"

#: A4 — Parallel but unstructured: a PLAIN agent (NO ``spec-*`` plugins) run N
#: times concurrently, gates OFF, NO spec provided, ``parallel-unstructured``
#: execution. The naive-parallelism control for ``A1 − A4``.
A4 = Arm(
    slug=A4_SLUG,
    pluginsEnabled=[],
    gatesEnabled=False,
    specProvided=False,
    executionMode="parallel-unstructured",
)

# --- N (matched to A1's task count on the seed) -----------------------------

#: The number of parallel agents A4 runs. Set to **4** to MATCH A1's typical task
#: count on the seed instance: A1's live plan for ``text_toolkit`` decomposed into
#: exactly four tasks (see the module docstring + ``_a1_live_evidence``). Matching
#: N to A1's task count equalises the parallelism budget so ``A1 − A4`` isolates
#: structure, not concurrency count (``02-arms.md`` §Implementation layout).
A4_N = 4

# --- budget matching to A1 --------------------------------------------------

#: A4's TOTAL budget across all N agents (USD) — set EQUAL to A1's single-run cap
#: so the A1−A4 comparison holds parallelism SPEND fixed and only structure
#: varies. A named constant so the live A4 run can never out-spend A1.
A4_TOTAL_MAX_BUDGET_USD = A1_MAX_BUDGET_USD

#: Per-agent budget cap (USD) handed to each agent's ``claude --max-budget-usd``
#: == total / N. The sum of the N per-agent caps therefore equals
#: :data:`A4_TOTAL_MAX_BUDGET_USD` by construction (budget matched, not hoped).
A4_PER_AGENT_MAX_BUDGET_USD = A4_TOTAL_MAX_BUDGET_USD / A4_N

#: The model A4 runs on (reused from A0 so A4 is a plain agent replicated N times;
#: the only variables vs A0 are concurrency + the naive merge).
A4_MODEL = A0_MODEL

# --- the fixed, prompt-only, coordination-free slice prompt -----------------

#: The fixed slice-prompt template. Every one of the N agents gets the IDENTICAL
#: full ``problem_statement`` plus this coordination-free framing — NO plan, NO
#: DoD, NO gates, NO coordinator decides the slices. ``{agent_index}`` /
#: ``{agent_count}`` make the "agent i of N, no coordination" framing explicit so
#: the agents self-divide the SAME problem; this is the naive split the pinned
#: policy fixes. No ``spec-*`` skills are mounted, so no planning happens.
A4_SLICE_INSTRUCTION = (
    "You are agent {agent_index} of {agent_count} working CONCURRENTLY on the "
    "same feature in this shared repository, with NO coordination between you "
    "and the other agents and NO shared plan. There is no task breakdown, no "
    "definition of done, and no review — just implement your share of the "
    "feature below as best you can on your own. The repository at /workspace is "
    "a skeleton with stub modules; edit the files in place so the public API "
    "works end to end. Do not ask questions; this is a batch run with no user "
    "to prompt — make every default decision yourself and proceed.\n\n"
    "Because {agent_count} agents are dividing this work with no coordinator, "
    "pick the part of the feature you (agent {agent_index}) will own and "
    "implement it; do not assume the others will cover any particular piece.\n\n"
    "The feature to build:\n\n"
    "{problem_statement}"
)


def a4_slice_prompt(
    problem_statement: str, *, agent_index: int, agent_count: int = A4_N
) -> str:
    """Return the A4 slice prompt for agent ``agent_index`` of ``agent_count``.

    Every agent gets the SAME ``problem_statement`` plus the fixed
    coordination-free framing (the pinned naive split). ``agent_index`` is
    1-based; ``agent_count`` defaults to the matched :data:`A4_N`.
    """
    return A4_SLICE_INSTRUCTION.format(
        agent_index=agent_index,
        agent_count=agent_count,
        problem_statement=problem_statement,
    )
