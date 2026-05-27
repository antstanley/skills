# Done certificate template

A done certificate is a **semi-formal reasoning certificate** that serves as a task-specific *verification protocol*. This skill **authors** it; a separate **validating agent** runs it. It restates each definition-of-done item as a proof obligation, names the evidence a validator must collect and the checks it must run, and leaves the status and verdict blank — the premise → claim → evidence → conclusion shape and the function-resolution and regression checkpoints defined in [`semiformal-method.md`](semiformal-method.md), pointed at a task's definition of done instead of a diff.

Read this before Phase 2 and adapt it to the task — do not paste it verbatim.

---

## Blank-field conventions (authored → validated)

The certificate is written **blank** and discharged by someone else. When you hand it over, these fields carry their unverified placeholders; the validating agent replaces them.

| Field | As authored (this skill) | As discharged (validator) |
|---|---|---|
| `**State:**` | `Authored YYYY-MM-DD — unverified` | `Validated YYYY-MM-DD` |
| Obligation `Evidence to collect` | a precise instruction: *which* file:line to read, *which* test to run + expected result, *which* trace to produce | the evidence actually produced |
| Obligation `Status` | `☐ unverified` | `SATISFIED` \| `UNSATISFIED` \| `UNVERIFIED` |
| `Regression check` | the callers to trace, named; outcome blank | `PRESERVED` / `REGRESSION` per caller |
| `VERDICT` / `CONFIDENCE` / `SUMMARY` | empty (the rubric is present; the verdict is not) | derived from the statuses |

**Never** pre-fill a status, an evidence result, or the verdict when authoring. The certificate is the questions and the method; the validator supplies the answers.

---

## Verdict rubric (carried in the certificate, applied by the validator)

- **NOT_DONE** — any load-bearing obligation is `UNSATISFIED`, **or** the regression check found a `REGRESSION`.
- **PARTIAL** — every obligation is `SATISFIED` except one or more that are `UNVERIFIED` (the available context could not prove them), and no regression.
- **DONE** — every obligation `SATISFIED`, regression check `PRESERVED`, and the evidence sufficient to verify each (including the `Reviewable:` obligation).

`CONFIDENCE` (high / medium / low) reflects how complete the evidence was — could the validator run every named test, trace every caller. **A `DONE` verdict with any non-`SATISFIED` obligation is malformed.**

---

## Skeleton

```markdown
# Done Certificate — Task NN: <title>

**Task:** [NN-snake_case_task.md](../NN-snake_case_task.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored YYYY-MM-DD — unverified   <!-- validator sets: Validated YYYY-MM-DD -->

> This certificate is a verification protocol for Task NN. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task NN) ≡ every obligation O1…On below holds, each backed by the evidence the obligation
names (a file location, a test result, or an execution trace) — not by assertion.

## Premises

- **P1 — Goal.** <one sentence: what the task produces, from the task's `Produces` line>.
- **P2 — Obligations.** The task is done iff O1…On all hold. One Oi per definition-of-done
  item, in DoD order; On is always the `Reviewable:` item.
- **P3 — Invariants.** Must not break <existing behavior the task touches — the regression surface>.

## Obligations

- **O1 — <DoD item 1>.**
  - *Claim:* <the checkable condition this item asserts>.
  - *Evidence to collect:* <precise instruction — which file:line to read, which named test to
    run and the result to expect, which input to trace through which function>.
  - *Checks:* <task-specific resolution/regression checks — e.g. "resolve <call> at <file:line>;
    confirm it is <intended definition>, not <plausible shadow>". Omit if no scope-crossing calls.>
  - *Status:* ☐ unverified

- **O2 — <DoD item 2>.**
  - *Claim:* …
  - *Evidence to collect:* …
  - *Status:* ☐ unverified

- **On — <the task's `Reviewable:` line> (Reviewable).**
  - *Claim:* a reviewer can <concrete action> and observe <concrete result>.
  - *Evidence to collect:* <the command/screen to exercise and the output to observe>.
  - *Status:* ☐ unverified

## Regression check

For each module the task touched, the validator traces one downstream caller:

- <caller> calls <touched unit> with <input> → expect <output> : ☐ (PRESERVED / REGRESSION)

(Or, if the task touches no existing code: "No existing callers in scope — nothing to regress.")

## Residue

Notes for the validator: edge cases outside the DoD, follow-ups, anything the obligations do not
cover. These are not obligations — the DoD is the contract. (Or: "None noted at authoring.")

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐ <one sentence deriving the verdict from the statuses>
```

---

## Worked example — an authored (unverified) certificate

Task 01 of a journal-app plan: the passphrase lock. Its task file's definition of done:

```
## Definition of done
- [ ] A wrong passphrase is rejected and the vault stays locked
- [ ] The unlock attempt limit is a named constant, not a literal (dev-guidelines limits rule)
- [ ] Negative-space test: empty passphrase is rejected without touching the store
- [ ] Meets the repo definition of done (tests, lint/format, named-constant limits — see plan.md baseline)
- [ ] Reviewable: a reviewer enters a wrong then the correct passphrase and sees the vault unlock only on the correct one
```

The certificate this skill authors from it — every status and the verdict left blank for a validator:

