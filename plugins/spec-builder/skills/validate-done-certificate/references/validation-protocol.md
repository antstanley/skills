# Validation protocol — discharging a done certificate

This skill is the **validating agent** the `done-certificates` skill writes for. A done
certificate is authored **blank**: each definition-of-done item becomes an obligation
naming the evidence to collect and the checks to run, with status `☐ unverified` and the
verdict empty. Discharging it means doing exactly what each obligation names, marking
each status from real evidence, and *deriving* the verdict by the rubric the certificate
carries. The author asked the questions; the validator supplies the answers.

The function-resolution and execution-trace/regression checkpoints used below are the
ones vendored in this plugin at
[`../../semi-formal-review/references/method.md`](../../semi-formal-review/references/method.md) —
read them once; this file does not restate them.

---

## Inputs

- **The certificate** — `.specs/plans/<plan>/certificates/NN-<task>.md` for a spec-planner
  plan, or wherever the task's certificate lives.
- **The task file** — `NN-<task>.md`: its `Produces`, `Pointers`, and the
  `## Definition of done` checklist the certificate's obligations mirror one-to-one.
- **The implementation** — the actual code/diff to validate (in spec-builder, the task
  sub-agent's workspace revision).

---

## Phase 1 — Read and confirm the contract

1. Open the certificate. Confirm its obligations `O1…On` map one-to-one onto the task's
   `Definition of done` items, in order, with `On` the `Reviewable:` item. If the
   certificate and the DoD have drifted, validate against the **DoD** (the contract) and
   note the drift in the summary.
2. Read the premises: `P1` goal, `P2` obligation set, `P3` invariants (the regression surface).
3. Set `State:` working context to "Validating YYYY-MM-DD" (today's date). Do not edit the
   authored obligation/evidence text — you fill statuses and the conclusion, not the protocol.

## Phase 2 — Discharge each obligation

For every obligation, in order:

1. **Collect the named evidence.** Do *exactly* what `Evidence to collect` says — read the
   named `file:line`, run the named test and observe the result, produce the named
   execution trace with the named input. Collect evidence; do not infer it.
2. **Run the named checks.** Where the obligation carries a `Checks` field, resolve each
   named call with the 5-step function-resolution sequence and confirm it is the intended
   definition, not the named plausible shadow. Flag shadowing.
3. **Set the status** from what the evidence actually showed:
   - `SATISFIED` — the evidence exists and shows the claim holds.
   - `UNSATISFIED` — the evidence shows the claim does **not** hold.
   - `UNVERIFIED` — the evidence could not be produced in the available context (a test
     would not run, a screen could not be exercised). Never `SATISFIED` by assumption.
4. **The `Reviewable:` obligation (`On`)** is discharged like any other: exercise the
   concrete action it names and observe the concrete result. If it cannot be exercised in
   the available context, it is `UNVERIFIED`, not `SATISFIED`.

## Phase 3 — Regression check and verdict

1. **Regression check.** For each downstream caller the certificate names, trace it with a
   typical input and record `PRESERVED` or `REGRESSION: <caller> would now get <wrong
   result> because <reason>`. If the certificate states no existing code was touched,
   confirm that and record it.
2. **Derive the verdict** — do not declare it:
   - **NOT_DONE** — any load-bearing obligation is `UNSATISFIED`, **or** the regression
     check found a `REGRESSION`.
   - **PARTIAL** — every obligation `SATISFIED` except one or more `UNVERIFIED` (the
     context could not prove them), and no regression.
   - **DONE** — every obligation `SATISFIED`, regression `PRESERVED`, and the evidence
     sufficient to verify each (including the `Reviewable:` obligation).
3. **`CONFIDENCE`** (high / medium / low) reflects how complete the evidence was — could
   every named test run, every caller be traced — not how done the work is hoped to be.
4. A `DONE` verdict alongside any non-`SATISFIED` obligation is **malformed**. If you reach
   for one, you have made an error; recheck the obligation.

Write `VERDICT`, `CONFIDENCE`, and `SUMMARY` (one sentence deriving the verdict from the
statuses) into the certificate's Conclusion block, and set `State:` to `Validated YYYY-MM-DD`.

---

## When there is no certificate — validate the DoD directly

A task may have a `Definition of done` checklist but no authored certificate (certificates
were skipped at planning time, or the task is not from spec-planner). Do not skip
validation — derive the obligations on the fly and discharge them the same way:

1. Treat each `- [ ]` item in the task's `## Definition of done` as one obligation, in
   order; the final `Reviewable:` item is the last obligation.
2. For each, name the evidence a validator would collect (read the relevant `file:line`,
   run the relevant test, trace the relevant input) — then collect it, exactly as Phase 2.
3. Apply the same regression check (Phase 3) over the code the task touched, and derive the
   same `DONE / PARTIAL / NOT_DONE` verdict.
4. Record the result inline (in the build log or alongside the task) rather than in a
   certificate file. Consider proposing that `done-certificates` author a real certificate
   if this task is one others depend on.

If the task has **neither** a certificate **nor** a definition of done, validation has
nothing to check — flag it as a defect in the plan (a spec-planner task without a DoD is
a defect by that skill's own checklist) rather than passing it by default.

---

## Worked discharge (abbreviated)

Given obligation `O1 — A wrong passphrase is rejected and the vault stays locked` whose
authored evidence reads *"read `src/auth/lock.ts` around the verify branch; confirm it
returns before any `vault.unlock()` when verification fails. Run `lock.test.ts › rejects
wrong passphrase` — expect PASS"* and check *"resolve `verify()` — confirm it is the
imported crypto `verify`, not `crypto.subtle.verify`"*:

```
O1 — collect: read src/auth/lock.ts:31–38 → on verify() === false the function returns
     before vault.unlock() (line 40). Ran `lock.test.ts › rejects wrong passphrase` → PASS.
   - check: verify() at lock.ts:33 resolves to import { verify } from "./crypto"
     (step 4, imported) — not the global crypto.subtle.verify. No shadowing.
   - Status: SATISFIED
```

Repeat for `O2…On`, trace the named regression caller, then:

```
VERDICT: DONE
CONFIDENCE: high
SUMMARY: O1–O5 all SATISFIED with evidence; the entries.ts caller of db.open() is PRESERVED.
```

---

## What NOT to do

- **Don't mark an obligation `SATISFIED` without its evidence.** No file location, test
  result, or trace means `UNVERIFIED` — never `SATISFIED`.
- **Don't author or rewrite the protocol.** You discharge the obligations as written. If
  an obligation is wrong or missing, note it in the summary; do not silently change it.
- **Don't fabricate a result.** Run the named test; do not guess its outcome.
- **Don't pass a task by default when validation cannot run.** `UNVERIFIED` obligations
  yield `PARTIAL`, not `DONE`. The downstream effect (re-dispatch, or surface to the user)
  is spec-builder's to decide.
- **Don't expand the contract.** The obligations are exactly the DoD items. Quality
  concerns outside the DoD are notes in the summary, not new obligations.
- **Don't declare the verdict first.** Derive it from the statuses and the regression check.
