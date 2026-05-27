---
name: spec-builder
description: Implement a spec-planner plan by dispatching one sub-agent per task in its own isolated workspace, gating every task through a semi-formal correctness review and a definition-of-done validation before it is merged and marked Done. Isolation works on jj or git repos (jj preferred when both exist), vendored self-contained so the plugin needs no other plugin installed. Walks the plan's dependency graph in waves — parallel by default (max 4 concurrent agents) or sequential — updating task and plan status as the build progresses. Triggers on "build this plan", "implement the plan", "execute the plan in docs/plans/...", "run the spec-builder", "build the tasks in parallel/sequentially", or handing a spec-planner plan folder over for implementation. Consumes docs/plans/YYYY-MM-DD-title/ (plan.md, NN-task.md files, optional certificates/); produces merged, reviewed, validated implementations with the plan folder kept current as a live board.
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
   the graph allows it; isolation comes from per-task workspaces (jj or git), not from trust.
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
- It is **self-contained** — it needs no other plugin installed. Workspace isolation is
  vendored into this skill at [`references/workspaces.md`](references/workspaces.md),
  covering both backends:
  - **Workspace isolation (jj or git)** — creates and tears down the per-task isolated
    workspaces. jj (jujutsu) is preferred when a repo supports both (a colocated repo);
    plain git repos use git worktrees. The standalone `jj-workspaces` skill is a richer
    companion when installed, but not required.
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

**Expect manual sign-off on visually-reviewable tasks.** Every task's definition of done ends
in a `Reviewable:` line, and its certificate makes that the final obligation — the validator
must *exercise* the action and *observe* the result. When the reviewable surface is visual (a
running UI, a screen that renders), a headless validator cannot produce that evidence: the
obligation is `UNVERIFIED`, the completeness gate returns `PARTIAL`, and the build loop surfaces
the task for the user to verify by hand (see [`references/build-loop.md`](references/build-loop.md)
→ *Handling a failed gate*, the `UNVERIFIED`-not-`UNSATISFIED` case). This is correct behaviour,
not a failure — but it means a UI-heavy plan is **not** built hands-off: spec-builder will pause
for manual review on those tasks. Say so up front so the user knows where the build will stop.

## Workflow

Five phases. The mechanics live in the three references — read them before the phase they back.

### Phase 1 — Load the plan and resolve settings

1. Locate the plan folder; detect the VCS backend and pick it — jj if present (preferred,
   even in a colocated repo), else git ([`references/workspaces.md`](references/workspaces.md));
   announce the choice. Read `plan.md`, every `NN-<task>.md`, and `certificates/` if present.
   **Check `plan.md` `Status` before building:** a `Draft` plan has not been agreed — confirm
   the decomposition and order with the user and promote it to `Accepted` before dispatching
   any task. `Accepted` proceeds. `In progress` resumes from the task statuses. `Done` is
   already built — say so rather than rebuilding. (spec-planner emits `Draft`; spec-builder
   owns the `Draft → Accepted` promotion at this handoff.)
2. Resolve `execution_mode` and `max_parallel_agents` (defaults: parallel, 4) from any
   `.claude/spec-builder.local.md` and the invocation; echo the resolved settings back.
3. Build the schedule from the **dependency table** (the source of truth, not the Mermaid
   graph); sanity-check the DAG (no cycles, every dependency a real lower number); read each
   task's `Status` so already-`Done` tasks are treated as preconditions. See
   [`references/orchestration.md`](references/orchestration.md).

### Phase 2 — Establish the base and the integration point

Create a clean shared base and set the **integration point** — the tip that accumulates
completed tasks (a jj revision, or the `spec-builder/integration` git branch) — to it (or
to a revision/ref the user names). Confirm a green test baseline before building, so later
failures are attributable. (orchestration.md → *Workspace lifecycle*; commands in
[`references/workspaces.md`](references/workspaces.md).)

### Phase 3 — Run the wave scheduler

