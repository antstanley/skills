"""The A1 — Full pipeline arm recipe (``spec-creator → spec-planner → spec-builder``).

Implements ``docs/benchmark/specs/02-arms.md`` §A1 — Full pipeline: *"spec-creator
authors a spec from the problem statement, spec-planner decomposes it into a task
graph with definitions of done and done-certificates, and spec-builder builds each
task in an isolated workspace behind both gates, merging into an integration
point."* A1 is the system under test — the full ``spec-*`` workflow — read against
the A0 floor as the headline ``A1 − A0`` delta (``06-scoring-and-statistics.md``).

The :data:`A1` :class:`~benchmark.harness.domain.Arm` record captures the
configuration: the three ``spec-*`` plugins enabled, BOTH gates on, NO spec
provided (the workflow authors it), and ``parallel-structured`` execution (the
spec-builder walks the plan's dependency graph in waves). The provisioning
constants here are the recipe the ``container`` RunBackend
(``benchmark/harness/backends/container.py``) reads to mount the plugins, enable
them, and drive the workflow end to end with one orchestrating ``claude -p``
prompt. Everything is a named constant so the A1 invocation is auditable,
reproducible, and HARD-BOUNDED — this arm spawns sub-agents recursively, so the
budget cap and wall-clock timeout below are the safety rail against an open-ended
spend.
"""

from __future__ import annotations

from pathlib import Path

from benchmark.harness.domain import Arm

# --- the A1 arm record ------------------------------------------------------

#: The fixed A1 slug (one of the closed ``ARM_SLUGS`` set).
A1_SLUG = "A1"

#: The plugin slugs A1 enables, in pipeline order. ``spec-builder`` vendors its
#: own workspace isolation but, in this harness, the workflow also reaches for
#: ``reasoning-semiformally`` (the semi-formal gate's reasoning skill), so all
#: four are mounted; the three the arm record declares are the pipeline stages.
A1_PLUGINS_ENABLED: list[str] = ["spec-creator", "spec-planner", "spec-builder"]

#: The full ``spec-*`` workflow arm: creator + planner + builder, BOTH gates on,
#: NO spec provided (the workflow authors it), structured parallel execution
#: (spec-builder walks the plan DAG in waves). The system under test.
A1 = Arm(
    slug=A1_SLUG,
    pluginsEnabled=A1_PLUGINS_ENABLED,
    gatesEnabled=True,
    specProvided=False,
    executionMode="parallel-structured",
)

# --- plugin mount recipe (read by the container RunBackend) -----------------

#: The host marketplace checkout that holds the ``spec-*`` plugin sources. The
#: container backend bind-mounts each plugin's directory (read-only) and passes a
#: ``--plugin-dir`` per plugin so the in-container ``claude -p`` resolves the
#: ``spec-creator`` / ``spec-planner`` / ``spec-builder`` skills for the session.
HOST_PLUGIN_MARKETPLACE_DIR = (
    Path.home() / ".claude" / "plugins" / "marketplaces" / "skills" / "plugins"
)

#: The plugin directories A1 mounts + loads, in pipeline order PLUS the
#: ``reasoning-semiformally`` skill the semi-formal gate leans on. Each is mounted
#: read-only and loaded with ``--plugin-dir`` (session-only, repeatable). Kept
#: distinct from :data:`A1_PLUGINS_ENABLED` (the three declared pipeline stages):
#: this is the full mount set the live workflow needs to run its gates.
A1_PLUGIN_DIR_NAMES: tuple[str, ...] = (
    "spec-creator",
    "spec-planner",
    "spec-builder",
    "reasoning-semiformally",
)

#: Mount point INSIDE the container for the read-only plugin sources. Each plugin
#: ``<name>`` is mounted at ``<A1_CONTAINER_PLUGIN_ROOT>/<name>`` and loaded with
#: ``--plugin-dir <that path>``.
A1_CONTAINER_PLUGIN_ROOT = "/opt/spec-plugins"

# --- provisioning recipe constants ------------------------------------------

#: The fixed model A1 runs on. The orchestrator and every sub-agent it spawns run
#: on this model alias the headless ``claude`` CLI resolves.
A1_MODEL = "sonnet"

