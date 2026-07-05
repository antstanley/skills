# Build loop — the per-task lifecycle

What happens to a single task from dispatch to `Done`. The scheduler in
[`orchestration.md`](orchestration.md) decides *which* tasks run and *when*; this file is
what each running task goes through. Every task is proven **correct and complete** before it
is merged, and the implementer never runs that verification on its own work. By default one
combined gate proves both in a single context ([`combined-gate.md`](combined-gate.md)); under
`gate_mode: split` the two gates run as separate agents, correctness then completeness.

```
ready ─► implement ─► verify: correctness + completeness ─► merge ─► done
            ▲                        │ (BUGGY/CONCERNS or PARTIAL/NOT_DONE)
            └────────────────────────┘  feedback, re-dispatch (bounded)
```

---

## Step 1 — Implement (sub-agent, isolated)

1. Create the task's workspace from the current integration point (orchestration.md →
   *Integration point*; commands in workspaces.md) so the builder's base holds its
   dependencies' work.
2. Assemble the brief from the task file ([`subagent-brief.md`](subagent-brief.md)) and
   dispatch the implementer at its policy model/effort — `sonnet` at `high` by default
   ([`model-policy.md`](model-policy.md)) — into the workspace. Move the task —
   `backlog/NN-*.md` and its `NN-*-certificate.md` — into `in-progress/`, on the main tree.
3. The sub-agent builds only this task, runs the repo's test/lint commands in its
   workspace, and reports back: files changed, how each DoD item is met, command results,
   and anything incomplete. It does **not** mark the task done.

The implementer's report is input to the gates, not a verdict. A sub-agent claiming "all
done, tests pass" is a claim the gates exist to check.

## Step 2 — Verify: correctness and completeness

Verify the workspace diff by an agent that is **not** the implementer, at the gate
model/effort — `fable` at `high` ([`model-policy.md`](model-policy.md)). How many agents run
it is the `gate_mode` knob ([`orchestration.md`](orchestration.md) → *Configuration*):

- **`combined` (default) — one gate, one context.** Dispatch a single verifier that reads the
  diff once and returns both verdicts, per [`combined-gate.md`](combined-gate.md). It runs the
  shared checkpoints (function resolution, execution trace, regression) once and derives the
  correctness verdict and the completeness discharge off that one reading — the token-efficient
  path, since the two gates otherwise iterate the same code twice.
- **`split` — two gates, two contexts.** Gate 1 (`semi-formal-review`) runs first; only if it
  passes does gate 2 (`validate-done-certificate`) run, each by a separate agent (or the
  orchestrator via the Skill tool — dispatch it as its own sub-agent when the `fable` model
  matters, since a gate the orchestrator runs itself uses the session model). Choose it when
  reviewer≠validator independence is worth the extra tokens — a high-risk plan, or a retry you
  distrust.

Either way the gate produces the **same two verdicts**:

- **Correctness** — `CORRECT | LIKELY_CORRECT | CONCERNS | BUGGY`, from the diff plus the
  task's `Produces` and `Steps` (what it was meant to do). **Pass:** `CORRECT` or
  `LIKELY_CORRECT`.
