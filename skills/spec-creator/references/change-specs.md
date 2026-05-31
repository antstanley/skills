# Change specs

A **change spec** proposes changes to the canonical spec. The canonical spec describes what exists in the current branch; a change spec describes a delta that does not yet exist. When the change ships in code, the change spec is **merged** into the canonical spec and retired.

Read this when the user asks to propose, draft, or write up a change to an existing spec ("change spec", "propose a change to the spec", "spec out this change", "RFC for X"). It assumes you already know the canonical conventions in `SKILL.md`.

---

## How a change spec differs from a canonical spec

| Aspect | Canonical spec | Change spec |
|---|---|---|
| Subject | What exists now | What will change |
| Shape | Numbered directory of pages + schema sidecar | A **single** markdown document |
| Tense in body | Present ("the editor exposes…") | Future / imperative ("the editor will expose…", "add…") |
| Location | `docs/specs/`, `docs/<package>/specs/` | `docs/specs/changes/` |
| Naming | `NN-name.md`, kebab-case | `YYYY-MM-DD-short_snake_case_title.md` |
| Lifecycle | `Draft` → `Implemented` → `Deprecated` | `Proposed` → `Accepted` → `Implemented` → `Merged` |
| Aspirational content | Only in the closing block | Throughout the body — that is the point |

The "describes-what-exists" rule is **inverted** for change specs. A change spec's body is allowed — required — to describe code that does not yet exist. That is exactly why it is a separate document and not an edit to the canonical pages: the canonical pages must keep describing the current branch until the change actually lands.

---

## Naming and location

```
docs/specs/changes/YYYY-MM-DD-short_snake_case_title.md
docs/specs/changes/merged/        ← merged change specs move here
```

- **Date prefix** is the date the change spec was first drafted, ISO `YYYY-MM-DD`. It does not change as the spec moves through its lifecycle.
- **Title** is `short_snake_case` (the one exception to the kebab-case rule, so the date prefix reads cleanly): `2026-05-21-add_tagging_to_entries.md`.
- One change spec per coherent change. If a "change" really is three unrelated changes, write three files.

---

## Status lifecycle

| Status | Meaning |
|---|---|
| `Proposed` | Drafted, awaiting agreement. The default for a new change spec. |
| `Accepted` | Agreed; ready to implement. |
| `Implemented` | The code change has shipped, but the canonical spec has not yet been updated. |
| `Merged` | Content has been folded into the canonical spec; the file has moved to `changes/merged/`. Terminal. |

A change spec that is rejected is deleted, not kept as `Rejected`. The git/jj history records that it existed.

---

## Document structure

A change spec is a single document with this section set. Drop sections that do not apply (e.g. no `Type changes` if no entities change), but keep the order.

