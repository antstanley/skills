# Semi-formal reasoning for done certificates

A done certificate is a **semi-formal reasoning certificate**: a structured evidence chain that sits between informal chain-of-thought and a fully formal proof. Rather than asserting a conclusion, it forces explicit checkpoints — premises, claims, evidence, a derived verdict — so that whoever runs it cannot skip a case or make an unsupported claim. This file is the self-contained method the skill applies; the certificate you author tells the validator to run these procedures against the code.

(The method is the one introduced for code analysis as "semi-formal reasoning" — structured prompting templates that act as certificates. It stays in natural language rather than a proof language like Lean or Coq: no automated proof checker, but far less translation overhead, and the structure still bars skipped cases and unsupported claims.)

---

## The certificate shape

Every semi-formal certificate has the same skeleton, regardless of what it certifies:

- **Definition** — what the conclusion *means* in this context (here: what `DONE` means for this task).
- **Premises** — the explicit assumptions: what the work touches, what the goal is, what must not break.
- **Claims** — specific, checkable predictions, each requiring a traceable justification ("test X passes because path Y produces Z"), not a hunch.
- **Evidence** — concrete code locations, test results, and execution traces backing each claim.
- **Conclusion** — a verdict derived logically from the documented evidence, with the rubric stated.

A done certificate instantiates this shape with one claim (obligation) per definition-of-done item. The two checkpoints below are what make the evidence trustworthy — apply them whenever an obligation makes a behavioral claim.

---

## Checkpoint 1 — Function resolution

For each function or method call an obligation's claim depends on, determine *which definition is actually invoked* before reasoning about its behavior. Name shadowing (a local, a module-level definition, an import, and a builtin sharing one name) is the classic source of confidently-wrong verification. Resolve each call with this exact sequence, stopping at the first match:

1. Is there a **local variable or parameter** with this name in the current function? If yes → that's what's called. STOP.
2. Is there a definition with this name in the **enclosing class**? If yes → STOP.
3. Is there a definition with this name at **module level** (same file, top-level)? If yes → STOP.
4. Is this name **imported**? If yes → trace the import to its source. STOP.
5. Is this a **language builtin**? If yes → STOP.
6. None of the above → flag as **UNRESOLVED**.

If a match is found *and* a later step would also match (e.g. a module-level function shares a name with a builtin), record it explicitly: **"NAME SHADOWING: `<name>` at `<scope>` shadows `<what it shadows>`."** A certificate obligation's `Checks` field names the calls a validator must resolve this way and the shadow to watch for.

---

## Checkpoint 2 — Execution trace and regression

**Execution trace.** For a behavioral claim, pick one concrete input and write 3–5 steps showing what happens, each step a concrete value or state change — not "processes the input". This is the evidence that a claim actually holds for a real case:

```
input → step → step → step → result
```

**Regression check.** A task that modifies existing code must not break code that depends on the old behavior. For each modified unit, find one downstream caller and trace that it still works:

```
<caller> calls <modified unit> with <typical input> → still produces <expected output>: PRESERVED
```

If behavior would break, write `REGRESSION: <caller> would now get <wrong result> because <reason>.` If no caller is visible in the available context, write that explicitly — an empty regression check is acceptable *only* when stated, never by silence.

---

## Verdict, derived not declared

The conclusion follows mechanically from the claim statuses and the regression check:

- **NOT_DONE** — any load-bearing obligation is `UNSATISFIED`, or the regression check found a `REGRESSION`.
- **PARTIAL** — every obligation is `SATISFIED` except one or more `UNVERIFIED` (the context could not prove them), and no regression.
- **DONE** — every obligation `SATISFIED`, regression `PRESERVED`, evidence sufficient to verify each.

`CONFIDENCE` (high / medium / low) reflects how complete the evidence was — could every named test run, every caller be traced — not how done the work is hoped to be. A `DONE` verdict alongside any non-`SATISFIED` obligation is malformed.

---

## Common mistakes

1. **Skipping function resolution.** Do not assume a call refers to the obvious definition; run the 5-step sequence whenever behavior depends on it.
2. **Marking a claim satisfied without evidence.** No file location, test result, or trace means `UNVERIFIED`, never `SATISFIED`.
3. **Empty regression checks.** "No regressions" is acceptable only after checking at least one downstream caller, or after stating that none is in scope.
4. **Vague traces.** Each step shows a concrete value or state change, not "handles it".
5. **Declaring the verdict.** Derive it from the statuses; never decide `DONE` first and back-fill.