#: HARD per-run budget ceiling (USD) handed to ``claude --max-budget-usd``. A1 is
#: a RECURSIVE workflow (the orchestrator spawns spec-builder sub-agents), so this
#: cap is the named safety rail against an open-ended spend. Conservative on
#: purpose; the live run reports honestly if it hits the cap before completing.
A1_MAX_BUDGET_USD = 20.0

#: Cheap budget ceiling (USD) for the FEASIBILITY PROBE — a short, capped A1 run
#: that confirms the plugins load and a spec file starts being produced, BEFORE
#: committing the full :data:`A1_MAX_BUDGET_USD`.
A1_FEASIBILITY_PROBE_MAX_BUDGET_USD = 5.0

#: Directory prefix (under the workspace) the workflow writes its artifacts into:
#: specs at ``docs/specs/``, plans + certificates at ``docs/plans/...``. The
#: candidate-patch extractor EXCLUDES this whole subtree so workflow artifacts
#: never leak into the scored CODE diff (they are captured into the bundle
#: instead). A single named constant so the exclusion and the capture agree.
A1_ARTIFACT_DIR = "docs"

#: Sub-paths under :data:`A1_ARTIFACT_DIR` that hold each artifact class. Used to
#: classify captured files into spec / plan / certificate buckets of the bundle.
A1_SPEC_SUBDIR = "specs"
A1_PLAN_SUBDIR = "plans"
A1_CERTIFICATE_DIR_NAME = "certificates"

#: The orchestrating prompt that drives the whole pipeline non-interactively. It
#: instructs the single headless agent to (a) author a spec with spec-creator,
#: (b) plan it with spec-planner, (c) build every task with spec-builder behind
#: BOTH gates, merging into the working tree (the integration tip). The workflow
#: writes its spec/plan/certificate artifacts under ``docs/`` (excluded from the
#: scored code diff); the CODE implementation lands in the package stubs.
A1_INSTRUCTION = (
    "You are driving the full spec-driven workflow to implement a feature in "
    "this repository non-interactively. The repository at /workspace is a "
    "skeleton with stub modules; the finished CODE must make the public API work "
    "end to end. Do not ask questions; this is a batch run with no user to "
    "prompt — make every default decision yourself and proceed.\n\n"
    "Carry out these three stages in order, using the named skills:\n"
    "1. Use the spec-creator skill to author a formal spec for the feature "
    "described below. Write the spec under docs/specs/.\n"
    "2. Use the spec-planner skill to decompose that spec into a dependency-"
    "ordered plan of task packages, each with a definition of done, and author "
    "one done-certificate per task. Write the plan folder under docs/plans/.\n"
    "3. Use the spec-builder skill to build every task in the plan in an "
    "isolated workspace, gating each through the semi-formal correctness review "
    "AND the validate-done-certificate completeness gate before merging it. "
    "Merge every completed task into the /workspace working tree — that working "
    "tree is the integration tip whose CODE will be scored.\n\n"
    "{timing_directive}\n\n"
    "When you finish, the package stubs under /workspace must be fully "
    "implemented and the spec/plan/certificate artifacts must exist under "
    "docs/. The feature to build:\n\n"
    "{problem_statement}"
)


def a1_prompt(problem_statement: str) -> str:
    """Return the full A1 orchestrating prompt for ``problem_statement``.

    The shared per-task :data:`~benchmark.harness.arms.a2_a3.TIMING_DIRECTIVE`
    is interpolated so spec-builder writes a per-task ``Elapsed:`` line into
    each certificate — the benchmark reads those back to populate
    ``ArtifactBundle.taskWallClocks`` and to compute the parallel-speedup
    metric the spec defines.
    """
    # Imported inside to avoid a module-level cycle (a2_a3 imports A1 constants
    # for the shared mount set and budget cap).
    from benchmark.harness.arms.a2_a3 import TIMING_DIRECTIVE

    return A1_INSTRUCTION.format(
        problem_statement=problem_statement,
        timing_directive=TIMING_DIRECTIVE,
    )
