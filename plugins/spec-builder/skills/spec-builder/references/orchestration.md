# Orchestration — scheduling, workspaces, configuration

How the spec-builder parent session schedules tasks, isolates each in a jj workspace,
and accumulates completed work. The unit of execution is the **task package** from a
spec-planner plan folder; the unit of isolation is the **jj workspace** (one per task in
flight); the rule that orders everything is the plan's **dependency table**.

---

## Configuration

Two knobs, with defaults, resolved in this order (later wins):

1. **Defaults:** `execution_mode: parallel`, `max_parallel_agents: 4`.
2. **Project config file** (optional): `.claude/spec-builder.local.md`, YAML frontmatter:
   ```yaml
   ---
   execution_mode: parallel        # parallel | sequential
   max_parallel_agents: 4          # ignored when sequential
   workspace_layout: sibling       # sibling | grouped (see workspaces.md)
   ---
   ```
   Read it with the `plugin-settings` pattern if present; create it only if the user asks
   to persist a preference.
3. **The invocation** — an explicit request ("build sequentially", "max 2 agents at a
   time") overrides both for this run. Echo the resolved settings back before starting so
   the user can correct them.

`sequential` is `parallel` with `max_parallel_agents = 1` and strict one-at-a-time
ordering; the build loop is otherwise identical. Choose sequential when the repo's tests
are stateful/serial, when tasks share files heavily, or when the user wants to watch each
task land before the next starts.

---

## Reading the plan into a schedule

1. **Locate the plan folder.** `docs/plans/YYYY-MM-DD-<title>/` for a repo-wide plan, or `docs/<package>/plans/YYYY-MM-DD-<title>/` (or a co-located `<package-location>/docs/plans/…`) for a package-scoped one. If the user named a plan,
   use it; if several exist, list them and ask which. The folder holds `plan.md`, the
   `NN-<task>.md` files, and (when authored) `certificates/NN-<task>.md`.
2. **Parse the dependency table in `plan.md` — it is the source of truth**, not the Mermaid
   graph. Each row gives a task `NN`, its `Depends on` set, the edge kind, and what it
   produces. Build the DAG from the table. If the Mermaid graph disagrees, the table wins;
   note the discrepancy.
3. **Read every task's `Status`.** The folder is a live board: a task already `Done` is a
   precondition, not work — skip it and treat its output as already integrated. Resume a
   partially-built plan by starting from the first non-`Done` task whose deps are met.
4. **Sanity-check the DAG.** Every `Depends on` references a real, lower task number; there
   is no cycle. A cycle or a dangling dependency is a plan defect — stop and surface it
   rather than guessing an order.

---

## The wave scheduler

A bounded-concurrency topological walk. Maintain three sets: `done`, `running`, `ready`.

```
ready   = tasks whose Depends-on ⊆ done, not yet running or done
running = tasks dispatched to a sub-agent, not yet resolved
done    = tasks marked Done (both gates passed) and merged into the integration point
```

Loop until every task is `done`:

1. While `|running| < max_parallel_agents` and `ready` is non-empty, pop the **highest-
   reviewability** ready task (follow the plan's implementation order — lowest `NN` first,
   since the plan already numbered in reviewability order) and dispatch it (see
   [`build-loop.md`](build-loop.md)). Move it `ready → running`.
2. When a running task resolves:
   - **Both gates pass →** merge its workspace into the integration point, mark it
     `done`, update its task `Status` to `Done`, recompute `ready` (newly-unblocked tasks),
     and tear down its workspace.
   - **A gate fails →** handle per [`build-loop.md`](build-loop.md) (re-dispatch with the
     verdict as feedback, up to a small retry bound; then surface to the user). Keep it
     `running` across a retry; move it out only when it lands or is parked.
3. If `ready` and `running` are both empty but tasks remain, the schedule is stuck — a
   dependency on a parked/failed task. Report which tasks are blocked on what and stop.

In **sequential** mode `max_parallel_agents = 1`, so step 1 dispatches exactly one task
and the loop fully resolves it (including merge) before the next — the same code path.

Dispatch the independent sub-agents of one wave **concurrently** (multiple Agent calls in
a single message), not one after another, so the wave actually runs in parallel.

---

## Workspace lifecycle

Isolation runs on either backend — **jj (preferred) or git** — using the vendored,
self-contained method in [`workspaces.md`](workspaces.md): backend detection (jj first,
so a colocated repo uses jj), sibling directory selection, the per-workspace commands, the
baseline test run, and teardown. Read it for the commands; this section covers only how
spec-builder *uses* workspaces across the wave, in backend-neutral terms.

### Integration point — the accumulating tip

spec-builder keeps one **integration point**: the running tip that holds every task merged
`done` so far — a **jj revision** on the jj backend, the **`spec-builder/integration`
branch** tip on the git backend. It starts at the plan's clean base (after `jj new`, or on
a clean integration branch) — or at a revision/ref the user names — and advances each time
a task is merged.

