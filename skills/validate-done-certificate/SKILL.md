---
name: validate-done-certificate
description: Discharge a task's done certificate against its implementation — collect each obligation's named evidence, run its checks, set each status, trace regressions, and derive a DONE / PARTIAL / NOT_DONE verdict by the certificate's rubric. The completeness gate after a spec-builder task is reviewed; when a task has no authored certificate, it derives obligations from the DoD checklist and discharges those the same way. It runs the protocol, it does not author it (that is done-certificates' job). Triggers on "validate the done certificate", "is task NN done", or "check the implementation against its definition of done".
---

# Validate Done Certificate

A skill for **discharging** a done certificate: opening the blank verification protocol
the `done-certificates` skill authored for a task, doing exactly what each obligation
names, and deriving whether the task is `DONE`. It is the validating agent that
companion was written for — it supplies the answers, it does not write the questions.

## Core principle

**A definition of done is a claim; the certificate is the protocol that proves it; this
skill runs the protocol.** Each definition-of-done item is an obligation that names the
evidence to collect (a `file:line` to read, a test to run and its expected result, a
trace to produce) and the checks to apply (function resolution to defeat name shadowing,
a regression trace). Discharging means collecting that evidence against the *real*
implementation, marking each obligation `SATISFIED / UNSATISFIED / UNVERIFIED`, and
deriving the verdict by the rubric — never ticking a box by assertion. The full
procedure is in [`references/validation-protocol.md`](references/validation-protocol.md);
the function-resolution and regression checkpoints it leans on are vendored in this
plugin at [`../semi-formal-review/references/method.md`](../semi-formal-review/references/method.md).

The split is the whole point: **done-certificates authors** the certificate,
**this skill validates** it, and they must be different agents. An agent that grades its
own homework re-asserts its own assumptions.

## Relationship to spec-builder, done-certificates, and semi-formal-review

- **done-certificates** ([in the spec-planner plugin](../../../spec-planner/skills/done-certificates/SKILL.md))
  authors one blank certificate per task. **This skill** discharges it. Numbers, obligations,
  and evidence instructions are already written — do not re-derive them; collect their answers.
- In **spec-builder**'s build loop this is the **completeness gate**, run after
  **semi-formal-review** passes. semi-formal-review asks *is the code correct?*
  (`CORRECT / … / BUGGY`); this skill asks *does the code satisfy what done means?*
  (`DONE / PARTIAL / NOT_DONE`). A task is marked `Done` only when review is
  `CORRECT`/`LIKELY_CORRECT` **and** this skill returns `DONE`. Both reuse the same
  checkpoints against different rubrics. By default spec-builder runs the two as **one**
  verifier agent over a single reading of the diff (`gate_mode: combined`, that plugin's
  `references/combined-gate.md`); `gate_mode: split` runs this gate as its own agent after the
  correctness gate passes. This skill's protocol and verdict are the same in both.
- **Run by an agent other than the task's implementer** — in spec-builder the implementer
  is a sub-agent in its own workspace; the validator is the orchestrator or a separate
  validator sub-agent working against that workspace's diff. It reads the task's
  `NN-<task>-certificate.md` from the task's **current kanban subfolder on the main tree**
  (`in-progress/` when the gate runs) — not from a `certificates/` path, and not from a
  sub-agent's workspace copy.

## When to apply this skill

- spec-builder has implemented a task, semi-formal-review has passed, and the **definition
  of done** must be proven before the task is marked done.
- The user asks to **validate, discharge, or run a done certificate**, or to **check an
  implementation against its definition of done** — "is task 04 done", "verify the DoD",
  "discharge the certificate for the lock task".
- A task has a `Definition of done` (with or without an authored certificate) and someone
  needs a checkable verdict rather than a hand-ticked checklist.

## Skip / flag conditions

- **No certificate, but a DoD exists** — do **not** skip. Derive obligations from the DoD
  checklist and discharge them the same way (see the protocol's *no certificate* section).
- **Neither a certificate nor a DoD** — there is nothing to validate. Flag it as a plan
  defect (a spec-planner task without a DoD is a defect by that skill's own checklist)
  rather than passing the task by default.
- **Trivial, local change** whose DoD is "the typo is gone" — a certificate is ceremony;
  confirm the obvious outcome and say so.

## Workflow

Follow [`references/validation-protocol.md`](references/validation-protocol.md):

1. **Read the contract.** Open the certificate — the co-located `NN-<task>-certificate.md` in
   the task's current subfolder on the main tree (or the DoD when none exists); confirm the
   obligations map one-to-one onto the DoD items; read the premises and the regression surface.
2. **Discharge each obligation.** Collect the named evidence, run the named checks (resolve
   each named call through the 5-step sequence), and set each status from what the evidence
   actually showed — `SATISFIED` only with evidence in hand, `UNVERIFIED` when it could not
   be produced, never by assumption. The `Reviewable:` obligation is exercised, not assumed.
3. **Regression and verdict.** Trace each named downstream caller (`PRESERVED` / `REGRESSION`);
   derive `DONE / PARTIAL / NOT_DONE` and `CONFIDENCE` by the rubric; write them and a
   one-sentence `SUMMARY` into the Conclusion, and set the certificate `State:` to
   `Validated YYYY-MM-DD`.

A `DONE` verdict with any non-`SATISFIED` obligation is malformed — recheck before recording it.

## What NOT to do

- **Don't author the certificate.** That is done-certificates' job; this skill only
  discharges. If an obligation is wrong, note it in the summary — do not rewrite it.
- **Don't mark `SATISFIED` without evidence**, and don't fabricate a test result — run it.
- **Don't pass a task by default** when validation cannot run; `UNVERIFIED` yields
  `PARTIAL`. What happens next (re-dispatch, surface to user) is spec-builder's call.
- **Don't validate your own implementation.** Validator ≠ builder.
- **Don't expand the contract** beyond the DoD items, and **don't declare the verdict
  first** — derive it from the obligation statuses and the regression check.

## Reference files

- [`references/validation-protocol.md`](references/validation-protocol.md) — How to
  discharge a certificate end to end: read the contract, collect evidence and run checks
  per obligation, set statuses, trace regressions, derive the `DONE / PARTIAL / NOT_DONE`
  verdict, the no-certificate DoD fallback, and a worked discharge. Read before validating.
- [`../semi-formal-review/references/method.md`](../semi-formal-review/references/method.md) —
  The vendored checkpoints the protocol uses: the 5-step function-resolution sequence and
  the execution-trace / regression checks.