```markdown
# Done Certificate — Task 01: passphrase lock

**Task:** [01-passphrase_lock.md](../01-passphrase_lock.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-05-24 — unverified

> Verification protocol for Task 01. A validating agent discharges it: collect each obligation's
> evidence, run its checks, set the Status, then derive the Conclusion by the rubric.

## Definition

DONE(Task 01) ≡ every obligation O1…O5 below holds, each backed by the evidence it names —
not by assertion.

## Premises

- **P1 — Goal.** The task produces a single-user passphrase lock that gates the vault: a
  reviewer can unlock the app only with the correct passphrase.
- **P2 — Obligations.** Done iff O1…O5 all hold; O5 is the Reviewable item.
- **P3 — Invariants.** Must not break the existing IndexedDB open path in `src/store/db.ts`,
  which the unlock flow now wraps.

## Obligations

- **O1 — A wrong passphrase is rejected and the vault stays locked.**
  - *Claim:* `unlock(wrong)` returns `false` and leaves `vault.state === "locked"`.
  - *Evidence to collect:* read `src/auth/lock.ts` around the verify branch; confirm the
    function returns before any `vault.unlock()` call when verification fails. Run
    `lock.test.ts › rejects wrong passphrase` — expect PASS.
  - *Checks:* resolve `verify()` in the unlock path — confirm it is the imported crypto
    `verify` (from `src/auth/crypto.ts`), not the global `crypto.subtle.verify`. Flag if shadowed.
  - *Status:* ☐ unverified

- **O2 — The unlock attempt limit is a named constant.**
  - *Claim:* the max-attempts value is a named constant, not a literal.
  - *Evidence to collect:* grep the attempt path in `src/auth/lock.ts` for numeric literals;
    confirm the limit is a `const` (e.g. `MAX_UNLOCK_ATTEMPTS`) and referenced by name. Run the
    `no-magic-numbers` lint rule — expect clean.
  - *Status:* ☐ unverified

- **O3 — Negative-space test: empty passphrase rejected without touching the store.**
  - *Claim:* `unlock("")` returns `false` and never calls `db.open()`.
  - *Evidence to collect:* run `lock.test.ts › empty passphrase short-circuits` — expect PASS,
    and confirm it spies on `db.open` asserting `not.toHaveBeenCalled()`. Trace `unlock("")` and
    confirm the empty-input guard returns before the store-open line.
  - *Checks:* resolve `db.open` to `src/store/db.ts:open`, not a same-named local.
  - *Status:* ☐ unverified

- **O4 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint/format clean, limits named.
  - *Evidence to collect:* run `npm test`, `npm run lint`, `npm run format:check` — expect all clean.
  - *Status:* ☐ unverified

- **O5 — Reviewable: wrong then correct passphrase, unlock only on the correct one.**
  - *Claim:* entering a wrong passphrase keeps the lock; entering the correct one unlocks the vault.
  - *Evidence to collect:* `npm run dev`, open `/`; enter `"nope"` → expect lock stays, error
    shown; enter the seeded passphrase → expect vault unlocks and the shell renders.
  - *Status:* ☐ unverified

## Regression check

- `src/store/db.ts:open()` is now called only after a successful unlock. Trace downstream caller
  `src/store/entries.ts:loadAll()` (calls `db.open()`): once unlocked, expect it still receives an
  open handle : ☐ (PRESERVED / REGRESSION)

## Residue

- Outside the DoD: no rate-limiting/backoff between attempts. Note for a later hardening task; not
  an obligation of Task 01.

## Conclusion

VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐
```

A validating agent later opens this, runs each obligation's evidence step, marks the statuses, and writes the verdict — e.g. `VERDICT: DONE` only if O1–O5 are all `SATISFIED` and the regression trace is `PRESERVED`.

---

## Notes on the blocks

- **One obligation per DoD item, in DoD order.** The mapping is one-to-one and checkable: every `- [ ]` in the task's definition of done becomes exactly one `Oi`, and the last DoD item (the `Reviewable:` line) is always the last obligation. A reader can diff the two lists.
- **`Evidence to collect` is an instruction, not a result.** It tells the validator exactly what to read, run, or trace — specific enough that two validators gather the same evidence. The result is the validator's to fill. For the "Meets the repo definition of done" obligation, the commands come from the repo's development guidelines (`docs/specs/development-guidelines.md` §Definition of done, per the plan's DoD baseline), not from the task's `Pointers` — the `npm test` / `npm run lint` in the worked example are this repo's commands, not a fixed template.
- **`Checks` is optional per obligation** — include it only when the claim depends on a function/method call that could be shadowed or resolved to the wrong definition, or on behavior that needs an execution trace. For a "lint passes" obligation there is nothing to resolve.
- **The regression check names callers at authoring time**; the validator traces them. Whenever the task modified existing code, name at least one downstream caller, or state explicitly that none is in scope.
- **Statuses and the verdict are blank at hand-off.** The certificate carries the rubric so the validator *derives* the verdict; this skill never pre-decides it.
- **Voice:** the certificate is an argument waiting to be discharged — short claim/evidence lines, no marketing words, no emoji, no exclamation points. Match spec-planner's voice.
