# Review Template R3: Change Spec vs Implemented Code

This template tells you exactly what to do at each step. Follow it literally. Do not skip steps. Do not summarize — write out each step's result before moving to the next. It is a semi-formal certificate procedure: state premises, extract the proposed changes as concrete code-level expectations, resolve each against the code through a fixed sequence, then deliver an implementation-status verdict by rubric.

Use when validating whether a change spec's proposed delta has actually shipped — for example before flipping its `Status` from `Accepted` to `Implemented`, or before a merge. The change spec is the source of truth for what *should* exist; the code is checked against it. The answer is one of NONE, PARTIAL, or IMPLEMENTED, and for PARTIAL the template enumerates the gaps.

## Procedure

**Step 1: State premises.**
Write exactly three lines:

```
P1: The change spec [path] proposes [list the concrete, code-level expectations it implies — new/changed entities and fields, new routes/contracts, migrations, behavior changes].
P2: The implementing code lives in [paths / modules in scope — start from the change spec's Implementation notes].
P3: The question under test: is each proposed change present in the current branch? (Status is Implemented only if all are.)
```

**Step 2: Expectation extraction.**
Build the checklist of code-level expectations from the change spec, drawing on every source it carries. The `Proposed changes` blocks are written in spec voice — translate each into the code change it implies. Write one row per expectation:

```
EXPECTATION [n]: [what the code must do or have — concrete and checkable]
  SOURCE: [Type changes $def | Implementation notes step N | Proposed changes block → page → heading]
```

Pull from each source:

- **Type changes fragment** — every new `$def` is a new type/entity the code must define; every added field on a modified entity is a field the code must carry.
- **Implementation notes** — each `file:line` pointer and each numbered step is a concrete edit the code must show (a new store, a wired-up call site, a migration).
- **Proposed changes prose** — any behavior, route, contract, or limit the merged-form prose describes is an expectation, even when Implementation notes omit it.

**Step 3: Implementation resolution.**
For EACH expectation, locate its counterpart in code using this exact sequence. Write out each sub-step:

1. Is there a symbol (type, field, function, route, store, migration) matching the expectation in the module the Implementation notes name? If yes → compare shape, then STOP.
2. Is it defined elsewhere in the package? Search. If yes → compare shape, then STOP.
3. Is it provided by a dependency or framework (e.g. a route registered via config, a column added by an ORM migration)? If yes → resolve there, then STOP.
4. None of the above → ABSENT.

Classify each expectation:

```
EXPECTATION [n]: [text]
  → PRESENT at [file:line], matches the proposed shape: IMPLEMENTED
  → PRESENT at [file:line], but [shape / name / call site / migration differs from the proposal]: DIVERGENT — [detail]
  → no counterpart in code: ABSENT
```

**Step 4: Status determination.**
Tally the results:

```
IMPLEMENTED: [count] · DIVERGENT: [count] · ABSENT: [count]  (of [total] expectations)
```

Apply this rubric:

- NONE: every expectation is ABSENT.
- PARTIAL: at least one expectation is IMPLEMENTED and at least one is ABSENT or DIVERGENT.
- IMPLEMENTED: every expectation is IMPLEMENTED (no ABSENT, no DIVERGENT).

**Step 5: Gap list.**
For each ABSENT or DIVERGENT expectation, write:

```
GAP: [the expectation]
  STATUS: [ABSENT | DIVERGENT]
  WHAT'S MISSING: [the specific code to add or correct]
  SOURCE: [where in the change spec this expectation came from]
```

If the status is IMPLEMENTED, write: "No gaps — every proposed change is present in the code."

**Step 6: Verdict.**
Write exactly:

```
IMPLEMENTATION STATUS: [NONE | PARTIAL | IMPLEMENTED]
CONFIDENCE: [high | medium | low]
COMPLETION: [n of m expectations implemented]
SUMMARY: [one sentence explaining the status]
NEXT STEPS:
- [per gap: the code change that closes it; or, if IMPLEMENTED, the lifecycle move]
```

When the status is IMPLEMENTED, the next step is the lifecycle move: the change spec is ready to have its `Status` flipped to `Implemented` and then merged (run R1 and the merge procedure in [`../../spec-creator/references/change-specs.md`](../../spec-creator/references/change-specs.md)). When PARTIAL or NONE, the next steps are the code changes that close the gaps — the change spec stays at `Accepted`.

## Worked Example

