---
name: semi-formal-review
description: Review an implemented change with a semi-formal certificate — premises, function resolution, execution trace, regression check, derived verdict — to decide whether it correctly and completely does what was asked without breaking what it touched. The mandatory correctness gate after a spec-builder task is implemented, run by an agent other than the one that wrote the code. Triggers on "review this change semi-formally", "semi-formal review of the diff", "verify this patch", "is this implementation correct", "check for regressions", or spec-builder dispatching a post-implementation review. Produces a CORRECT / LIKELY_CORRECT / CONCERNS / BUGGY verdict with confidence; for a done-vs-definition-of-done check use validate-done-certificate instead.
---

# Semi-Formal Review

A skill for reviewing a completed implementation with a **semi-formal reasoning
certificate**: premises, claims, the evidence behind each, and a verdict *derived* from
explicit checkpoints rather than declared. It is the consolidated, self-contained form
of the `reasoning-semiformally` method, pointed at one question — **does this change
correctly and completely do what its task asked, without breaking what it touched?**

## Core principle

**A review is a certificate, not an opinion.** Three checkpoints stand between the diff
and the verdict, and the verdict follows mechanically from them: which definition each
call actually resolves to (name shadowing is the classic confidently-wrong bug),
whether the change addresses the root cause or only a symptom, and whether the code
that depended on the old behavior still works. Skip a checkpoint and the verdict is an
assertion; run all three and it is evidence. The full method — the certificate shape,
the 5-step function-resolution sequence, the execution-trace and regression checks, the
verdict rubric, and a worked example — is vendored at
[`references/method.md`](references/method.md).

## Relationship to spec-builder and validate-done-certificate

This skill is one of the two completion gates in **spec-builder**'s build loop:

- **semi-formal-review** (this skill) gates **correctness** — is the implementation
  right, free of scope/shadowing bugs, and free of regressions? Verdict:
  `CORRECT / LIKELY_CORRECT / CONCERNS / BUGGY`.
- **validate-done-certificate** gates **completeness** — does the change satisfy the
  task's definition of done (discharging its done certificate, or the DoD checklist
  directly when no certificate exists)? Verdict: `DONE / PARTIAL / NOT_DONE`.

Both reuse the same procedure from [`references/method.md`](references/method.md)
against different rubrics. A task is only marked `Done` when this skill returns
`CORRECT`/`LIKELY_CORRECT` **and** validate-done-certificate returns `DONE`.

**Run by a different agent than the one that wrote the code.** A builder reviewing its
own work re-asserts its own assumptions. In spec-builder the implementer is a sub-agent
in its own workspace; this review is run by the orchestrator or a separate reviewer
sub-agent against that workspace's diff.

## When to apply this skill

- spec-builder has finished implementing a task and needs the **correctness gate** run
  against the resulting diff before the task can be marked done.
- The user asks to **verify a patch or implementation**, hunt a cross-scope bug, check a
  change for regressions, or compare two candidate fixes.
- A change crosses scope boundaries (calls into other modules, shadows a name, relies on
  resolution that is not locally obvious) and a quick read is not enough.

## Skip conditions

Proceed with standard reasoning — no certificate — when:

- The change is trivial: docs, formatting, version bumps, config-only edits.
- The bug or change is locally obvious: a typo, an off-by-one in the same function, a
  missing argument, with no execution path crossing a scope boundary.
- The task is not code analysis (text editing, data extraction, summarization).

In spec-builder, a skipped review is still recorded — note that the change was trivial
and why — so the build log shows the gate was considered, not silently bypassed.

## Workflow

Apply the certificate from [`references/method.md`](references/method.md):

1. **Premises (P1–P3).** What the change touches; what the task asked it to do (from the
   task file's `Produces` and `Steps`); what must not break.
2. **Function resolution.** Resolve every call in the changed lines through the 5-step
   sequence; flag shadowing or `UNRESOLVED`.
3. **Execution trace.** One concrete input, 3–5 concrete steps, to the result the task promised.
4. **Regression check.** Trace at least one downstream caller of each modified unit, or
   state that none is in scope.
5. **Sufficiency.** Confirm the change addresses the root cause, not just a symptom.
6. **Verdict.** Derive `CORRECT / LIKELY_CORRECT / CONCERNS / BUGGY` with confidence and a
   one-sentence summary — never declared up front.

Follow this full procedure on every review, regardless of which model or agent runs it —
there is no compact shortcut. If the verdict is `BUGGY` and the caller needs the
offending line, expand to fault localization (also in the reference) and report the line
with its sufficiency test.

## What NOT to do

- **Don't review your own implementation.** The reviewer must differ from the builder.
- **Don't declare the verdict, then justify it.** Run the checkpoints first; the verdict
  is their output.
- **Don't skip the regression trace silently.** Trace a caller or state that none is in
  scope — never leave it implicit.
- **Don't conflate correctness with done-ness.** This skill judges whether the code is
  right; whether it satisfies the definition of done is validate-done-certificate's job.
- **Don't apply the certificate to trivial changes.** Ceremony without rigor; say it was trivial and move on.

## Reference files

- [`references/method.md`](references/method.md) — The vendored, consolidated semi-formal
  method: the certificate shape, the single step-by-step procedure used for every review,
  the 5-step function-resolution sequence, the execution-trace and regression checks, the
  verdict rubric, and a worked example. Read before reviewing.