```markdown
# Change: <Human-readable title>

**Status:** Proposed · **Date:** YYYY-MM-DD · **Owner:** <Name> · **Target:** <canonical scope, e.g. apps/editor or Repo-wide>

<One-paragraph summary: what changes, and why, in plain language. A reader should know the shape of the change from this paragraph alone.>

---

## Motivation

<Why this change. The gap, requirement, or problem that drives it. Two short paragraphs. This is the one place a change spec argues for itself; the rest describes the delta.>

---

## Affected spec pages

| Canonical page | Nature of change |
|---|---|
| [`docs/editor/specs/01-domain-model.md`](../../editor/specs/01-domain-model.md) | Add `Tag` entity and its relationship to `Entry` |
| [`docs/editor/specs/04-persistence.md`](../../editor/specs/04-persistence.md) | New `tags` object store and index |
| [`canonical-types.schema.json`](../../editor/specs/canonical-types.schema.json) | Add `Tag` `$def`; add `tagIds` to `Entry` |

Link each affected page with a relative path that resolves from `docs/specs/changes/`. If the change adds a brand-new page to the canonical set, say so here ("Adds `docs/editor/specs/06-tagging.md`").

---

## Proposed changes

One subsection per affected page. Reference the exact canonical section being changed, then give the delta written **in canonical voice** — the prose as it should read once merged. Mark each block as Add / Modify / Remove.

### `docs/editor/specs/01-domain-model.md` → Entities (Add)

> A `Tag` (`tag_`) is a user-defined label applied to entries. It carries:
> - `id` — `tag_<uuid7>`
> - `name` — non-empty string, unique per workspace
> - `createdAt` — timestamp

### `docs/editor/specs/01-domain-model.md` → Relationships (Modify)

> `Entry *—* Tag`: an entry references many tags by id; a tag applies to many entries.

(Repeat per affected section. Quoting the merged-form prose makes the merge step mechanical: the merge is a copy of these blocks into the canonical pages.)

---

## Type changes

Inline JSON Schema fragment holding only the new or changed `$defs`. On merge, these fold into the relevant canonical `canonical-types.schema.json`. Use the same Draft 2020-12 conventions and `$ref` the global shared types.

```json
{
  "$comment": "Fragment for 2026-05-21-add_tagging_to_entries. Folds into apps/editor canonical-types.schema.json on merge.",
  "$defs": {
    "Tag": {
      "type": "object",
      "required": ["id", "name", "createdAt"],
      "additionalProperties": false,
      "properties": {
        "id": { "$ref": "https://interrupt.dev/schemas/canonical-types.schema.json#/$defs/Id" },
        "name": { "$ref": "https://interrupt.dev/schemas/canonical-types.schema.json#/$defs/NonEmptyString" },
        "createdAt": { "$ref": "https://interrupt.dev/schemas/canonical-types.schema.json#/$defs/Timestamp" }
      }
    }
  }
}
```

For a **modified** entity, show the entity with its new shape and note which fields are added or changed in a comment or in the `Proposed changes` block above.

---

## Implementation notes

What an implementing agent needs that is not already in the canonical spec or the blocks above: code entry points to touch (as `file:line`), the order to make changes in, migrations, and any references (RFCs, tickets, upstream docs). Pointers, not a tutorial.

```
1. Add the `tags` store in src/db/schema.ts (bump version, onupgradeneeded).
2. Add Tag type + parser in src/domain/tag.ts (mirror src/domain/entry.ts:12).
3. Wire the tag picker into the editor toolbar at src/ui/Toolbar.svelte:40.
```

---

## Merge plan

The mechanical steps to fold this change spec into the canonical spec once the code ships. Spelling these out up front makes the merge a checklist, not a judgement call.

1. Apply each `Proposed changes` block to its canonical page; bump that page's `**Date:**` to the merge date.
2. Fold the `Type changes` `$defs` into the canonical `canonical-types.schema.json`.
3. If a new canonical page was named in `Affected spec pages`, create it and index it in `docs/README.md`.
4. Flip this file's `**Status:**` to `Merged`, add a `**Merged:** YYYY-MM-DD` field to its header, and move it to `docs/specs/changes/merged/`.
5. Update `docs/README.md`: remove the file from the pending list, leave the merged area pointing at `changes/merged/`.

---

## Assumptions and open questions

(Standard closing block — `**Assumptions**`, `**Decisions**`, `**Open questions**`. Decisions here record choices about the change itself; Open questions are what still blocks acceptance or implementation.)
```

---

## Writing the change spec

1. **Read the canonical spec first.** You cannot describe a delta without knowing the base. Read every canonical page the change touches, end to end, and read the canonical schema.
2. **Write `Proposed changes` in canonical voice.** Each block is the prose that will live in the canonical page after merge. If you would not write it in the canonical spec, do not write it here.
3. **Keep the body honest about uncertainty.** If part of the design is undecided, it goes in Open questions, not as a hedged sentence in the body. The body states the proposed design; the closing block holds what is not yet settled.
4. **Reference, do not restate.** The change spec points at canonical sections by path and heading; it does not reproduce the surrounding canonical content. A reader is expected to open the canonical page alongside it.

---

## Merging a change spec

When the user says the change has shipped ("we implemented the tagging change, merge the spec"):

1. Read the change spec and confirm its `Status` is `Implemented` (or move it there).
2. Walk the `Merge plan` step by step. The `Proposed changes` blocks are the source of truth for the canonical edits.
3. Verify after merge: every block landed on its canonical page, the schema folds in cleanly, internal links still resolve, and `docs/README.md` is updated.
4. Move the file to `docs/specs/changes/merged/`, flip `Status` to `Merged`, stamp `**Merged:**`.

The canonical spec now describes the new reality; the change spec is preserved as dated history of how it got there.

---

## Cross-linking

- `docs/README.md` gains a **Change specs** section: a list of pending change specs under `docs/specs/changes/`, and a pointer to `docs/specs/changes/merged/` for history. A pending change spec the index does not reference is invisible.
- Every link inside the change spec to a canonical page must resolve from `docs/specs/changes/` (so `../../editor/specs/…` for a per-package page, `../foo.md` for a global page).
