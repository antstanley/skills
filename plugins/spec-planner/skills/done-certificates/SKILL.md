---
name: done-certificates
description: Author a task-specific semi-formal done certificate — a structured verification protocol that a separate validating agent runs to decide whether a task is complete. For each task it restates the definition of done as proof obligations, names the exact evidence to collect and the resolution/regression checks to run, and leaves the status and verdict blank for the validator to discharge. Triggers on "create a done certificate", "write a certificate of done for these tasks", "add done certificates to the plan", "make a DoD verification certificate", or "generate a completion certificate". Works standalone over any task with a definition of done, and is the companion certificate-author for spec-planner task packages — one certificate per task.
---

# Done Certificates

A skill for writing the **verification protocol** that decides whether a task is done — not for running it. For each task it produces a task-specific **semi-formal reasoning certificate**: the definition of done restated as explicit proof obligations, each naming the evidence a validator must collect and the checks it must run, with the status and verdict left blank. A separate validating agent later opens the certificate and discharges it against the code.

The split is the whole point:

- **This skill authors the certificate** — it does the reasoning about *what must be true for this task to be done and how a validator would prove it*, tailored to the task's actual definition of done, produces, and code surface.
- **A different agent validates** — it opens the certificate, collects the named evidence, runs the named checks, fills in each status, and derives the verdict.

A certificate is therefore a checkable, task-specific contract: a validator following it cannot skip an obligation or call a task done without producing the evidence the certificate demands.

## Core principle

**A definition of done is a claim; a done certificate is the protocol that proves or refutes it.** A spec-planner task ends in a `Definition of done` checklist — a list of obligations stated as boxes to tick. Ticking them by hand is an assertion. This skill turns that checklist into a semi-formal certificate where each obligation names *the evidence required* (a file location to read, a test to run, an execution trace to produce) and *the checks that apply* (function resolution to defeat name shadowing, a regression trace against named callers). The discipline is **semi-formal reasoning** — structured templates that act as certificates: the agent running them cannot skip cases or make unsupported claims. The method is vendored into this skill at [`references/semiformal-method.md`](references/semiformal-method.md).

Two rules follow:

1. **Every definition-of-done item becomes one obligation that names its own evidence.** The certificate does not say "verify the lock works"; it says "verify O1 by running `lock.test.ts › rejects wrong passphrase` and tracing `unlock()` at `src/auth/lock.ts`, confirming it returns before `vault.unlock()`." The obligation is specific enough that any validator collects the *same* evidence.
2. **The certificate is authored blank and discharged by someone else.** Status fields are `☐ unverified` and the verdict is empty when this skill hands the certificate over. Filling them is the validator's job, governed by the rubric the certificate carries. This skill never fabricates evidence or pre-decides the verdict.

This skill applies semi-formal reasoning (the certificate shape and the function-resolution and regression checkpoints, all in [`references/semiformal-method.md`](references/semiformal-method.md)) to the question *"how would an agent prove this specific task is done?"* — and writes that proof obligation down so the agent can.

## Relationship to spec-planner

This skill is a companion to **spec-planner**. spec-planner produces task packages, each carrying a `Definition of done` checklist that ends in a `Reviewable:` line. done-certificates consumes that checklist and writes the certificate that a validator uses to discharge it.

- **spec-planner** writes *what done means* for each task (the DoD checklist). **done-certificates** writes *the protocol to prove it* (the certificate). A *validating agent* (a subagent, a reviewer, a later session) *runs* the protocol.
- The **semi-formal reasoning method** — the premise/claim/evidence/verdict structure and the function-resolution and regression checkpoints — is vendored into this skill at [`references/semiformal-method.md`](references/semiformal-method.md), so the skill is self-contained when installed. A done certificate is that method instantiated for one task's definition of done; the certificate you author tells the validator to run those exact procedures.

It is not limited to spec-planner output. Any task with a definition of done — an issue with acceptance criteria, a PRD feature with a "done when" list, a checklist in a ticket — can have a certificate authored for it. The source of the obligations shapes how you read them; the certificate structure is the same.

## When to apply this skill

- The user asks to **create, write, or generate a done certificate** for one or more tasks — "create a certificate of done for each of these tasks", "add done certificates to the plan", "make a completion certificate for task 04".
- spec-planner has produced (or is producing) a plan and the user wants **done certificates added** to its task packages so each task ships with the protocol that will later validate it.
- A team wants a **task-specific verification contract** a reviewer or validating agent can run, rather than re-deriving "what does done mean here" each time.

