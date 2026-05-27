---
name: spec-builder
description: Implement a spec-planner plan by dispatching one sub-agent per task in its own jj workspace, gating every task through a semi-formal correctness review and a definition-of-done validation before it is merged and marked Done. Walks the plan's dependency graph in waves — parallel by default (max 4 concurrent agents) or sequential — updating task and plan status as the build progresses. Triggers on "build this plan", "implement the plan", "execute the plan in docs/plans/...", "run the spec-builder", "build the tasks in parallel/sequentially", or handing a spec-planner plan folder over for implementation. Consumes docs/plans/YYYY-MM-DD-title/ (plan.md, NN-task.md files, optional certificates/); produces merged, reviewed, validated implementations with the plan folder kept current as a live board.
---

# Spec Builder

A skill for **executing** an implementation plan: turning a spec-planner plan folder into
merged, reviewed, validated code. Each task is built by its own sub-agent in its own jj
workspace, and no task reaches `Done` until it has passed two gates run by an agent other
than the one that built it — a semi-formal **correctness** review and a definition-of-done
**completeness** validation.

## Core principle

**A plan is executed task by task, and a task is only done when proven done — correct and
complete — by someone other than its builder.** spec-planner already did the hard thinking:
it decomposed the spec into reviewable task packages, ordered them for reviewability, and
wrote each one's definition of done (and, by default, a done certificate). spec-builder's
job is to *honour that structure* — build in dependency order, give each task exactly the
context its package names, and let the two gates decide done-ness, never the builder's
self-report.

Three rules follow:

1. **One sub-agent per task, in one isolated workspace.** Tasks are built in parallel where
   the graph allows it; isolation comes from jj workspaces, not from trust.
2. **Two gates, both mandatory, neither self-graded.** Correctness (semi-formal-review) and
   completeness (validate-done-certificate) both pass before a task merges. The implementer
   runs neither on its own work.
3. **The plan folder is the live board.** Task and plan `Status`, the checked-off steps, and
   the discharged certificates are kept current as the build runs, so progress is readable
   from the files and an interrupted build resumes from them.

## Relationship to the companion skills

spec-builder is the execution end of a four-skill pipeline:

- **spec-creator** writes the spec → **spec-planner** decomposes it into a task graph with a
  definition of done per task → **done-certificates** authors the per-task verification
  protocol → **spec-builder** (this skill) builds the tasks and discharges those protocols.
- It depends on three skills at build time:
  - **using-jj-workspaces** — creates and tears down the per-task isolated workspaces, and
    intercepts any git-worktree assumption in this jj repo. spec-builder delegates all
    workspace mechanics to it.
  - **semi-formal-review** (this plugin) — gate 1, correctness.
  - **validate-done-certificate** (this plugin) — gate 2, completeness; discharges the
    certificate done-certificates authored, or the DoD checklist when none exists.

It is **optimised for spec-planner plans** — it reads the dependency table as the source of
truth, the `Implements / Produces / Pointers / Steps / Definition of done` task fields, and
the `certificates/` subfolder. It can build a plan from another shape (a hand-written task
list, a checklist) only insofar as that source carries the same essentials: a dependency
order and a per-task definition of done. Missing those, send the user to spec-planner first.

## When to apply this skill

- A spec-planner plan exists and the user asks to **build, implement, or execute** it —
  "build the plan in docs/plans/…", "implement these tasks", "run the spec-builder".
- The user wants **sub-agent-driven implementation** of a planned feature with parallel or
  sequential execution and a concurrency cap.
- A partially-built plan needs **resuming** — pick up from the first non-`Done` task whose
  dependencies are met.

Skip or redirect when:

- **There is no plan** — only a spec. Point at **spec-planner** to produce the plan first;
  building straight from a spec skips the decomposition and ordering that make the build
  reviewable.
- **The change is a single trivial task** — a one-file edit with a three-line definition of
  done. Building it directly is faster than spinning up a workspace and two gates; say so.
- The request is to *write or change the spec* (spec-creator) or to *plan* it (spec-planner).

## Workflow

Five phases. The mechanics live in the three references — read them before the phase they back.

### Phase 1 — Load the plan and resolve settings