- **Completeness** — `DONE | PARTIAL | NOT_DONE`, from the diff, the task's `Definition of
  done`, and its co-located `in-progress/NN-<task>-certificate.md` if it exists — read from the
  **main tree**, never a sub-agent's workspace copy. With a certificate, discharge it; without
  one, derive obligations from the DoD (the protocol's no-certificate fallback). The verdict,
  obligation statuses, and `State: Validated …` are written into the certificate. **Pass:** `DONE`.

**Both must pass = correct and complete.** Either alone is insufficient: a `CORRECT` diff that
is `PARTIAL` does the wrong scope well; a `DONE` diff that is `BUGGY` meets the checklist while
breaking something it touched. Correctness is judged first, and completeness is not run on a
diff that failed correctness — fix correctness first (the combined gate short-circuits
internally; split mode gates in that order).

For a trivial change (docs/format/config — semi-formal-review's skip conditions), record that
the correctness check was skipped as trivial and why; do not fabricate a certificate for it.

The two verdicts use different-depth rubrics by design: correctness is four-level with a
`LIKELY_CORRECT` tier for when context is incomplete; completeness is three-level
(`DONE / PARTIAL / NOT_DONE`), where `PARTIAL` already absorbs the incomplete-evidence
`UNVERIFIED` case, so it needs no separate "likely" tier.

## Step 3 — Merge and move to done/

Only when correctness ∈ {CORRECT, LIKELY_CORRECT} **and** completeness = DONE:

1. Fold the workspace into the integration point and advance the tip (orchestration.md →
   *Merging a completed task*; commands in workspaces.md). Resolve any merge conflict and,
   if the merge changed the result, re-run the verification on the merged code for this task.
2. **Move the task file and its `-certificate.md` from `in-progress/` into `done/`** (on the
   main tree) and check off its remaining `- [ ]` items. This move is the commit point for
   "Done" — the last action, *after* the code merges into the integration point. Then
   recompute `plan.md`'s `Status` from the subfolders and write back only that field.
3. Tear down the workspace (unregister + remove — workspaces.md → *Teardown*).
4. Record in the build log: review verdict, validation verdict, merged. Recompute the
   scheduler's `ready` set — newly-unblocked tasks may now dispatch.

---

## Handling a failed gate

A failing gate is feedback, not a dead end. The verdict and its evidence are precise — use
them.

1. **Re-dispatch the implementer** (preferably the same sub-agent, with its context) in the
   **same workspace**, briefed with the specific failure: the review's `BUGGY`/`CONCERNS`
   finding (the offending `file:line`, the regression, the unhandled case), or the
   validator's `UNSATISFIED`/`UNVERIFIED` obligations (which DoD items are unmet and what
   evidence was missing). Ask it to fix exactly those.
2. **Re-run the verification.** In combined mode the whole gate re-runs (one agent, both
   verdicts). In split mode a correctness fix re-runs gate 1 then gate 2; a completeness fix
   re-runs gate 2, and gate 1 too if the fix changed logic.
3. **Bound the retries.** After a small number of attempts (default **2**) without both
   gates passing, **stop and surface to the user** with the diff, the standing verdicts,
   and what remains — do not loop indefinitely or lower the bar to force a pass. **Park the
   task**: move it (and its `-certificate.md`) from `in-progress/` into `blocked/` on the main
   tree and add a `**Blocked:** <reason>` line to its header. Leave its workspace intact for
   inspection, and let the scheduler continue with tasks that do not depend on it.
4. **`UNVERIFIED`, not `UNSATISFIED`.** If the completeness verdict was `PARTIAL` only because
   evidence could not be produced in the workspace (a test harness missing, a screen not
   exercisable headlessly), that is an environment gap, not a defect — surface it to the
   user to verify manually rather than re-dispatching the builder against a wall.

A parked task blocks its dependents. If parking strands part of the graph, report which
tasks are now unreachable so the user can decide: fix the parked task, re-plan, or accept
a partial build.

---

## Invariants (do not violate, whatever the mode)

- **The implementer never grades its own work.** The verification is run by a different agent —
  one combined verifier, or the two split gates.
- **Both verdicts pass before merge.** No task reaches `done/` on one verdict, or on the
  implementer's say-so.
- **Folder membership reflects reality.** "Done" means the task file sits in `done/` after the
  merge; a parked task is moved to `blocked/`, never left as if done; `plan.md`'s recomputed
  `Status` is `Done` only when every task is in `done/`. A task is in **exactly one** of the
  four subfolders, and on resume that membership is authoritative.
- **Plan-folder moves are the orchestrator's, on the main tree.** A sub-agent never moves a
  task file or touches the plan folder; it edits code in its workspace only.
- **The merged result is what was reviewed.** If a merge conflict changed the code, the
  verification re-runs on the merged code — a per-workspace pass does not cover the merge.
- **Failures surface; they do not get papered over.** The bar is not lowered to force a
  green build. An honest parked task beats a falsely-`Done` one.
