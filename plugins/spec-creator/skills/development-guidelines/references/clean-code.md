# Clean Code — core (language-agnostic)

The sections below are the language-independent parts of a development-guidelines page rendered in Clean Code style. Drop them into the page in the order shown in the SKILL workflow, adapting each to the repo. Spec voice throughout (present tense, no marketing words); keep it that way.

Clean Code is a readability-first discipline (after Robert C. Martin and the "simple design" tradition). Its design priority is **maintainability — code is read far more often than it is written, so optimize for the reader.** The whole style follows from one habit: express intent in the code itself, so a later reader needs no commentary to understand *what* and no surprise to understand *how*.

> **Relationship to Tiger Style.** Clean Code and Tiger Style disagree on load-bearing points — exceptions vs. errors-as-data, deep abstraction vs. explicit linear flow, tests vs. assertions as the primary correctness net. A repo adopts one. Do not blend them silently; a deviation needs a written reason in the change description.

The per-language specifics — the `### Error handling in <language>` subsection plus this style's code-style and naming emphases — live in the language overlays: [`typescript-clean.md`](typescript-clean.md), [`javascript-clean.md`](javascript-clean.md), [`rust-clean.md`](rust-clean.md), [`python-clean.md`](python-clean.md). The neutral language substrate (toolchain, formatting, naming case, testing, documentation) lives in the base files ([`typescript.md`](typescript.md), etc.).

---

## `<Style>` — the pervasive style

> Heading on the page: `## Clean Code — the pervasive style`

This project adopts **Clean Code** as its pervasive coding style. This is the default, not a recommendation. Deviations require a written reason in the change description.

The short form: **make the code reveal its intent.** A reader should understand a unit from its name and shape without tracing it. Prefer clarity to cleverness.

The design priority — **readability and maintainability first** — applies throughout. When a clever construction and a clear one compete, the clear one wins even at a cost in lines.

Load-bearing principles:

- **Meaningful names.** Intention-revealing, pronounceable, searchable. The name states what a thing is or does; no encodings, no abbreviations that need a key.
- **Small functions that do one thing.** A function operates at a single level of abstraction. Few parameters (prefer 0–2; avoid boolean flag arguments — they signal a function doing two things). No hidden side effects; separate commands from queries.
- **Single responsibility.** A module or class has one reason to change. High cohesion, low coupling. Depend on abstractions, not concretions (SOLID).
- **No duplication (DRY).** Duplicated logic has one home — tempered by judgment: prefer a little duplication over the wrong abstraction.
- **Self-documenting code; comments are a last resort.** A comment is often a failure to express something in code. Good comments explain *why* or warn of consequences; they never paraphrase the code, and commented-out code is deleted.

---

## Error handling and boundaries

> Heading on the page: `## Error handling and boundaries`. This is Clean Code's analog of Tiger Style's "Defensive coding and assertions" slot.

### Where validation lives

Validate where data crosses from a place you do not control into one you do, and translate the failure into the repo's own vocabulary at that line.

| Boundary | What to validate | How |
|---|---|---|
| External request → handler | Body shape, sizes, IDs, enums | Schema validation against `canonical-types.schema.json` (or its derived types) before the handler sees the data |
| Third-party API → core | Status, content type, body shape | Access the API through a repo-owned wrapper that validates the response and translates its errors |
| Disk / blob read | Round-trip integrity | Re-validate on read; raise a typed error on mismatch |
| Wire decode | Frame discriminant + payload shape | Reject unknown frames with a typed error; do not best-effort parse |

> The per-language `### Error handling in <language>` subsections (one per selected language, from each `<language>-clean.md` overlay) slot in here, between "Where validation lives" and "Use exceptions".

### Use exceptions, not return codes

- Signal failure with exceptions, not error codes a caller may forget to check. (In languages without exceptions, use the language's `Result`/`Optional` type — see the per-language overlay.)
- Write the `try/catch/finally` first; it defines the scope of what can fail.
- Throw exceptions carrying enough **context** to locate the cause — the operation that failed and why. Never log a secret in that context.
- **Do not return `null`; do not pass `null`.** Return an empty collection, a null-object, or an `Optional`/`Result`. A null that escapes is a future crash with no context.

### Make intent explicit

- Prefer types that make an invalid value hard to construct (value objects, enums/tagged unions over free strings) so fewer states need runtime guarding.
- When behaviour is hard to read, the fix is a better name or a smaller function — not a comment.
- Match exhaustively over enums/tagged unions; the unexpected case raises rather than falling through.

---

## Limits and bounds

> Heading on the page: `## Limits and bounds`. Clean Code does not emphasize hard bounds the way Tiger Style does, but the meta-rule survives.

Magic numbers are replaced with **named constants** that state their meaning. Any genuine limit — payload sizes, retry counts, timeouts, collection cardinality — is a named constant referenced wherever it applies, not a literal. The *existence* of a limit is the rule here; concrete values are an app concern and live in the per-package specs.

---

## Version control

> Heading on the page: `## Version control`. **Shared with Tiger Style — not a code-style concern.** Reuse the version-control blocks from [`tiger-style.md`](tiger-style.md) (shared core + jujutsu/git variants) unchanged, selecting the variant per the skill's Version control parameter.

---

## Repository hygiene

> Heading on the page: `## Repository hygiene`. Adapt paths to the repo's actual layout.

- **`.specs/`** is the canonical home for specs and decisions.
- **Local, untracked operator data** lives in a gitignored directory; never commit environment-specific config or secrets.
- **The pre-push hook** runs format-check, lint, and the fast test tier. CI re-runs the same plus the slow tier. (Clean Code leans on the test suite, rather than assertions, as its safety net — keep it fast and green.)
- **Generated code is checked in** and grep-able; a CI job regenerates and fails the build if the checked-in output drifts.

---

## Guidelines for AI agents

> Heading on the page: `## Guidelines for AI agents`. Emphasis on where agents slip against this style. Add language-specific slips from the per-language overlay files.

1. **Optimize for the reader.** Prefer the clear construction; do not introduce cleverness to save lines.
2. **Keep functions small and single-purpose.** When a function grows a second level of abstraction, extract it with an intention-revealing name.
3. **No null in, no null out.** Return empty collections or `Optional`/`Result` types.
4. **Express intent in names, not comments.** Do not add a comment that restates the code; if a comment is needed to explain *what*, rename instead.
5. **Tests are first-class.** A change ships with tests that are Fast, Independent, Repeatable, Self-validating, and written with the change (FIRST). "Compiles" is not "works" — run the tests and report the actual output.
6. **No duplication.** Before adding logic, check whether it already has a home.
7. **Stay inside the architecture.** Depend on abstractions; do not reach across a boundary a wrapper already owns.
8. **Errors are raised with context, never swallowed.** Every catch handles or re-raises with more information.
9. **Do not run destructive version-control operations without explicit confirmation.**
10. **Do not skip pre-commit / pre-push hooks.** If a hook fails, fix the underlying issue.

---

## Definition of done

> Heading on the page: `## Definition of done`. Append per-language items (test-runner names, format/lint commands) from the language base files.

A change is done when:

- The behaviour is covered by tests that follow FIRST; new validation paths have negative-space tests.
- Functions are small and single-purpose; names reveal intent without comments.
- No duplicated logic was introduced.
- Magic numbers are named constants.
- Errors are raised with context; no `null` is returned or passed for a domain value.
- Format, lint, and the test suite pass locally.
- If domain types changed, `canonical-types.schema.json` is updated and any generated types are regenerated.
- The commit description states the *why*.