1. Locate the plan folder; confirm it is jj-managed (delegate detection to
   using-jj-workspaces). Read `plan.md`, every `NN-<task>.md`, and `certificates/` if present.
2. Resolve `execution_mode` and `max_parallel_agents` (defaults: parallel, 4) from any
   `.claude/spec-builder.local.md` and the invocation; echo the resolved settings back.
3. Build the schedule from the **dependency table** (the source of truth, not the Mermaid
   graph); sanity-check the DAG (no cycles, every dependency a real lower number); read each
   task's `Status` so already-`Done` tasks are treated as preconditions. See
   [`references/orchestration.md`](references/orchestration.md).

### Phase 2 — Establish the base and the integration revision

Create a clean shared base (`jj new`) and set the **integration revision** — the tip that
accumulates completed tasks — to it (or to a revision the user names). Confirm a green test
baseline before building, so later failures are attributable. (orchestration.md → *jj
workspace lifecycle*.)

### Phase 3 — Run the wave scheduler

Walk the graph with bounded concurrency (orchestration.md → *The wave scheduler*): dispatch
ready tasks up to `max_parallel_agents`, each into its own workspace branched from the
current integration revision, each via a context-sized brief
([`references/subagent-brief.md`](references/subagent-brief.md)). Dispatch a wave's
independent agents concurrently. Sequential mode is the same loop with the cap at 1.

### Phase 4 — Gate, merge, and update status per task

Each task runs the build loop ([`references/build-loop.md`](references/build-loop.md)):
implement → **gate 1: semi-formal-review** (correctness) → **gate 2: validate-done-certificate**
(completeness) → merge into the integration revision → mark `Done`. A failed gate re-dispatches
the implementer with the verdict as feedback, bounded by a small retry count; past that, the
task is parked and surfaced to the user. Update the task file `Status`, check off its steps,
let the validator write the certificate verdict, and recompute the ready set as each task lands.

### Phase 5 — Finish and report

When every task is `Done`, set `plan.md` `Status: Done`, confirm the integration revision
holds the whole build and the suite is green on it, and report the build summary: tasks
built, the review and validation verdict per task, any parked tasks and why, and where the
integrated work sits. Bookmarking/shipping the integration revision is the user's call —
offer it; do not push or land without being asked.

## What NOT to do

- **Don't let a builder grade its own work.** Both gates are run by a different agent. This
  is the rule the whole skill exists to enforce.
- **Don't mark a task `Done` on one gate, or on the implementer's self-report.** Correct and
  complete, both proven, then merge.
- **Don't lower the bar to force a green build.** A parked task honestly surfaced beats a
  falsely-`Done` one. Failures surface; they are not papered over.
- **Don't build from a spec with no plan.** Decomposition and ordering are spec-planner's
  job; without them the build is not reviewable. Redirect.
- **Don't hand-roll workspaces or ignore jj.** Delegate isolation to using-jj-workspaces;
  one workspace per task, branched from the integration revision, torn down after merge.
- **Don't over- or under-context a sub-agent.** Carry the task package's own fields and its
  dependencies' merged output (already in the workspace base) — not the whole repo, not the
  whole spec, not other tasks' files.
- **Don't ignore the dependency table.** It is the source of truth; if the Mermaid graph
  disagrees, the table wins and the discrepancy is noted.
- **Don't auto-resolve a conflict between "independent" tasks silently** — it may signal a
  missing edge in the plan; resolve it, re-gate the merged result, and flag it.

## Reference files

- [`references/orchestration.md`](references/orchestration.md) — Configuration (mode, max
  agents), reading the plan into a schedule, the bounded-concurrency wave scheduler, the jj
  workspace lifecycle and the accumulating integration revision, merge-conflict handling,
  and status bookkeeping. Read before Phases 1–3.
- [`references/subagent-brief.md`](references/subagent-brief.md) — How to assemble a
  context-sized brief from a task package, the implementer prompt template, brief sizing,
  and the narrower reviewer/validator briefs. Read before dispatching.
- [`references/build-loop.md`](references/build-loop.md) — The per-task lifecycle: implement,
  the two gates and their pass/fail rules, merge-and-mark-done, handling a failed gate
  (feedback, bounded retries, parking), and the invariants. Read before Phase 4.