- **Branching a task's workspace.** A task's workspace must start from a base that already
  contains its dependencies' work, so create it from the **current integration point**
  (`jj workspace add -r <int>` / `git worktree add -b spec-builder/task-NN … spec-builder/integration`).
  The sub-agent then sees exactly the code its `Depends on` tasks produced — no more, no less.
- **Parallel tasks in one wave** share the same integration point as their base (the ready
  set guarantees they don't depend on each other), so they branch from the same tip and
  cannot see each other's in-flight edits.
- **Merging a completed task.** Once both gates pass, fold the workspace into the
  integration tip (`jj new`/`jj rebase` / `git merge --no-ff`) and advance the integration
  point to the result. Because parallel tasks branched from the *same* base, the second and
  later merges of a wave land on a tip that already moved; usually clean, but see below.
- **Tearing down.** After a successful merge, unregister and remove the workspace; after an
  abandoned attempt, drop its revision/branch first. Exact commands in [`workspaces.md`](workspaces.md).

### Merge conflicts between parallel tasks

Two parallel tasks that the plan declared independent can still touch the same file. When
merging the second one conflicts:

1. Do **not** silently auto-resolve. A conflict between tasks the plan called independent
   is signal — the decomposition may have a missing edge.
2. Resolve in a dedicated step (the orchestrator, or a sub-agent briefed with both diffs
   and the conflict), then **re-run both gates** on the merged result for the later task —
   a clean per-workspace review does not cover the merge.
3. Note the conflict in the build log and consider flagging the missing dependency edge
   back to the plan (an `Open question` for a spec-planner pass).

### Stale working copy (jj backend)

If a merge rewrote a revision another jj workspace was editing, that workspace's next `jj`
command reports it stale. Resolve with `jj workspace update-stale` — never force-reset; jj
preserves prior state in a recovery commit if needed. On the git backend this does not
arise: a worktree's branch is locked to it and is not rewritten underneath it.

---

## Status bookkeeping (the plan is the live board)

The plan folder *is* the build's state. Keep it current so the build is resumable and the
user can read progress from the files alone:

- **Task file `Status`:** `Todo → In progress` on dispatch; check off `- [ ]` step items as
  the sub-agent reports them; `→ Done` only when both gates pass and the work is merged.
  On a failed gate it stays `In progress` (with a note), never silently `Done`.
- **`plan.md` `Status`:** spec-planner hands the plan over as `Draft`; spec-builder owns the
  `Draft → Accepted` promotion — confirm the decomposition with the user, then set `Accepted`
  before the first dispatch. From there: `Accepted → In progress` when the first task is
  dispatched; `→ Done` only when **every** task file is `Done`. Leave it `In progress` if any
  task is parked. A plan already `In progress` is resumed, not re-promoted.
- **Certificate `State`** (when one exists): the validator sets it to `Validated
  YYYY-MM-DD` with the derived verdict — that is validate-done-certificate's write, not
  the orchestrator's.
- **Build log.** Keep a short running log (per task: dispatched, review verdict, validation
  verdict, merged / parked, retries). Surface it at the end as the build summary.

Resuming an interrupted build is just re-reading these statuses: `done` = task files
already `Done`, and the scheduler restarts from the current `ready` set.
