# Model & effort policy — which model runs each role, and how it is enforced

spec-builder is the one skill in the spec-* family that actually **fans out** — it
dispatches a sub-agent per task and two more per gate. That fan-out is where model and
reasoning-effort choices can be pinned to each role.

This file is the single source of truth for the role → model/effort mapping. The build
loop, the sub-agent brief, and the orchestrator all defer here.

---

## The policy

| Role | Model | Effort | Why |
|---|---|---|---|
| **Implementer** (per-task builder) | `sonnet` | `high` | Code-writing, high volume, one per task — the cost/throughput role. High effort keeps it careful without the top-tier price on every task. |
| **Reviewer** — gate 1, `semi-formal-review` | `fable` | `high` | Correctness is the load-bearing gate: certificate reasoning, function resolution, regression tracing. Run it on the most capable model — Fable 5 — so the verdict is as trustworthy as the pipeline can make it. |
| **Validator** — gate 2, `validate-done-certificate` | `fable` | `high` | Completeness is the other load-bearing gate: discharging obligations and tracing evidence. Same tier as the reviewer. |
| **Orchestrator** (this top-level session) | inherits the session | — | Coordination and bookkeeping — the DAG walk, merges, folder moves, status. It runs at whatever the user launched spec-builder on. |

Effort is the `low | medium | high | xhigh | max` scale; `high` is the default across these
roles (and the recommended default for Fable 5), with `xhigh`/`max` available as the
"maximum reasoning / ultracode" ceiling when a run needs it. A harder task, a repo the user
flags as high-risk, or a failing-gate retry may warrant bumping a role to `xhigh` (or the
implementer to `opus`/`fable`); treat the table as the default, not a ceiling.

An explicit invocation override wins, exactly like the other settings
([`orchestration.md`](orchestration.md) → *Configuration*): "build with the implementer on
opus", "run the gates at xhigh". Echo the resolved model/effort per role back alongside the
other settings before dispatching.

---

## How it is enforced — dispatch carries the model (and, on Workflow, the effort)

The dispatch that starts each role carries its model. spec-builder builds by dispatching
sub-agents through whatever the harness provides ([`portability.md`](portability.md)); the
enforcement strength depends on which:

- **On Claude Code, prefer the `Workflow` tool for the fan-out** — its `agent()` call takes
  **both** `model` and `effort`, so the policy is fully honoured. The orchestrator keeps its
  stateful DAG walk, integration point, and merges in its own control flow (it has a shell; a
  Workflow script does not); it uses Workflow only to run each scheduling batch's implement →
  gate 1 → gate 2 chain at the model/effort above. The per-batch shape — one `pipeline()` over
  the currently-ready tasks, each carried through the three stages under Workflow's own
  concurrency cap:

  ```js
  // batch = the ready tasks this tick, capped at max_parallel_agents
  const results = await pipeline(
    batch,
    task  => agent(implementerBrief(task), { model: 'sonnet', effort: 'high',
               label: `impl:${task.id}`, phase: 'Implement' }),
    (impl, task) => agent(reviewBrief(task, impl), { model: 'fable', effort: 'high',
               label: `review:${task.id}`, phase: 'Gate 1 · correctness' }),
    (rev,  task) => agent(validateBrief(task),     { model: 'fable', effort: 'high',
               label: `validate:${task.id}`, phase: 'Gate 2 · completeness' }),
  )
  // Workflow returns per-task verdicts + workspace refs; the orchestrator then MERGES the
  // CORRECT-and-DONE tasks into the integration point in reviewability order, moves them to
  // done/, tears down their workspaces, recomputes ready, and runs the next batch.
  ```

- **On any harness (the portable path — `Task`/`Agent` tool, or the sequential fallback):**
  set the sub-agent's **model** on the dispatch where the tool supports it (Claude Code's
  `Task`/`Agent` carries `model`); **effort** is not a dispatch parameter there, so the policy
  effort is **advisory** — apply it at the session level or note it in the brief. When the
  orchestrator runs a gate itself via the Skill tool (see [`build-loop.md`](build-loop.md)),
  that gate runs on the session model; dispatch the gate as its own sub-agent when the `fable`
  model matters.

Rules that hold on every path (see [`build-loop.md`](build-loop.md) and
[`orchestration.md`](orchestration.md)):

- **Workspaces stay on jj/git, provisioned by the orchestrator — not Workflow.** Do **not**
  use Workflow's `isolation:'worktree'`: it is git-only and would drop jj. The orchestrator
  creates each task's workspace from the current integration point *before* the batch
  (serially, so parallel `jj workspace add` calls cannot race — [`workspaces.md`](workspaces.md)),
  and passes the path into the implementer brief. The agent just edits files in the path it is
  given.
- **A separate agent runs each gate.** The reviewer and validator are distinct dispatches from
  the implementer — the "never grade your own work" invariant holds by construction.
- **Failed-gate retries** (bounded, default 2) re-dispatch the implementer in the same
  workspace with the verdict as feedback, then re-run the gate. Parking to `blocked/` after the
  bound, and the `UNVERIFIED`-not-`UNSATISFIED` case, are unchanged.
- **Merges and folder moves stay with the orchestrator.** A wave's tasks are implemented+gated
  in parallel, then merged in reviewability order and moved to `done/` between batches;
  merge-conflict re-gating still applies. The whole DAG is **not** one pipeline — a task cannot
  start until its dependencies have merged, so the orchestrator loops batch-by-batch over the
  ready frontier rather than passing all tasks to a single call.