**Input:** The change spec `.specs/changes/2026-05-21-add_tagging_to_entries.md`. Its `Type changes` fragment adds a `Tag` entity (`id`, `name`, `createdAt`) and adds `tagIds` to `Entry`. Its `Implementation notes` read: (1) add the `tags` store in `src/db/schema.ts` (bump version, `onupgradeneeded`); (2) add the `Tag` type + parser in `src/domain/tag.ts`; (3) wire the tag picker into the editor toolbar at `src/ui/Toolbar.svelte:40`. The code has `src/domain/tag.ts` (Tag type with all three fields) and a `tags` store in `src/db/schema.ts` (version bumped), but `Entry` has no `tagIds` field and `Toolbar.svelte` has no tag picker.

**Correct output:**

```
P1: The change spec proposes a Tag entity (id, name, createdAt), a tagIds field on Entry, a tags object store, and a tag picker in the editor toolbar.
P2: The implementing code lives in src/domain/ (tag.ts, entry.ts), src/db/schema.ts, and src/ui/Toolbar.svelte.
P3: The question under test: is each proposed change present in the current branch?

EXPECTATION EXTRACTION:
EXPECTATION 1: a Tag type with fields id, name, createdAt.
  SOURCE: Type changes $def Tag; Implementation notes step 2.
EXPECTATION 2: Entry carries a tagIds field.
  SOURCE: Type changes (modified Entry); Proposed changes → 01-domain-model.md → Entities.
EXPECTATION 3: a tags object store in the IndexedDB schema, with a version bump.
  SOURCE: Implementation notes step 1; Proposed changes → 04-persistence-and-export.md.
EXPECTATION 4: a tag picker wired into the editor toolbar.
  SOURCE: Implementation notes step 3.

IMPLEMENTATION RESOLUTION:
EXPECTATION 1: Tag type.
  1. Symbol Tag in src/domain/tag.ts? YES — fields id, name, createdAt. Shape matches.
  → PRESENT at src/domain/tag.ts:6: IMPLEMENTED.
EXPECTATION 2: Entry.tagIds.
  1. Field tagIds on Entry in src/domain/entry.ts? NO.
  2. Defined elsewhere? NO. 3. From a dependency? NO.
  → ABSENT.
EXPECTATION 3: tags store + version bump.
  1. tags store in src/db/schema.ts with bumped version? YES.
  → PRESENT at src/db/schema.ts:22: IMPLEMENTED.
EXPECTATION 4: tag picker in toolbar.
  1. Tag picker component or call in src/ui/Toolbar.svelte? NO.
  2. Elsewhere in src/ui/? NO. 3. From a dependency? NO.
  → ABSENT.

STATUS DETERMINATION:
IMPLEMENTED: 2 · DIVERGENT: 0 · ABSENT: 2  (of 4 expectations)
→ PARTIAL.

GAP LIST:
GAP: Entry.tagIds
  STATUS: ABSENT
  WHAT'S MISSING: add a tagIds field to the Entry type in src/domain/entry.ts and to its parser.
  SOURCE: Type changes (modified Entry); Proposed changes → 01-domain-model.md → Entities.
GAP: tag picker in toolbar
  STATUS: ABSENT
  WHAT'S MISSING: wire a tag picker into src/ui/Toolbar.svelte around line 40, per Implementation notes step 3.
  SOURCE: Implementation notes step 3.

IMPLEMENTATION STATUS: PARTIAL
CONFIDENCE: high
COMPLETION: 2 of 4 expectations implemented
SUMMARY: The Tag type and tags store have shipped, but Entry.tagIds and the toolbar tag picker are not yet in the code.
NEXT STEPS:
- Add tagIds to the Entry type and parser in src/domain/entry.ts.
- Wire the tag picker into src/ui/Toolbar.svelte:40.
- Re-run R3 once both land; on IMPLEMENTED, flip the change spec to Implemented and proceed to merge (R1 + merge procedure).
```

## Common Mistakes to Avoid

1. **Extracting from prose only.** The `Proposed changes` blocks are spec-facing prose; on their own they undercount the work. Derive expectations from the `Type changes` fragment and `Implementation notes` too — those name the entities, fields, migrations, and call sites the code must show.
2. **Calling it Implemented too early.** Entities existing is not the whole change. A migration not run, a call site not wired, or a field not added means PARTIAL — every expectation must be PRESENT for IMPLEMENTED.
3. **Trusting the obvious symbol.** A matching name is not proof; compare the *shape* (fields, signature, store version, route path) against what the change spec proposes. A shape that differs is DIVERGENT, not IMPLEMENTED.
4. **Vague gaps.** Each gap must name the concrete code to add or correct, anchored to a `file:line` or module — not "tagging isn't finished".
5. **Editing instead of suggesting.** The reviewer reports status and the gaps; it does not implement the missing code or flip the change spec's status unprompted. Surface the next steps and let the user act.
