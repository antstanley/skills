# Semi-formal review method

The self-contained method this skill applies. It is the semi-formal certificate
method — structured templates that act as a certificate: premises, claims, evidence,
a derived verdict — consolidated from the `reasoning-semiformally` plugin and pointed
at one question: **does this implementation correctly and completely do what its task
asked, without breaking what it touched?**

A review is *not* a vibe check. It is a short certificate whose verdict is *derived*
from explicit checkpoints, never declared up front. The structure bars the two failure
modes strong reasoners still fall into on real diffs — name shadowing / scope
ambiguity, and calling a symptom-fix a root-cause fix.

---

## The certificate shape

Every semi-formal certificate has the same skeleton, whatever it certifies:

- **Premises** — what the change touches, what it was meant to do, what must not break.
- **Claims** — specific, checkable predictions, each needing a traceable justification
  ("test X passes because path Y produces Z"), not a hunch.
- **Evidence** — concrete code locations, test results, and execution traces backing each claim.
- **Conclusion** — a verdict derived logically from the documented evidence, against a stated rubric.

The method stays in natural language rather than a proof language: no automated
checker, far less translation overhead, and the structure still bars skipped cases and
unsupported claims.

> **Vendored copy — keep in sync.** This is the *validate/review* side of the method, used by
> both `semi-formal-review` and `validate-done-certificate` in this plugin. The *author* side is
> a sibling vendored copy at `spec-planner/skills/done-certificates/references/semiformal-method.md`.
> The two ends of the handoff must agree on the **5-step function-resolution sequence** and the
> verdict rubrics; if you edit either here, mirror it in that copy (and ideally upstream in the
> `reasoning-semiformally` plugin), or a certificate authored against one will be discharged
> against a different method.

---

## The procedure

Run this procedure on every review, regardless of which LLM or agent executes it. There
is no compact or "strong reasoner" shortcut — the structure is the point, and the same
explicit steps bar the same failure modes whatever model is reasoning.

Follow these steps literally. Do not skip steps. Write out each step's result before
moving on — do not summarize.

**Step 1 — Premises.** Write exactly three lines:

```
P1: The change modifies [every file and function touched].
P2: The task asked the change to [one sentence: what it should accomplish — from the task's Produces / Steps].
P3: Must not break [one sentence: existing behavior that must be preserved].
```

**Step 2 — Function resolution.** For EACH function call in the changed lines, resolve
it with this exact sequence, stopping at the first match:

1. Local variable or parameter with this name in the current function? If yes → STOP.
2. Definition with this name in the enclosing class? If yes → STOP.
3. Definition at module level (same file, top-level)? If yes → STOP.
4. Is the name imported? If yes → trace the import to its source. STOP.
5. Is it a language builtin? If yes → STOP.
6. None of the above → flag as `UNRESOLVED`.

If a match is found *and* a later step would also match, record it:
`NAME SHADOWING: <name> at <scope> shadows <what it shadows>.`

**Step 3 — Execution trace.** Pick one concrete input. Write 3–5 steps, each a concrete
value or state change, not "processes the input":

```
input → step → step → step → result
```

For a fix, trace before and after. For a new feature, trace the primary path the task's
`Produces` line promises.

**Step 4 — Regression check.** For each unit the change modified, find one downstream
caller and trace that it still works:

```
<caller> calls <modified unit> with <typical input> → still produces <expected output>: PRESERVED
```

If behavior would break: `REGRESSION: <caller> would now get <wrong result> because <reason>.`
If no caller is visible in scope, say so — an empty regression check is acceptable only
when stated, never by silence.

**Step 5 — Edge cases.** List 1–3 inputs the change does not handle, or
"No unhandled edge cases identified."

**Step 6 — Verdict.** Derive it; do not declare it:

- **BUGGY** — Step 2 found unresolved shadowing that changes behavior, OR Step 4 found a
  regression, OR Step 3 shows the change does not do what the task asked.
- **CONCERNS** — Step 5 found edge cases that could fail, OR Step 2 found shadowing that
  is risky but may not change behavior, OR the change fixes a symptom not the root cause.
- **LIKELY_CORRECT** — all steps passed but the available context is incomplete (a caller
  could not be traced, a test could not be run).
- **CORRECT** — all steps passed and the context was sufficient to verify fully.

```
VERDICT: [CORRECT | LIKELY_CORRECT | CONCERNS | BUGGY]
CONFIDENCE: [high | medium | low]
SUMMARY: [one sentence explaining the verdict]
```

---

## Worked example

**Input:** a patch that changes `src/utils/text.ts` line 42 from `return format(value, spec)`
to `return globalThis.format(value, spec)` to fix lazy-string formatting.

```
P1: The change modifies src/utils/text.ts, function formatLazy(), line 42.
P2: The task asked formatLazy() to return a formatted string, not a lazy wrapper.
P3: Must not break existing callers of formatLazy() that expect a finished string.

FUNCTION RESOLUTION:
- format() on line 42 (before): local? no. enclosing class? no. module level? YES —
  text.ts defines format() at line 12.
  → NAME SHADOWING: module-level format() at line 12 shadows the intended global.
  → Before: line 42 called the module-level lazy format(), not the global.
- globalThis.format (after): explicit global reference bypasses all scopes.

EXECUTION TRACE:
Before: formatLazy("hi {}", "x") → module format() wraps lazily → returns LazyString, not "hi x".
After:  formatLazy("hi {}", "x") → global format("hi {}", "x") → returns "hi x".

REGRESSION CHECK:
- src/render/template.ts:render() calls formatLazy() expecting a string → now gets a
  finished string: PRESERVED.

EDGE CASES:
- formatLazy() with no spec: global format raises TypeError, same as before. Not new.

VERDICT: CORRECT
CONFIDENCE: high
SUMMARY: The change bypasses name shadowing by referencing the global explicitly; the one downstream caller is preserved.
```

---

## Composing with the other skills

- A `BUGGY` verdict that needs the *exact* offending line localized: switch to fault
  localization — trace the buggy input from the entry point, and for each suspicious line
  apply the sufficiency test ("if I fix ONLY this line, does the symptom go away? yes →
  root cause; no → contributor only").
- Comparing two candidate fixes: run the procedure on each and compare per-test outcomes.
- This skill verifies *correctness*. Confirming the task's **definition of done** is met
  is the separate job of `validate-done-certificate`, which reuses this same procedure
  against a different rubric (`DONE / PARTIAL / NOT_DONE`).

## Common mistakes

1. **Skipping function resolution.** Run the 5-step sequence whenever behavior depends on a call; do not assume the obvious definition.
2. **Stopping at "contributor."** The sufficiency test is mandatory when localizing — a suspicious line is not yet a root cause.
3. **Empty regression checks.** "No regressions" is valid only after tracing one caller, or after stating none is in scope.
4. **Vague traces.** Each step shows a concrete value or state change, not "handles it".
5. **Declaring the verdict.** Derive it from the checkpoints; never decide first and back-fill.