Walk the graph with bounded concurrency (orchestration.md → *The wave scheduler*): dispatch
ready tasks up to `max_parallel_agents`, each into its own workspace branched from the
current integration point, each via a context-sized brief
([`references/subagent-brief.md`](references/subagent-brief.md)). Dispatch a wave's
independent agents concurrently. Sequential mode is the same loop with the cap at 1.

### Phase 4 — Gate, merge, and update status per task

Each task runs the build loop ([`references/build-loop.md`](references/build-loop.md)):
implement → **gate 1: semi-formal-review** (correctness) → **gate 2: validate-done-certificate**
(completeness) → merge into the integration point → mark `Done`. A failed gate re-dispatches
the implementer with the verdict as feedback, bounded by a small retry count; past that, the
task is parked and surfaced to the user. Update the task file `Status`, check off its steps,
let the validator write the certificate verdict, and recompute the ready set as each task lands.

### Phase 5 — Finish and report

When every task is `Done`, set `plan.md` `Status: Done`, confirm the integration point
holds the whole build and the suite is green on it, and report the build summary: tasks
built, the review and validation verdict per task, any parked tasks and why, and where the
integrated work sits. Shipping it — a jj bookmark, or merging the git integration branch
into the target — is the user's call; offer it, but do not push or land without being asked.

**Close the loop back to the spec.** The two gates prove each task is correct and complete
against its *own* definition of done — they do **not** re-check the integrated code against
the source spec. Whether the spec is faithfully implemented rests on the plan's coverage
(spec-planner's Phase 5 maps every in-scope spec section to a task) plus each DoD encoding
that section's intent. A silently under-covered spec is invisible to this build. So at
finish, **offer a spec-conformance pass** over the integrated result — `spec-reviewer` R2
(canonical spec) or R3 (change spec) when the spec-creator plugin is available, else a manual
read of the spec against the merged code. Note in the summary that this reconciliation is the
user's to run; it is outside the per-task gates.

## What NOT to do

- **Don't let a builder grade its own work.** Both gates are run by a different agent. This
  is the rule the whole skill exists to enforce.
- **Don't mark a task `Done` on one gate, or on the implementer's self-report.** Correct and
  complete, both proven, then merge.
- **Don't lower the bar to force a green build.** A parked task honestly surfaced beats a
  falsely-`Done` one. Failures surface; they are not papered over.
- **Don't build from a spec with no plan.** Decomposition and ordering are spec-planner's
  job; without them the build is not reviewable. Redirect.
- **Don't hand-roll workspace commands.** Follow the vendored method in workspaces.md
  (jj preferred, git supported); one workspace per task, branched from the integration
  point, torn down after merge.
- **Don't over- or under-context a sub-agent.** Carry the task package's own fields and its
  dependencies' merged output (already in the workspace base) — not the whole repo, not the
  whole spec, not other tasks' files.
- **Don't ignore the dependency table.** It is the source of truth; if the Mermaid graph
  disagrees, the table wins and the discrepancy is noted.
- **Don't auto-resolve a conflict between "independent" tasks silently** — it may signal a
  missing edge in the plan; resolve it, re-gate the merged result, and flag it.

## Reference files

- [`references/orchestration.md`](references/orchestration.md) — Configuration (mode, max
  agents), reading the plan into a schedule, the bounded-concurrency wave scheduler, the
  backend-neutral workspace lifecycle and the accumulating integration point, merge-conflict
  handling, and status bookkeeping. Read before Phases 1–3.
- [`references/workspaces.md`](references/workspaces.md) — The vendored, self-contained
  workspace-isolation method for **both backends**: detection (jj preferred, else git),
  sibling directory selection, the per-workspace commands, the baseline test run, merging
  and teardown, and an operation-mapping table (concept → jj → git). Read before Phase 2.
- [`references/subagent-brief.md`](references/subagent-brief.md) — How to assemble a
  context-sized brief from a task package, the implementer prompt template, brief sizing,
  and the narrower reviewer/validator briefs. Read before dispatching.
- [`references/build-loop.md`](references/build-loop.md) — The per-task lifecycle: implement,
  the two gates and their pass/fail rules, merge-and-mark-done, handling a failed gate
  (feedback, bounded retries, parking), and the invariants. Read before Phase 4.
