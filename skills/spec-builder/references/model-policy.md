# Model & effort — the orchestrator's choice per role, and how to override it

spec-builder is the one skill in the spec-* family that actually **fans out** — it
dispatches a sub-agent per task and, by default, one more to verify it (two under
`gate_mode: split`). Each dispatch can carry its own model and reasoning effort.

**There are no pinned per-role defaults.** By default the **orchestrator chooses** the model
and effort for each role, using its judgment about that role and the plan in front of it; the
user can override any role. This file gives the orchestrator the reasoning to choose well and
the mechanics to carry the choice — the build loop, the sub-agent brief, and the orchestrator
all defer here.

---

## Choosing per role (the default is the orchestrator's judgment)

Pick per role by matching model strength to the role's **consequence** and **volume** — spend
capability where a wrong result is expensive, economize where the work is voluminous and
mechanical. These are considerations, not a fixed table:

- **Implementer** (per-task builder) — high volume (one per task), code-writing. The
  cost/throughput role: a solid mid-tier model at good effort is usually right. Step up to a
  stronger model or higher effort for a hard, high-risk, or retrying task — not for every task.
- **Verifier** — the gate: correctness (`semi-formal-review`) + completeness
  (`validate-done-certificate`), one agent by default or two under `gate_mode: split`. The
  load-bearing role: its verdict gates the merge, so favour the **most capable model available**
  at high effort. A wrong verdict is the expensive mistake; this is where to spend. (By default
  one verifier runs both halves over a single reading of the diff —
  [`combined-gate.md`](combined-gate.md).)
- **Orchestrator** (this top-level session) — coordination and bookkeeping (the DAG walk,
  merges, folder moves, status). It simply **inherits the session** — whatever the user
  launched spec-builder on.

Effort is the `low | medium | high | xhigh | max` scale; `high` is a sensible baseline for the
working roles, with `xhigh`/`max` as the "maximum reasoning / ultracode" ceiling when a run
needs it. A harder task, a repo flagged high-risk, or a failing-gate retry may warrant bumping
a role. The orchestrator picks concrete models for the actual plan and **states its choices
when it echoes the resolved settings** — the choice is visible, not silent.

## Overriding

An explicit user override wins, exactly like the other settings
([`orchestration.md`](orchestration.md) → *Configuration*) — set per role in
`.claude/spec-builder.local.md` or in the invocation: "build with the implementer on opus",
"run the gates at xhigh", "everything on sonnet". Resolve overrides over the orchestrator's
choices and echo the resolved model/effort per role back before dispatching.

---

## How the choice is carried — dispatch carries the model (and, on Workflow, the effort)

The dispatch that starts each role carries its model. spec-builder builds by dispatching
sub-agents through whatever the harness provides ([`portability.md`](portability.md)); the
enforcement strength depends on which:

- **On Claude Code, prefer the `Workflow` tool for the fan-out** — its `agent()` call takes
  **both** `model` and `effort`, so the chosen values are fully honoured. The orchestrator keeps
  its stateful DAG walk, integration point, and merges in its own control flow (it has a shell; a
  Workflow script does not); it uses Workflow only to run each scheduling batch's implement →
  verify chain at the per-role model/effort it resolved. The per-batch shape — one `pipeline()`
  over the currently-ready tasks, each carried through the two stages (implement, then verify)
  under Workflow's own concurrency cap, with the model/effort **variables** holding the
  orchestrator's choice (or the user's override) for each role:

  ```js
  // batch = the ready tasks this tick, capped at max_parallel_agents
  // implModel/implEffort and gateModel/gateEffort = the resolved per-role choices
  // (orchestrator's judgment, or user override) — NOT hard-coded model names.
  // gate_mode: combined (default) — implement, then ONE verifier returns both verdicts
  const results = await pipeline(
    batch,
    task         => agent(implementerBrief(task),        { model: implModel, effort: implEffort,
               label: `impl:${task.id}`,   phase: 'Implement' }),
    (impl, task) => agent(combinedGateBrief(task, impl), { model: gateModel, effort: gateEffort,
               label: `verify:${task.id}`, phase: 'Gate · verify' }),
  )
  // Under gate_mode: split, add the third stage back — gate 1 then gate 2, both at gateModel/gateEffort:
  //   (impl, task) => agent(reviewBrief(task, impl), { model: gateModel, effort: gateEffort, label:`review:${task.id}`,   phase:'Gate 1 · correctness' }),
  //   (rev,  task) => agent(validateBrief(task),     { model: gateModel, effort: gateEffort, label:`validate:${task.id}`, phase:'Gate 2 · completeness' }),
  // Workflow returns per-task verdicts + workspace refs; the orchestrator then MERGES the
  // CORRECT-and-DONE tasks into the integration point in reviewability order, moves them to
  // done/, tears down their workspaces, recomputes ready, and runs the next batch.
  ```

- **On any harness (the portable path — `Task`/`Agent` tool, or the sequential fallback):**
  set the sub-agent's **model** on the dispatch where the tool supports it (Claude Code's
  `Task`/`Agent` carries `model`); **effort** is not a dispatch parameter there, so the resolved
  effort is **advisory** — apply it at the session level or note it in the brief. When the
  orchestrator runs a gate itself via the Skill tool (see [`build-loop.md`](build-loop.md)),
  that gate runs on the session model; dispatch the gate as its own sub-agent when the chosen
  gate model matters.

Rules that hold on every path (see [`build-loop.md`](build-loop.md) and
[`orchestration.md`](orchestration.md)):

- **Workspaces stay on jj/git, provisioned by the orchestrator — not Workflow.** Do **not**
  use Workflow's `isolation:'worktree'`: it is git-only and would drop jj. The orchestrator
  creates each task's workspace from the current integration point *before* the batch
  (serially, so parallel `jj workspace add` calls cannot race — [`workspaces.md`](workspaces.md)),
  and passes the path into the implementer brief. The agent just edits files in the path it is
  given.
- **A separate agent runs the verification.** The combined verifier (default), or the reviewer
  and validator under `split`, are distinct dispatches from the implementer — the "never grade
  your own work" invariant holds by construction.
- **Failed-gate retries** (bounded, default 2) re-dispatch the implementer in the same
  workspace with the verdict as feedback, then re-run the gate. Parking to `blocked/` after the
  bound, and the `UNVERIFIED`-not-`UNSATISFIED` case, are unchanged.
- **Merges and folder moves stay with the orchestrator.** A wave's tasks are implemented+gated
  in parallel, then merged in reviewability order and moved to `done/` between batches;
  merge-conflict re-gating still applies. The whole DAG is **not** one pipeline — a task cannot
  start until its dependencies have merged, so the orchestrator loops batch-by-batch over the
  ready frontier rather than passing all tasks to a single call.
