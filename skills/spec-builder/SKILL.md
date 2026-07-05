---
name: spec-builder
description: Implement a spec-planner plan by dispatching one sub-agent per task in its own isolated workspace (jj or git, jj preferred), gating every task through a semi-formal correctness review and a definition-of-done validation before it is merged and marked Done. Self-contained — workspace isolation is vendored, no other plugin required. Walks the dependency graph in waves, parallel by default (max 4 agents) or sequential. Triggers on "build this plan", "implement the plan", "execute the plan in .specs/plans/...", or handing a spec-planner plan folder over for implementation.
compatibility: Needs a harness that can dispatch sub-agents — Claude Code or OpenCode (core Task tool), or Pi with a subagents extension (e.g. @tintinweb/pi-subagents). Without one, runs a sequential single-agent fallback (references/portability.md).
---

# Spec Builder

A skill for **executing** an implementation plan: turning a spec-planner plan folder into
merged, reviewed, validated code. Each task is built by its own sub-agent in its own jj
workspace, and no task reaches `Done` until an agent other than the one that built it has
proven it **correct** (a semi-formal review) and **complete** (a definition-of-done
validation) — by default in one combined verification gate, or as two separate gates under
`gate_mode: split`.

## Core principle

**A plan is executed task by task, and a task is only done when proven done — correct and
complete — by someone other than its builder.** spec-planner already did the hard thinking:
it decomposed the spec into reviewable task packages, ordered them for reviewability, and
wrote each one's definition of done (and, by default, a done certificate). spec-builder's
job is to *honour that structure* — build in dependency order, give each task exactly the
context its package names, and let the gates decide done-ness, never the builder's
self-report.

Three rules follow:

1. **One sub-agent per task, in one isolated workspace.** Tasks are built in parallel where
   the graph allows it; isolation comes from per-task workspaces (jj or git), not from trust.
2. **Two proofs, both mandatory, neither self-graded.** Correctness (semi-formal-review) and
   completeness (validate-done-certificate) both pass before a task merges — by default proven
   by one verification gate in a single context, or by two separate gates under
   `gate_mode: split`. The implementer runs neither on its own work.
3. **The plan folder is a board of folders.** Tasks move between `backlog/`, `in-progress/`,
   `blocked/`, and `done/` as their status changes — the task file and its co-located
   certificate move together — and `plan.md`'s plan-level `Status` is recomputed from the
   subfolder union. Progress is `ls`-legible and an interrupted build resumes from folder
   membership.

## Relationship to the companion skills

spec-builder is the execution end of a three-plugin pipeline (spec-creator → spec-planner → spec-builder):

- **spec-creator** writes the spec → **spec-planner** decomposes it into a task graph with a
  definition of done per task, and its **done-certificates** skill authors the per-task
  verification protocol → **spec-builder** (this skill) builds the tasks and discharges those
  protocols. (done-certificates ships inside the spec-planner plugin, not as a separate one.)
- It is **self-contained** — it needs no other plugin installed. Workspace isolation is
  vendored into this skill at [`references/workspaces.md`](references/workspaces.md),
  covering both backends:
  - **Workspace isolation (jj or git)** — creates and tears down the per-task isolated
    workspaces. jj (jujutsu) is preferred when a repo supports both (a colocated repo);
    plain git repos use git worktrees. The standalone `jj-workspaces` skill is a richer
    companion when installed, but not required.
  - **semi-formal-review** (this plugin) — the correctness method.
  - **validate-done-certificate** (this plugin) — the completeness method; discharges the
    certificate done-certificates authored, or the DoD checklist when none exists.
  - By default a single **verification gate** runs both over one reading of the diff
    ([`references/combined-gate.md`](references/combined-gate.md)), for token efficiency;
    `gate_mode: split` runs them as two separate agents.

It is **optimised for spec-planner plans** — it reads the dependency table (keyed by task
number) as the source of truth, the `Implements / Produces / Pointers / Steps / Definition of
done` task fields, and the `**Layout:** kanban` marker (or a `backlog/` subfolder) that
distinguishes a kanban plan from a legacy-flat one. A task carries **no `Status` field** — its
status is the subfolder it sits in. It can build a plan from another shape (a hand-written
task list, a checklist) only insofar as that source carries the same essentials: a dependency
order and a per-task definition of done. Missing those, send the user to spec-planner first.

## When to apply this skill

- A spec-planner plan exists and the user asks to **build, implement, or execute** it —
  "build the plan in .specs/plans/…", "implement these tasks", "run the spec-builder".
- The user wants **sub-agent-driven implementation** of a planned feature with parallel or
  sequential execution and a concurrency cap.