Skip when:

- There is **no definition of done** to build a certificate from — the task has no acceptance criteria and none can be inferred. Ask for them (or, for a spec-planner task, that is a defect in the plan — flag it).
- The task is **trivial and local** — a one-line doc fix whose DoD is "the typo is gone". A certificate adds ceremony without rigor. Say so.
- The request is to *write* the definition of done (that is spec-planner) or to *validate* a task right now (that is the downstream validating agent running an already-authored certificate — this skill writes the certificate, it does not run it). If the user wants you to *both* author and then validate, author the certificate first, then validate it as a separate, explicit step.

## What the certificate is — and who fills it in

A done certificate is a **blank verification protocol specific to one task**. When this skill finishes, the certificate contains:

- a precise **definition** of what done means for this task;
- **premises** about the task's goal, obligations, and invariants;
- one **obligation per definition-of-done item**, each naming the **evidence to collect** and the **checks to run** — but with the **status left `☐ unverified`**;
- a **regression check** naming the downstream callers a validator must trace — left blank;
- a **conclusion** block with the **verdict rubric** spelled out but the **verdict empty**.

A validating agent (or reviewer, or a later session) then opens it, does the work each obligation names, marks each status, and derives the verdict by the rubric. The authored certificate is the *questions and the method*; the validator supplies the *answers*. See [`references/certificate-template.md`](references/certificate-template.md) for the skeleton and the field conventions.

## Workflow

Three phases. All three are about *authoring* — collecting live evidence and reaching a verdict is the validator's job, downstream and out of scope here.

### Phase 1 — Read the obligations

