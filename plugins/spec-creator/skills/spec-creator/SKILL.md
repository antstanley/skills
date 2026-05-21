---
name: spec-creator
description: Create, expand, or change formal design specifications for an app, package, or codebase. Triggers on "create/write a spec", "spec out this app", "document the design", "formalize the architecture", "promote to a global spec", "layer a per-app spec on a global one", using another project's specs as a template ("use ../foo/specs as a template"), or proposing/merging a change spec ("change spec", "RFC for X", "draft a change spec", "merge the change spec"). Output is a numbered, layered directory of markdown plus a JSON Schema sidecar (repo-wide globals + per-app specs); a change spec is a single document under docs/specs/changes/.
---

# Spec Creator

A skill for writing canonical design specifications: numbered, layered, cross-linked markdown that defines what exists in the current branch.

## Core principle

**A spec is the canonical definition of what exists in the current branch.** Not a plan, not a wishlist, not an MVP cut. Body sections describe code that is checked in. Aspirational content — "to be tuned later", "deferred", "next iteration" — lives **only** in the closing `Assumptions / Decisions / Open questions` block of each page.

If something the spec describes does not exist in the code, that's a **divergence**. Flag it; do not paper over it with "deferred at MVP". Plans to resolve divergence are a separate workflow handled by other skills.

This rule shapes every section. A `Routes` section lists routes that exist. A `Plugins mounted` section lists plugins that the app actually mounts. A `Database shape` section describes the schema of the IndexedDB store as it is, not as it will be.

## When to apply this skill

- User asks to create a new spec ("spec out X", "write design docs for Y").
- User asks to extend an existing spec set with a new app or component.
- User asks to **promote** content from a per-app spec to a repo-wide global spec ("make this cross-cutting", "this should apply to every app").
- User asks to **layer** a per-app spec on top of an existing global spec ("add an editor-specific arch spec that builds on the global one").
- User points at another project's specs as a template ("use ../kleya/specs as a template", "follow the same shape as the editor specs").

Skip if the request is for a `README`, a runbook, a tutorial, an API reference, or any prose-first doc. Specs are about structural design — entities, lifecycles, contracts, conventions — not how-to walkthroughs.

## Workflow

The skill is a four-phase process. The phases are sequential; don't skip the investigation. The bulk of the value of a good spec comes from the *understanding* the writer has of the code before they write a word.

### Phase 1 — Investigate

Before writing anything, build the understanding:

1. **Read any template the user pointed at.** If the user said "use ../foo/specs as a template", read every file in that directory top to bottom. Capture the file naming, header format, section conventions, and any sidecar files (JSON schemas, asset bundles).
2. **Read existing notes.** Look in `docs/<app>/`, `docs/`, `README.md` files, `CHANGELOG.md`. Don't reinvent what's already documented; extend or formalize.
3. **Read the actual code.** Walk the package(s) the spec covers. Read entry points, key modules, route handlers, store/state files, configuration. Note what exists, what doesn't, and what's load-bearing.
4. **Read existing specs in the same repo.** If `docs/specs/` or `docs/<other-app>/specs/` already exists, read them. Match the shape and the cross-link style.
5. **Identify the layering.** Decide which content belongs at the **global** layer (`docs/specs/`) versus the **per-app** layer (`docs/<app>/specs/`). See [§Layered structure](#layered-structure) below.

The investigation phase often reveals divergence (the code doesn't match a previous doc, or two apps disagree on the same convention). Flag these to the user before writing — the spec should describe one consistent reality.

### Phase 2 — Plan the structure

Sketch the file set before writing. Specs use **flexible numbered files** — the numbering is a reading order, not a schema. Pick a set that matches the project's surface area.

A typical small app:

```
00-overview.md
01-domain-model.md
02-app-shell.md
03-runtime.md            (e.g. editor runtime, query engine)
04-persistence-and-export.md
05-design-system.md      (link to global)
06-architecture.md       (link to global)
07-development.md        (link to global)
canonical-types.schema.json
```

A more complex app might split further: `02-routes.md`, `03-api-contract.md`, `04-storage.md`, `05-jobs.md`, `06-auth.md`, `07-design-system.md`, `08-architecture.md`, `09-development.md`. Numbering is local to the directory; the global layer has its own (or no) numbering.

Always include:
- An **overview** (`00-overview.md`).
- A **domain model** for any spec describing more than one entity.
- A **canonical-types schema** sidecar (`canonical-types.schema.json`) for any spec that has typed entities, even small ones.

Always include if applicable:
- An **architecture / package layout** page.
- A **development guidelines** page.

For the global layer (`docs/specs/`), the typical set is:
- `architecture-principles.md`
- `development-guidelines.md`
- `canonical-types.schema.json` (shared types only — `Id`, `Timestamp`, `Url`, common envelopes)

### Phase 3 — Write

For each file, follow the conventions in [§File conventions](#file-conventions) and [§Section conventions](#section-conventions) below.

Write one file at a time. Cross-link as you go. Keep an internal map of "claims that need a Decision entry at the bottom" — every non-obvious choice ends up in the closing block.

When the file set includes a `development-guidelines.md` page, delegate it to the companion **`development-guidelines` skill** instead of writing it by hand. It resolves the repo's languages and coding style and assembles the page from per-language templates, then hands back here for Phase 4.

If the spec layers on a global spec (e.g., per-app architecture builds on `docs/specs/architecture-principles.md`), open with a one-paragraph **Read first** pointer rather than restating the global rules. See [§Layered structure](#layered-structure).

### Phase 4 — Cross-link

This phase is mandatory and easy to skip — every iteration of this skill has missed at least one of the steps below when not made explicit. Treat each as a checkbox before declaring the spec done.

1. **Update `docs/README.md`** (creating it if absent) to index every spec file and directory you created or moved. This includes:
   - Any new **global** spec file (e.g., a new `docs/specs/foo.md`) — add it to the global-specs list.
   - Any new **per-app** spec set (e.g., `docs/<app>/specs/`) — add the app to the per-app section.
   - This is non-optional. A new spec that the index doesn't reference is invisible to anyone scanning the doc tree. If you wrote a new file at `docs/specs/<name>.md` or under `docs/<app>/specs/`, the very next edit is `docs/README.md`.
2. **Update `docs/<app>/README.md`** for per-app specs — open with a pointer to the global specs at `docs/specs/`, then list the per-app spec set.
3. **Verify every internal link** (`(other-spec.md)`, `[…](../specs/foo.md)`) resolves to a real file.
4. **Verify every `canonical-types.schema.json` entity** referenced in prose actually exists in the schema (and vice versa — every schema entity is described somewhere in prose).
5. **Re-read the closing block** on every page. If you find yourself in step 5 and any page is missing an `Assumptions and open questions` section, add it before declaring done. The closing block is mandatory; even `(None at this stage.)` under a heading counts.
6. **Offer change specs for deferred items.** Collect the deferred work the spec surfaced — Open questions and any Decision that names a planned-but-absent change. If there are any, ask the user whether they want a change spec drafted for them (one per coherent change), so the deferred work has a home outside the canonical body. If yes, draft each per [§Change specs](#change-specs) and [`references/change-specs.md`](references/change-specs.md). If no, leave them in the Open questions blocks. Do not create change specs without asking.

Do not declare the spec complete until all six steps are done. The checklist at [`references/checklist.md`](references/checklist.md) has the full pre-handoff verification.

## File conventions

### Naming

- Per-app specs: numbered `NN-name.md`, two-digit prefix, kebab-case suffix. Number is reading order; pad with leading zero.
- Global specs: kebab-case names, no numbering — they're standalone reference docs (`architecture-principles.md`, not `01-architecture-principles.md`).
- JSON Schema sidecar: `canonical-types.schema.json` (Draft 2020-12).

### Frontmatter / header

Every spec file (markdown only — not the JSON Schema) opens with:

```markdown
# <Title>

**Status:** Draft · **Date:** YYYY-MM-DD · **Owner:** <Name>
```

The status is `Draft`, `Implemented`, or `Deprecated`. The date is the spec's last meaningful revision (today's date for new specs). The owner is the human accountable for the spec's correctness.

For specs with explicit scope, add `· **Scope:** Repo-wide` (global) or `· **Scope:** apps/editor` (per-app). Scope is optional; include it on global specs and on per-app specs that share a name with a global one.

### Closing block

Every spec file closes with `## Assumptions and open questions`, divided into three subheadings:

```markdown
## Assumptions and open questions

**Assumptions**

- A bullet list of facts about the world that the spec relies on but does not control. ("IndexedDB is available", "the user is on a desktop browser".)

**Decisions**

- *Item.* **Choice.** One- to two-sentence rationale, ideally pointing at the code or commit.

**Open questions**

- *Item.* The question. What's blocking resolution. (Or: `(None at this stage.)`)
```

This block is the **only** place aspirational, "to be tuned", or hypothetical content belongs. The body of every spec page describes what is.

### Length

Aim for spec files between 100 and 300 lines of markdown. Above 300 lines, consider splitting (a spec that mixes routes + storage + design probably wants three files). Below 50 lines, consider merging (a sub-section, not its own page).

The `architecture-principles` and `development-guidelines` pages are the common exceptions — they tend to be longer because they hold many cross-cutting decisions.

## Section conventions

Each page type has a characteristic section set. **Full skeletons live in [`references/section-templates.md`](references/section-templates.md)** — read it when you need a starting point for a specific page; don't reproduce them from memory. The essentials and the rules that aren't in the templates:

- **`00-overview.md`** — the entry point; a reader should grasp the whole system from this page alone. Sections: Problem · Goals · Non-goals · System shape (ASCII) · Detail-pages table · Scope summary · closing block. **No "MVP" framing anywhere** — Goals describe what the code achieves now, Non-goals what it deliberately omits. The Scope-summary table replaces any older "MVP cut" matrix.
- **`01-domain-model.md`** — entities, IDs, relationships, lifecycles. Sections: ID scheme · Entities (one block each) · Relationships (ASCII) · Lifecycle/state machines (ASCII) · Required query patterns · closing block.
- **Per-component pages (`02-…`, `03-…`)** — pattern: **Responsibilities · Contract/API/Routes · Flow/Lifecycle · Implementation layout · closing block.**
- **`architecture-principles.md`** (global) — how the code is organised: layering, monorepo layout, dependency graph, language conventions, stack baseline. Long file (200–400 lines is normal).
- **`development-guidelines.md`** (global) — toolchain, code style, defensive coding, version control, testing pyramid, repo hygiene, definition of done, AI-agent rules. Long file. **Produced by the companion `development-guidelines` skill** — it detects the repo's languages, applies a coding style (Tiger Style), and assembles this page from per-language templates. Invoke it rather than writing this page from scratch; it returns to this skill's Phase 4 for the final cross-link pass.
- **Per-app spec that shadows a global one** — open with a **Read first** pointer to the global page, then describe only the per-app deltas. Don't restate the global rules.
- **`canonical-types.schema.json`** (sidecar) — JSON Schema Draft 2020-12, one `$def` per entity; per-app schemas `$ref` the global schema for shared types. The global schema holds only **truly shared** types (`Id`, `Timestamp`, `Url`, `Email`, `Bytes`, `Milliseconds`, `ErrorEnvelope`, `NonEmptyString`); a type goes global only when at least two apps reference it.

## Layered structure

Two layers, with strict rules:

- **Global** (`docs/specs/`) — repo-wide, cross-cutting. Architecture principles, development guidelines, shared types schema.
- **Per-app** (`docs/<app>/specs/`) — app-specific. Numbered detail pages, app schema.

Rules:

1. **Per-app specs may reference global specs**; global specs do not reference per-app specs.
2. **No duplicated content.** If two per-app specs say the same thing about a cross-cutting concern, promote to global and have both reference it.
3. **Per-app specs that shadow a global topic open with a "Read first" pointer.** They state only the per-app deltas.
4. **App-specific limits live in per-app specs**, even though the *meta-rule* for declaring limits lives in the global development guidelines. Concrete values are app concerns; rules about declaring values are repo concerns.

## Change specs

A **canonical spec** describes what exists in the current branch. A **change spec** proposes a delta to it. The two are different document types with inverted rules, and this skill writes both.

- **Canonical spec** — numbered, layered directory of pages. Body describes what is. Lives in `docs/specs/` and `docs/<app>/specs/`.
- **Change spec** — a single document proposing changes that do **not** yet exist. Body describes what will change, in future/imperative voice. Lives in `docs/specs/changes/`, named `YYYY-MM-DD-short_snake_case_title.md`.

A change spec references the canonical pages it touches by path and heading, restates each affected section as the prose it should become once merged, carries an inline JSON Schema fragment for any new or changed entities, and lists the implementation pointers an agent needs. The goal is that an agent can take the change spec plus its references and implement the change.

When the change ships in code, the change spec is **merged** into the canonical spec: each proposed block is applied to its canonical page, the schema fragment folds into the canonical schema, and the change spec moves to `docs/specs/changes/merged/` with its `Status` flipped to `Merged`. It is preserved as dated history, not deleted.

This is the one place the "describes-what-exists" rule is suspended — and only inside a change spec's body, never in a canonical page. Do not edit canonical pages to describe a change until that change has shipped; that is what the change spec is for.

The change-spec lifecycle is `Proposed` → `Accepted` → `Implemented` → `Merged`. Full template, document structure, and merge procedure are in [`references/change-specs.md`](references/change-specs.md). Read it before writing or merging a change spec.

## Voice and tone

- Present tense for what exists (`the editor exposes /api/opengraph`).
- Past tense in Decisions (`we chose IndexedDB because …`).
- Question form in Open questions (`what is the migration strategy when …`).
- No marketing voice. No "easily", "simply", "just", "powerful", "robust". Specs describe; they don't advertise.
- No emoji. Specs are formal documents.
- No exclamation points.
- Short declarative sentences. Explanatory clauses earn their place.

## Decisions pattern

Every non-obvious choice is recorded in the closing block as a `Decision`:

```markdown
- *Document size cap.* **5 MiB serialised JSON.** Rough envelope: a long-form essay with embedded images encoded as data URLs would bump against this; plain prose is well below.
```

Format:
- Italic short label naming the decision.
- Bold the choice.
- Sentence(s) explaining the *why*. Concrete reasoning, not "team consensus".

A spec without a Decisions list is a spec that hasn't done enough thinking. If you're writing the body and find yourself wanting to insert "we picked X because…" inline, lift it into the Decisions list and reference forward (`see Decisions §<name>`).

## What NOT to do

- **Don't use MVP framing.** No "Goals (MVP)", "Non-goals (MVP)", "MVP cut summary", "at MVP", "deferred". The spec describes what the code does now.
- **Don't speculate about future work** in a canonical spec's body. Future work belongs in Open questions, or in a **change spec** (see [§Change specs](#change-specs)) — a separate single document under `docs/specs/changes/` whose whole job is to propose a delta.
- **Don't restate global content in per-app specs.** Use a "Read first" pointer.
- **Don't add fields to schemas that aren't in the code.** A schema field with `description: "Reserved for next iteration"` is a lie. If the field doesn't exist, leave it out and put the gap in Open questions.
- **Don't write tutorials inside specs.** Specs define structure; tutorials and runbooks are separate doc types.
- **Don't wrap the spec in code comments or quote blocks.** Markdown headings are the structural API; respect them.
- **Don't number global specs.** They're standalone references, not a numbered series.
- **Don't omit the closing Assumptions / Decisions / Open questions block.** Even `(None at this stage.)` is a valid Open Questions entry.

## Examples

### Promotion (per-app → global)

User: "The architecture page in `docs/editor/specs/06-architecture-principles.md` is mostly cross-cutting. Make it global."

1. Read the per-app file.
2. Identify cross-cutting paragraphs (hexagonal layering, monorepo layout, dependency graph, TS config, frontend stack).
3. Identify per-app paragraphs (the editor's specific package boundaries, ports, file layout).
4. Create `docs/specs/architecture-principles.md` with the cross-cutting content, scoped `Repo-wide`.
5. Rewrite `docs/editor/specs/06-architecture-principles.md` to a thin per-app version that opens with the **Read first** pointer and only covers the editor-specific deltas.
6. Update `docs/README.md` (creating it if needed) to index the new global spec.

### Adding a sibling app

User: "Add a spec for the website app at `apps/website` modelled on the editor specs."

1. Read `docs/editor/specs/` end-to-end as the template.
2. Read `apps/website/` source: routes, layouts, build config.
3. Pick a numbered file set appropriate to the website's surface area (smaller than the editor's — 00-overview, 01-content-model, 02-routes-and-layouts, 03-build-pipeline, plus per-app architecture and development pointer pages).
4. Write each file describing what exists.
5. Cross-link the global specs.
6. Update `docs/README.md` to add the website specs.

## Reference files

- [`references/section-templates.md`](references/section-templates.md) — Detailed section skeletons for overview, domain-model, architecture, dev-guidelines, canonical-types schema. Read when you need a starting point for a specific page type.
- [`references/voice-and-decisions.md`](references/voice-and-decisions.md) — Worked examples of the Decisions pattern and the voice rules. Read when phrasing feels awkward.
- [`references/checklist.md`](references/checklist.md) — Pre-handoff checklist (no MVP language, all cross-refs resolve, closing block on every page, schema sidecar matches body claims). Read after writing, before declaring done.
- [`references/change-specs.md`](references/change-specs.md) — Change-spec document type: how a proposed-change document differs from a canonical spec, its single-document structure, the `Proposed → Accepted → Implemented → Merged` lifecycle, and the merge procedure. Read when the user wants to propose a change to an existing spec or merge a shipped change back in.