- A partially-built plan needs **resuming** — pick up from the first non-`Done` task whose
  dependencies are met.

Skip or redirect when:

- **There is no plan** — only a spec. Point at **spec-planner** to produce the plan first;
  building straight from a spec skips the decomposition and ordering that make the build
  reviewable.
- **The change is a single trivial task** — a one-file edit with a three-line definition of
  done. Building it directly is faster than spinning up a workspace and a verification gate; say so.
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

Five phases. The mechanics live in the references — read them before the phase they back.

### Preflight — confirm sub-agent dispatch is available

This skill builds by dispatching a sub-agent per task. Before Phase 3, confirm the
harness can do that — gate on the **capability**, not on which harness you are in
(there is no reliable runtime harness-detection signal, and you don't need one):

- Check your own toolset for a sub-agent dispatch tool — `Task` (Claude Code,
  OpenCode) or `Agent` (Pi + a subagents extension) or an equivalent. Match on
  capability, not one exact name.
- **Present** → proceed with the parallel, gated build below.
- **Absent** → you are most likely in Pi without a subagents extension. Do **not**
  fake parallelism or let the builder grade its own work. Offer the user the
  install path (`pi install npm:@tintinweb/pi-subagents`, then reload Pi) or the
  sequential single-agent fallback that still runs the verification (correctness and
  completeness) in-context — see
  [`references/portability.md`](references/portability.md). State which mode ran.

### Phase 1 — Load the plan and resolve settings

1. Locate the plan folder; detect the VCS backend and pick it — jj if present (preferred,
   even in a colocated repo), else git ([`references/workspaces.md`](references/workspaces.md));
   announce the choice. **Detect the layout:** a `**Layout:** kanban` marker in `plan.md` (or a
   `backlog/` subfolder) means kanban — enumerate the task set as the **union** of `backlog/`,
   `in-progress/`, `blocked/`, and `done/` (a missing subfolder is empty) and read `plan.md`
   plus every `NN-<task>.md` with its co-located `NN-<task>-certificate.md`. A plan with
   **neither** marker nor `backlog/` — task files flat at the folder root — is **legacy-flat**:
   migrate it in place before building (create the subfolders, move each task by its
   `**Status:**` value — `Done`→`done/`, `In progress`→`in-progress/`, anything else→`backlog/` —
   relocate each `certificates/NN-*.md` to a co-located `NN-*-certificate.md`, drop the per-task
   `Status` field, and stamp `**Layout:** kanban`; see
   [`references/orchestration.md`](references/orchestration.md) → *Migrating a legacy-flat plan*).
   **Check `plan.md` `Status` before building:** a `Draft` plan has not been agreed — confirm
   the decomposition and order with the user and promote it to `Accepted` before dispatching
   any task. `Accepted` proceeds. `In progress` resumes from folder membership. `Done` is
   already built — say so rather than rebuilding. (spec-planner emits `Draft`; spec-builder
   owns the `Draft → Accepted` promotion at this handoff.)
2. Resolve `execution_mode`, `max_parallel_agents`, and `gate_mode` (defaults: parallel, 4,
   combined) from any `.claude/spec-builder.local.md` and the invocation; echo the resolved
   settings back. Resolve the **per-role model and effort** the same way — but with no pinned
   defaults: by default the orchestrator chooses each role's model/effort by its own judgment
   ([`references/model-policy.md`](references/model-policy.md)), overridable per role/run; echo
   the resolved choices back too.
3. Build the schedule from the **dependency table** (the source of truth, not the Mermaid
   graph), keyed by task number; sanity-check the DAG (no cycles, every dependency a real lower
   number); treat tasks already in `done/` as preconditions. See
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
independent agents concurrently, each at the model/effort the orchestrator resolved for it
([`references/model-policy.md`](references/model-policy.md)) — on Claude Code prefer a single
`Workflow` call per batch (it carries model **and** effort); on the portable `Task`/`Agent`
path set the model per dispatch and treat effort as advisory. Sequential mode is the same
loop with the cap at 1.

### Phase 4 — Gate, merge, and move per task

Each task runs the build loop ([`references/build-loop.md`](references/build-loop.md)):
implement → **verify** (correctness + completeness — one combined gate by default
([`references/combined-gate.md`](references/combined-gate.md)), or two gates under
`gate_mode: split`) → merge into the integration point → move the task into `done/`. A failed gate
re-dispatches the implementer with the verdict as feedback, bounded by a small retry count;
past that, the task is parked — moved into `blocked/` with a `**Blocked:** <reason>` line — and
surfaced to the user. The orchestrator moves the task file and its certificate between
subfolders on the main tree, checks off its steps, lets the validator write the certificate
verdict, recomputes `plan.md`'s `Status` from the subfolders, and recomputes the ready set as
each task lands.

### Phase 5 — Finish and report

When every task is in `done/`, `plan.md`'s recomputed `Status` is `Done`; confirm the integration point
holds the whole build and the suite is green on it, and report the build summary: tasks
built, the review and validation verdict per task, any parked tasks and why, and where the
integrated work sits. Shipping it — a jj bookmark, or merging the git integration branch
into the target — is the user's call; offer it, but do not push or land without being asked.

**Close the loop back to the spec.** The gates prove each task is correct and complete
against its *own* definition of done — they do **not** re-check the integrated code against
the source spec. Whether the spec is faithfully implemented rests on the plan's coverage
(spec-planner's Phase 5 maps every in-scope spec section to a task) plus each DoD encoding
that section's intent. A silently under-covered spec is invisible to this build. So at
finish, **offer a spec-conformance pass** over the integrated result — `spec-reviewer` R2
(canonical spec) or R3 (change spec) when the spec-creator plugin is available, else a manual
read of the spec against the merged code. Note in the summary that this reconciliation is the
user's to run; it is outside the per-task gates.

## What NOT to do

- **Don't let a builder grade its own work.** The verification — combined or split — is run
  by a different agent. This is the rule the whole skill exists to enforce.
- **Don't fake parallelism when the harness can't dispatch sub-agents.** If no dispatch tool
  is present (typically Pi without a subagents extension), take the documented fallback in
  [`references/portability.md`](references/portability.md) and say which mode ran — don't
  pretend gates were run by a separate agent when they weren't.
- **Don't mark a task `Done` on one verdict, or on the implementer's self-report.** Correct and
  complete, both proven, then merge.
- **Don't lower the bar to force a green build.** A parked task honestly surfaced beats a
  falsely-`Done` one. Failures surface; they are not papered over.
- **Don't build from a spec with no plan.** Decomposition and ordering are spec-planner's
  job; without them the build is not reviewable. Redirect.
- **Don't ignore the dependency table.** It is the source of truth; if the Mermaid graph
  disagrees, the table wins and the discrepancy is noted.
- **Don't hand-roll the mechanics.** Workspace commands (workspaces.md), sub-agent brief
  sizing (subagent-brief.md), and merge-conflict handling (orchestration.md) each carry a
  method and a *Common mistakes* coda in their reference — follow them rather than improvising.
  In particular, never auto-resolve a conflict between "independent" tasks silently: it may
  signal a missing plan edge, so resolve it, re-gate the merged result, and flag it.

## Reference files

- [`references/orchestration.md`](references/orchestration.md) — Configuration (mode, max
  agents), reading the plan into a schedule, the bounded-concurrency wave scheduler, the
  backend-neutral workspace lifecycle and the accumulating integration point, merge-conflict
  handling, and status bookkeeping. Read before Phases 1–3.
- [`references/model-policy.md`](references/model-policy.md) — How the orchestrator **chooses**
  each role's model and reasoning effort (implementer, the verifier gate(s), orchestrator) and
  how the user overrides it, plus how dispatch carries the choice — `Workflow` batch dispatch on
  Claude Code (model + effort), the portable `Task`/`Agent` fallback (model set, effort
  advisory). Read before Phase 3.
- [`references/workspaces.md`](references/workspaces.md) — The vendored, self-contained
  workspace-isolation method for **both backends**: detection (jj preferred, else git),
  sibling directory selection, the per-workspace commands, the baseline test run, merging
  and teardown, and an operation-mapping table (concept → jj → git). Read before Phase 2.
- [`references/subagent-brief.md`](references/subagent-brief.md) — How to assemble a
  context-sized brief from a task package, the implementer prompt template, brief sizing,
  and the verifier brief (combined by default, or the split reviewer/validator briefs). Read
  before dispatching.
- [`references/build-loop.md`](references/build-loop.md) — The per-task lifecycle: implement,
  the verification gate and its pass/fail rules, merge-and-mark-done, handling a failed gate
  (feedback, bounded retries, parking), and the invariants. Read before Phase 4.
- [`references/combined-gate.md`](references/combined-gate.md) — The default single-context
  verification gate: one agent, one reading of the diff, both verdicts; the merged protocol
  (shared checkpoints once, then correctness and completeness), the dual-verdict output, and
  the `gate_mode: combined | split` knob — what the merge preserves and what it relaxes. Read
  before Phase 4.
- [`references/portability.md`](references/portability.md) — Which harnesses can dispatch
  sub-agents (Claude Code, OpenCode, Pi-with-extension), the capability gate, and the
  sequential single-agent fallback when no dispatch tool is present. Read at Preflight.
