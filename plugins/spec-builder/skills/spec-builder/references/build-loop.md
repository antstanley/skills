# Build loop — the per-task lifecycle

What happens to a single task from dispatch to `Done`. The scheduler in
[`orchestration.md`](orchestration.md) decides *which* tasks run and *when*; this file is
what each running task goes through. Every task passes the **same two gates** before it is
merged, and the implementer never runs either gate on its own work.

```
ready ─► implement ─► gate 1: semi-formal review ─► gate 2: validate done ─► merge ─► done
            ▲                  │ (BUGGY/CONCERNS)         │ (NOT_DONE/PARTIAL)
            └──────────────────┴─────────────────────────┘  feedback, re-dispatch (bounded)
```

---

## Step 1 — Implement (sub-agent, isolated)

1. Create the task's workspace from the current integration point (orchestration.md →
   *Integration point*; commands in workspaces.md) so the builder's base holds its
   dependencies' work.
2. Assemble the brief from the task file ([`subagent-brief.md`](subagent-brief.md)) and
   dispatch the implementer sub-agent into the workspace. Mark the task `In progress`.
3. The sub-agent builds only this task, runs the repo's test/lint commands in its
   workspace, and reports back: files changed, how each DoD item is met, command results,
   and anything incomplete. It does **not** mark the task done.

The implementer's report is input to the gates, not a verdict. A sub-agent claiming "all
done, tests pass" is a claim the gates exist to check.

## Step 2 — Gate 1: semi-formal review (correctness)

Run **semi-formal-review** against the workspace diff, by an agent that is **not** the
implementer (the orchestrator, or a separate reviewer sub-agent).

- Input: the diff, plus the task's `Produces` and `Steps` (what it was meant to do).
- Output: `VERDICT: CORRECT | LIKELY_CORRECT | CONCERNS | BUGGY` with confidence and a
  one-line summary.
- **Pass:** `CORRECT` or `LIKELY_CORRECT` → proceed to gate 2.
- **Fail:** `BUGGY` or `CONCERNS` → go to *Handling a failed gate*. Do not run gate 2 on a
  diff that failed review — fix correctness first.

For a trivial change (docs/format/config — semi-formal-review's skip conditions), record
that the review was skipped as trivial and why; do not fabricate a certificate for it.

## Step 3 — Gate 2: validate done (completeness)

Run **validate-done-certificate** against the (now review-clean) workspace diff, again by
an agent that is **not** the implementer.

- Input: the diff, the task's `Definition of done`, and `certificates/NN-<task>.md` if it
  exists. With a certificate, discharge it; without one, derive obligations from the DoD
  and discharge those (the protocol's no-certificate fallback).
- Output: `VERDICT: DONE | PARTIAL | NOT_DONE` with confidence; when a certificate exists,
  the validator writes the statuses and verdict into it and sets `State: Validated …`.
- **Pass:** `DONE` → proceed to merge.
- **Fail:** `PARTIAL` or `NOT_DONE` → *Handling a failed gate*.

Both gates pass = correct **and** complete. Either alone is insufficient: a `CORRECT` diff
that is `PARTIAL` does the wrong scope well; a `DONE` diff that is `BUGGY` meets the
checklist while breaking something it touched.

## Step 4 — Merge and mark done

Only when gate 1 ∈ {CORRECT, LIKELY_CORRECT} **and** gate 2 = DONE:

1. Fold the workspace into the integration point and advance the tip (orchestration.md →
   *Merging a completed task*; commands in workspaces.md). Resolve any merge conflict and,
   if the merge changed the result, re-run both gates on the merged code for this task.
2. Set the task file `Status: Done` and check off its remaining `- [ ]` items.
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
2. **Re-run the gate(s).** A correctness fix re-runs gate 1 then gate 2; a completeness fix
   re-runs gate 2 (and gate 1 if the fix changed logic).
3. **Bound the retries.** After a small number of attempts (default **2**) without both
   gates passing, **stop and surface to the user** with the diff, the standing verdicts,
   and what remains — do not loop indefinitely or lower the bar to force a pass. Mark the
   task **parked** (it stays `In progress` with a note), leave its workspace intact for
   inspection, and let the scheduler continue with tasks that do not depend on it.
4. **`UNVERIFIED`, not `UNSATISFIED`.** If gate 2 returned `PARTIAL` only because evidence
   could not be produced in the workspace (a test harness missing, a screen not
   exercisable headlessly), that is an environment gap, not a defect — surface it to the
   user to verify manually rather than re-dispatching the builder against a wall.

A parked task blocks its dependents. If parking strands part of the graph, report which
tasks are now unreachable so the user can decide: fix the parked task, re-plan, or accept
a partial build.

---

## Invariants (do not violate, whatever the mode)

- **The implementer never grades its own work.** Both gates are run by a different agent.
- **Both gates pass before merge.** No task reaches `Done` on one gate, or on the
  implementer's say-so.
- **Status reflects reality.** `Done` means merged-and-both-gates-passed; a parked task is
  never silently marked `Done`; `plan.md` is `Done` only when every task is.
- **The merged result is what was reviewed.** If a merge conflict changed the code, the
  gates re-run on the merged code — a per-workspace pass does not cover the merge.
- **Failures surface; they do not get papered over.** The bar is not lowered to force a
  green build. An honest parked task beats a falsely-`Done` one.
