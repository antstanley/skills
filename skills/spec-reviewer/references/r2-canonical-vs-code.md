# Review Template R2: Canonical Spec vs Implemented Code

This template tells you exactly what to do at each step. Follow it literally. Do not skip steps. Do not summarize — write out each step's result before moving to the next. It is a semi-formal certificate procedure: state premises, resolve every claim through a fixed sequence, classify each divergence, then deliver a verdict by rubric.

Use when reviewing a canonical spec page against the code it claims to describe. You are verifying spec-creator's core rule in both directions: every body claim maps to code that exists (no missing or incorrect implementations), and every significant code feature is captured in the spec (no unspec'd features).

## Procedure

**Step 1: State premises.**
Write exactly three lines:

```
P1: The spec page [path] claims [list the concrete, checkable claims — entities, fields, routes, contracts, lifecycles, limits].
P2: The implementing code lives in [paths / modules in scope].
P3: The spec rule under test: the body describes only what exists in the current branch (missing code = divergence, not "deferred").
```

**Step 2: Claim resolution (forward pass).**
For EACH concrete claim in the spec body, locate its code counterpart using this exact sequence. Write out each sub-step:

1. Is there a symbol (type, function, route, field, constant) with this name/shape in the module the page names? If yes → compare shape, then STOP.
2. Is it defined elsewhere in the package? Search. If yes → compare shape, then STOP.
3. Is it provided by a dependency or framework (e.g. a route registered via config, a field from an ORM base)? If yes → resolve there, then STOP.
4. None of the above → MISSING.

Classify each claim:

```
CLAIM [n]: [spec text — the claim being checked]
  → FOUND at [file:line], shape matches the spec: CONFORMS
  → FOUND at [file:line], but [field / return type / route path / limit value differs]: MISMATCH — [detail]
  → no counterpart in code: MISSING
```

**Step 3: Coverage resolution (reverse pass).**
For each significant exported or public code symbol in scope (entity, route, public API, persisted field, named limit), check whether the spec body describes it. Write:

```
SYMBOL [file:line]: [name]
  → described at [spec page → heading]: SPEC'D
  → not described anywhere in the spec body: UNSPEC'D — [what the spec omits]
```

Skip private helpers and incidental internals; the reverse pass is for the surface the spec is meant to define.

**Step 4: Divergence classification.**
For each MISSING, MISMATCH, or UNSPEC'D result, classify it and assign the spec-creator remedy. Write:

```
DIVERGENCE: [the claim or symbol]
  TYPE: [MISSING impl | INCORRECT impl | UNSPEC'D feature]
  SOURCE OF TRUTH: [does the code or the spec hold the intended reality? state which and why]
  SUFFICIENCY TEST: if this were the only change made, would the spec and code agree? [yes/no — if no, what else diverges]
  REMEDY:
    - code is right, spec is stale → update the body to match the code (spec-creator authors it)
    - spec is right, code is absent → DIVERGENCE: flag to user; route to an Open question or a change spec; do NOT edit the body to pretend it exists
    - genuinely undecided → Open question
```

The middle case is the binding one: spec-creator's core principle says a body claim with no code is a divergence to surface, never to soften.

**Step 5: Edge cases.**
List 1–3 claims you could only partially verify — dynamic registration, generated code, behavior behind a feature flag, anything the provided context did not let you trace fully. If none, write: "All claims verifiable from the provided context."

**Step 6: Verdict.**
Use this decision rubric:

- DIVERGES: Step 2 found any MISSING implementation of a body claim, OR any MISMATCH.
- CONCERNS: only UNSPEC'D features in Step 3, OR claims verifiable only partially in Step 5.
- LIKELY_CONFORMS: every checked claim conforms, but the code context was incomplete (you could not see all modules in scope).
- CONFORMS: every body claim maps to code and no significant symbol is unspec'd.

Write exactly:

```
VERDICT: [CONFORMS | LIKELY_CONFORMS | CONCERNS | DIVERGES]
CONFIDENCE: [high | medium | low]
SUMMARY: [one sentence explaining the verdict]
DIVERGENCES:
- [TYPE] [claim or symbol] → [remedy]
```

## Worked Example

**Input:** `docs/editor/specs/01-domain-model.md` claims three entities: `Entry` (with fields `id`, `body`, `createdAt`, `updatedAt`), `Workspace`, and `Tag`. The code in `src/domain/` defines `entry.ts` (fields `id`, `body`, `createdAt` — no `updatedAt`) and `workspace.ts`. There is no `tag.ts`. The code also defines `src/domain/draft.ts` (a `Draft` entity) that the spec does not mention.

