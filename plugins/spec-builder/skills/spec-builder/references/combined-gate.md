# The combined verification gate — correctness and completeness in one context

spec-builder's default gate. One sub-agent reads the task's diff **once** and returns
**both** verdicts — the correctness verdict (`CORRECT / LIKELY_CORRECT / CONCERNS / BUGGY`)
and the completeness verdict (`DONE / PARTIAL / NOT_DONE`) — by running the two gates'
methods over a single shared reading of the code. It exists because the two gates iterate the
same diff, resolve the same calls, and trace the same regressions; computing that shared work
twice, in two agent contexts, is the token cost this gate removes.

It changes **who** runs the checks, not **what** they are. The correctness method
([`../../semi-formal-review/references/method.md`](../../semi-formal-review/references/method.md))
and the completeness protocol
([`../../validate-done-certificate/references/validation-protocol.md`](../../validate-done-certificate/references/validation-protocol.md))
are unchanged and still leaned on directly — this file only sequences them so their shared
checkpoints run once.

---

## What it preserves and what it relaxes

- **Preserved — the load-bearing invariant:** the gate agent is **not** the implementer. A
  builder never grades its own work; that is the rule the whole skill exists to enforce, and
  one combined agent honours it exactly as two separate ones did.
- **Relaxed — reviewer ≠ validator:** the two gates are now one agent, so the correctness
  reviewer and the completeness validator are the same mind. The plan always allowed this
  ([`subagent-brief.md`](subagent-brief.md) — "the orchestrator may run both gates itself since
  it did not write the code"); it was an *ideally*, not an invariant. The cost is mild
  anchoring — an agent that has just concluded `CORRECT` is a little primed to read obligations
  as `SATISFIED`. Two things blunt it: the completeness half collects its **own** execution
  evidence (it runs the named tests and exercises the `Reviewable:` action, it does not merely
  reason from the correctness pass), and the semi-formal structure bars declare-then-justify.
  When that residual risk is not acceptable — a high-risk plan, or a retry whose verdict you
  distrust — set `gate_mode: split` and the two gates run as separate agents again.

## The two modes

- **`combined` (default):** one verifier sub-agent, the protocol below, both verdicts.
- **`split`:** the historical flow — gate 1 (`semi-formal-review`) runs first, and only if it
  passes does gate 2 (`validate-done-certificate`) run, each as its own dispatch (or via the
  Skill tool by the orchestrator). Same two verdicts, same merge condition, two contexts.
  Nothing else in the build loop changes. Resolve the knob per
  [`orchestration.md`](orchestration.md) → *Configuration*.

---

## The protocol (combined mode)

Run by a single agent that is **not** the implementer, at the model/effort the orchestrator
resolved for the gate ([`model-policy.md`](model-policy.md)). Follow it in order; do not
collapse the two verdicts into one.

1. **Read once.** Read the workspace diff, the code it touches, and the task's
   `NN-<task>-certificate.md` (from the **main tree**, the `in-progress/` subfolder — never a
   sub-agent's workspace copy), or its `Definition of done` when no certificate exists. Write
   the correctness premises `P1–P3` (method.md Step 1) **and** note the obligation set `O1…On`
   from the certificate together — one framing of the change serves both halves.
2. **Shared checkpoints, once.** Over the whole diff, run the method's checkpoints a single
   time: function resolution (the 5-step sequence) for every call in the changed lines, one
   execution trace on the path the task's `Produces` promises, and the regression check for
   each modified unit's downstream callers. This evidence is the substrate of **both** verdicts
   — do not recompute it in the completeness half.
3. **Derive the correctness verdict.** Against that evidence plus the edge-case and
   root-cause-sufficiency steps, apply the correctness rubric →
   `CORRECT / LIKELY_CORRECT / CONCERNS / BUGGY` (method.md Step 6). Derive it; do not declare it.
4. **Short-circuit on a failed correctness verdict.** If it is `BUGGY` or `CONCERNS`, stop
   before the completeness-specific evidence collection — the named-test runs and the
   `Reviewable:` exercise, which a correctness fix would invalidate. Report the correctness
   verdict and set completeness to `pending correctness fix`; the build loop re-dispatches the
   implementer on the correctness finding. This keeps the old economy — a failed diff never
   pays for a completeness discharge.
5. **Discharge completeness** (only when correctness passed). Work the validation protocol
   ([`../../validate-done-certificate/references/validation-protocol.md`](../../validate-done-certificate/references/validation-protocol.md)),
   **reusing** the step-2 resolution and regression evidence rather than reproducing it, and
   adding only what is genuinely new: collect each obligation's named evidence, **run the named
   tests**, **exercise the `Reviewable:` action** and observe the result, set each status
   (`SATISFIED / UNSATISFIED / UNVERIFIED`) from what the evidence showed, and derive
   `DONE / PARTIAL / NOT_DONE`. Write the statuses, the verdict, and `State: Validated
   YYYY-MM-DD` into the certificate, exactly as validate-done-certificate specifies.
6. **Return both verdicts** in one report (below).

## Output

```
CORRECTNESS:  [CORRECT | LIKELY_CORRECT | CONCERNS | BUGGY]        confidence: [high|medium|low]
COMPLETENESS: [DONE | PARTIAL | NOT_DONE | pending correctness fix] confidence: [high|medium|low]
SUMMARY: [one sentence tying the two verdicts to the evidence]
```

The certificate is written as in split mode — the completeness half owns that write; the
correctness verdict lives in the build log, not the certificate.

## The merge condition (unchanged)

A task merges only when **correctness ∈ {`CORRECT`, `LIKELY_CORRECT`} and completeness =
`DONE`** — exactly the two-gate rule ([`build-loop.md`](build-loop.md)). The verdicts stay
distinct because the build loop branches on them differently: a `BUGGY`/`CONCERNS` re-dispatch
fixes correctness (then the whole gate re-runs); a `PARTIAL`/`NOT_DONE` re-dispatch fixes
completeness; and a `PARTIAL` that is `UNVERIFIED`-not-`UNSATISFIED` surfaces to the user
rather than re-dispatching. Collapsing the two into one verdict would lose the signal these
branches need.

## What NOT to do

- **Don't collapse the two verdicts.** Emit both, each by its own rubric. One "looks good" is
  not a gate.
- **Don't skip the dynamic evidence.** Completeness still runs the named tests and exercises
  the `Reviewable:` action. Reasoning from the correctness pass is not a substitute — it is
  precisely what would make the merged gate weaker than two.
- **Don't recompute the shared checkpoints.** Function resolution and the regression trace are
  done once, in step 2, and reused. Recomputing them in the completeness half throws away the
  saving this gate exists for.
- **Don't grade your own work.** The verifier is never the implementer — combined or split.
- **Don't run completeness on a failed correctness verdict.** Short-circuit; fix correctness
  first, exactly as split mode's gate ordering does.