1. **Locate the definition of done.** For a spec-planner task, read its `NN-snake_case_task.md`: the `Produces` line (the goal), `Depends on` and `Pointers` (the surface), and the `## Definition of done` checklist (the obligations). For any other source, find the acceptance criteria / "done when" list.
2. **Map the task's surface.** From `Pointers`, the steps, and (if the code exists) the files involved, identify the scope-crossing calls and the downstream callers — these become the resolution and regression checks the certificate will tell the validator to run. If the code does not exist yet (planning time), reference the planned entry points from `Pointers`.
3. **Confirm there is something to certify.** If the DoD is empty or absent, stop and flag it (a spec-planner task without a DoD is a defect, per that skill's own checklist).

### Phase 2 — Derive the proof obligations

This is where the reasoning lives — translating a DoD checklist into a protocol a validator can run without re-deriving intent. Following [`references/certificate-template.md`](references/certificate-template.md):

1. **Definition.** State what `DONE` means for *this* task: every obligation below holds, each backed by the evidence the obligation names — not by assertion.
2. **Premises.** `P1` the goal (one sentence, from `Produces`); `P2` the obligation set (one obligation `Oi` per DoD item, in DoD order, the last always the `Reviewable:` item); `P3` the invariants (existing behavior that must not break — the regression surface from Phase 1).
3. **Obligations.** One block per DoD item. Each carries:
   - a **Claim** — the checkable condition the item asserts;
   - **Evidence to collect** — the *specific* artifact a validator must produce: which file:line to read, which named test to run and the result to expect, which execution trace with which input. Specific enough that two validators collect the same evidence. For the **"Meets the repo definition of done"** obligation, draw the concrete commands (the test, lint, and format invocations) from the repo's development guidelines — `docs/specs/development-guidelines.md` §Definition of done, named in the plan's DoD baseline — **not** from the task's `Pointers`, which carry code entry points rather than build commands. When the commands are not yet pinned down at planning time, name them by role ("the repo's test command", "the lint gate") so the validator resolves them from the guidelines.
   - **Checks** — the task-specific resolution and regression checks that apply (e.g., "resolve `verify()` at `lock.ts:34` — confirm it is the imported crypto `verify`, not the global `crypto.subtle.verify`"). Omit for an obligation with no scope-crossing calls (e.g. "lint passes").
   - a **Status** field, left `☐ unverified` for the validator.

### Phase 3 — Write the validator's rubric and hand off

1. **Regression check.** Name the downstream callers the validator must trace and the expected outcome, left blank for `PRESERVED`/`REGRESSION`. If the task touches no existing code, say so.
2. **Conclusion block.** Spell out the **verdict rubric** (below) so the validator derives, not declares, the verdict — and leave `VERDICT`, `CONFIDENCE`, and `SUMMARY` empty.
3. **Hand off.** State plainly that the certificate is authored and unverified, and that a validating agent discharges it. Do not fill it in yourself unless the user explicitly asks you to also validate — and if so, do that as a separate, clearly-marked step.

The verdict rubric the certificate carries, for the validator to apply:

- **NOT_DONE** — any load-bearing obligation is `UNSATISFIED`, **or** the regression check found a `REGRESSION`.
- **PARTIAL** — every obligation is `SATISFIED` except one or more that are `UNVERIFIED` (the available context could not prove them), and no regression.
- **DONE** — every obligation `SATISFIED`, regression check `PRESERVED`, and the evidence sufficient to verify each (including the `Reviewable:` obligation). A `DONE` verdict with any non-`SATISFIED` obligation is malformed.

## Where the certificate lives

- **For a spec-planner plan:** one certificate per task in a `certificates/` subfolder of the plan folder, named to mirror the task file — `docs/plans/YYYY-MM-DD-title/certificates/NN-snake_case_task.md`. The `NN` matches the task it certifies, so the folder sorts in implementation order alongside the tasks. The certificate links up to its task (`../NN-…md`) and to `plan.md` (`../plan.md`); the task file may add a `**Certificate:** [certificates/NN-…md](certificates/NN-…md)` line to its header so the link is two-way.
- **Standalone (no plan folder):** write to `docs/certificates/<snake_case_task>.md`, or alongside the artifact the task lives in if the user names a location. Link to whatever defines the task's DoD.

Numbers are append-only, exactly as in spec-planner: a certificate keeps its task's number; a task added later takes the next free number.

## When invoked by spec-planner

spec-planner may delegate here after Phase 4 (writing the task files), when the user asks for done certificates as part of the plan. In that case:

- The DoD baseline, owner, and task numbering are already established — do not re-derive them.
- Write **one certificate per task file** into the plan folder's `certificates/` subfolder, with obligations drawn from each task's `Definition of done` and the evidence/checks named per obligation — left unverified.
- Add the two-way `**Certificate:**` link to each task file's header.
- spec-planner owns the plan and its cross-link pass; done-certificates owns the `certificates/` subfolder and the certificate ↔ task links within it.

The certificates then ship with the plan as the per-task validation contracts: when each task is built, a validating agent (not this skill) opens its certificate and discharges it to decide whether the task is done.

## What NOT to do

- **Don't validate from this skill.** Authoring the certificate and running it are different jobs done by different agents. This skill writes the protocol; it leaves status and verdict blank. Validate only if the user explicitly asks, and then as a separate, marked step.
- **Don't write vague obligations.** "Verify it works" is not an obligation. Name the file, the test, the trace, the caller. A second validator must be able to collect the same evidence from your obligation alone.
- **Don't fabricate or pre-fill evidence.** Evidence is collected by the validator against real code. The certificate names *what* to collect, not a guessed result.
- **Don't restate the task or the spec.** The certificate references the task file and names the DoD items; it does not reproduce the steps. A reader opens the task alongside the certificate.
- **Don't author beyond the definition of done.** The certificate's obligations are exactly the DoD items, one to one. Quality concerns outside the DoD belong in `Residue` as notes, not as new obligations — the DoD is the contract.
- **Don't renumber certificates.** They mirror the task numbers, which are append-only.
- **Don't write a certificate for a trivial change.** Ceremony without rigor.

## Reference files

- [`references/semiformal-method.md`](references/semiformal-method.md) — The vendored semi-formal reasoning method: the certificate shape (definition / premises / claims / evidence / conclusion), the function-resolution checkpoint (the 5-step name-resolution sequence), the execution-trace and regression checks, and the verdict rubric. The self-contained basis for everything this skill writes. Read first.
- [`references/certificate-template.md`](references/certificate-template.md) — The done-certificate skeleton (definition, premises, obligations with evidence/checks/status, regression check, residue, conclusion with the verdict rubric), the blank-field conventions for hand-off to a validator, and a worked example of an authored (unverified) certificate. Read before Phase 2.