**Correct output:**

```
P1: The spec page docs/editor/specs/01-domain-model.md claims entities Entry (id, body, createdAt, updatedAt), Workspace, and Tag.
P2: The implementing code lives in src/domain/ (entry.ts, workspace.ts, draft.ts).
P3: The spec rule under test: the body describes only what exists in the current branch.

CLAIM RESOLUTION (forward pass):
CLAIM 1: Entry entity with fields id, body, createdAt, updatedAt.
  1. Symbol Entry in src/domain/entry.ts? YES — fields id, body, createdAt. No updatedAt.
  → FOUND at src/domain/entry.ts:8, but updatedAt is absent: MISMATCH — spec claims a field the type lacks.
CLAIM 2: Workspace entity.
  1. Symbol Workspace in src/domain/workspace.ts? YES — shape matches.
  → FOUND at src/domain/workspace.ts:5: CONFORMS.
CLAIM 3: Tag entity.
  1. Symbol Tag in the named module? NO.
  2. Defined elsewhere in src/domain/? NO. 3. From a dependency? NO.
  → MISSING.

COVERAGE RESOLUTION (reverse pass):
SYMBOL src/domain/entry.ts:8: Entry → described at 01-domain-model.md → Entities: SPEC'D.
SYMBOL src/domain/workspace.ts:5: Workspace → described: SPEC'D.
SYMBOL src/domain/draft.ts:6: Draft → not described anywhere: UNSPEC'D — the spec omits the Draft entity entirely.

DIVERGENCE CLASSIFICATION:
DIVERGENCE: Entry.updatedAt
  TYPE: INCORRECT impl (spec over-claims a field).
  SOURCE OF TRUTH: unclear — either the field was dropped from code or never added. Ask the user.
  SUFFICIENCY TEST: fixing only this still leaves Tag missing and Draft unspec'd → no.
  REMEDY: if updatedAt was intentionally dropped, remove it from the body; if it should exist, this is a divergence to flag (code change, not a spec edit).
DIVERGENCE: Tag entity
  TYPE: MISSING impl.
  SOURCE OF TRUTH: the spec body describes Tag but no code backs it.
  SUFFICIENCY TEST: independent of the other two → no.
  REMEDY: DIVERGENCE per core principle — flag to user; move Tag to an Open question or draft a change spec for it; do NOT leave it asserted in the body.
DIVERGENCE: Draft entity
  TYPE: UNSPEC'D feature.
  SOURCE OF TRUTH: the code (Draft exists and ships).
  SUFFICIENCY TEST: independent → no.
  REMEDY: add a Draft entity block to the body (spec-creator authors it), with a Decision recording why it exists.

EDGE CASES:
- Entry.body type (string vs rich-text node) could not be fully verified without reading the serializer; flagged for confirmation.

VERDICT: DIVERGES
CONFIDENCE: high
SUMMARY: The page over-claims Entry.updatedAt, describes a Tag entity the code never shipped, and omits the Draft entity the code defines.
DIVERGENCES:
- INCORRECT impl: Entry.updatedAt → confirm intent, then remove from body or flag the code gap.
- MISSING impl: Tag → flag divergence; route to Open question or change spec.
- UNSPEC'D feature: Draft → add a body section for it.
```

## Common Mistakes to Avoid

1. **Trusting the obvious code symbol.** A spec claim and a same-named symbol are not proof of conformance — compare the *shape* (fields, return type, route path, limit value), not just the name.
2. **Softening a divergence.** When the body claims a feature the code lacks, the verdict is DIVERGES and the remedy routes to an Open question or change spec. "It's basically there" and "deferred" are exactly the outcomes spec-creator's core principle forbids.
3. **Empty reverse pass.** "The spec is complete" is acceptable only after checking that the significant code symbols in scope each appear in the body. If you did not trace the exports, say so and lower confidence.
4. **Editing instead of suggesting.** The reviewer surfaces issues and proposes the edit. Authoring the fix to a canonical page is spec-creator's job — hand back rather than rewriting unprompted.
5. **Vague verdicts.** Every issue in DIVERGENCES must name a concrete anchor (a path, a heading, a `file:line`, a field) and the edit that resolves it — not "some claims look off".
