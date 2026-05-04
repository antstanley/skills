---
name: spec-creator
description: Use this skill when the user wants to create or expand formal design specifications for an app, package, or codebase. Triggers on phrases like "create a spec", "spec out this app", "write design docs", "formalize the architecture", "document the design", "spec for <component>", "promote this to a global spec", "make repo-wide spec", or when the user references using another project's specs as a template ("use ../foo/specs as a template"). Also triggers when the user asks to add a per-app spec under an existing global spec layer, or to extract repeated content into a global cross-cutting spec. The output is a numbered directory of markdown files plus a JSON Schema sidecar, layered as repo-wide globals + per-app specs.
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

Do not declare the spec complete until all five steps are done. The checklist at [`references/checklist.md`](references/checklist.md) has the full pre-handoff verification.

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

Different spec types have different section sets. The skeletons below are starting points — adapt to what the code actually warrants.

### `00-overview.md`

The entry point. A reader should be able to read only this file and know what the spec covers, what the system does, and where to go next.

```
# <Project> — <Surface> Design Overview
header

The <surface> is <what it is>. <One sentence on the system shape.>

This document is the entry point. Detail pages are linked from each section.

---

## Problem

<Two short paragraphs on what the system solves and why existing options don't.>

---

## Goals

<Numbered list of what the code achieves, today.>

## Non-goals

<Bullet list of what the code deliberately does NOT do.>

---

## System shape

<ASCII diagram of the moving parts, drawn so a reader can follow the data flow.>

<One paragraph naming each box.>

---

## Detail pages

| Page | Topic |
|---|---|
| [01-domain-model.md](01-domain-model.md) | … |
| … | … |

---

## Scope summary

| Area | Implementation | Notes |
|---|---|---|
| <Area> | <What's in the code> | <Constraints> |

(Replace the old "MVP cut" matrix. The scope summary describes implemented surface, not future plans.)

---

closing block
```

**No "MVP" anywhere.** Goals describe what the code achieves now, Non-goals describe what's intentionally absent.

### `01-domain-model.md`

Defines entities, IDs, relationships, lifecycles.

```
# 01 — Domain Model

intro paragraph

## ID scheme

<rule for IDs; table of prefixes>

## Entities

### <Entity> (`<prefix>_`)
<one-paragraph description>
<bullet list of fields>

(repeat per entity)

## Relationships

<ASCII diagram of cardinalities>

## Lifecycle / state machines

<ASCII diagram per stateful entity>

## Required query patterns

<table: query name → access pattern>

closing block
```

### Per-component pages (`02-…`, `03-…`)

Pattern: **Responsibilities · Contract · Flow · Layout · closing block.**

```
# NN — <Component>

intro paragraph

## Responsibilities

<numbered list>

## Contract / API / Routes

<table: method/path → purpose>

## Flow / Lifecycle

<ASCII diagram>

## Implementation layout

<file tree or pointer to where it lives>

closing block
```

### `architecture-principles.md` (global)

Defines how the code is organised. Hexagonal layering, monorepo layout, dependency graph, language conventions, frontend stack baseline. Long file (200–400 lines is normal). Closes with the standard block.

### `development-guidelines.md` (global)

Toolchain, code style, defensive coding, version control conventions, testing pyramid, repo hygiene, definition of done, AI-agent rules. Long file. Closes with the standard block.

### Per-app spec that shadows a global spec

When a per-app `06-architecture-principles.md` builds on a global `docs/specs/architecture-principles.md`, open with a **Read first** pointer:

```markdown
# 06 — Architecture (editor-specific)

> **Read first:** [`docs/specs/architecture-principles.md`](../../specs/architecture-principles.md). That document defines the cross-cutting rules. This page only covers the <app>-specific shape under those rules.

This page records how the <app> applies the global principles: …
```

Then describe only the per-app deltas. Don't restate the global rules.

### `canonical-types.schema.json` (sidecar)

JSON Schema Draft 2020-12. `$defs` for each entity. Per-app schemas `$ref` the global schema for shared types.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.dev/schemas/<scope>-canonical-types.schema.json",
  "title": "<scope> canonical types",
  "description": "Authoritative shapes for <scope>'s domain entities.",
  "$defs": {
    "<Entity>": { … }
  }
}
```

The global schema (`docs/specs/canonical-types.schema.json`) holds only **truly shared** types: `Id`, `Timestamp`, `Url`, `Email`, `Bytes`, `Milliseconds`, `ErrorEnvelope`, `NonEmptyString`. A type belongs in the global schema only when at least two apps reference it.

## Layered structure

Two layers, with strict rules:

- **Global** (`docs/specs/`) — repo-wide, cross-cutting. Architecture principles, development guidelines, shared types schema.
- **Per-app** (`docs/<app>/specs/`) — app-specific. Numbered detail pages, app schema.

Rules:

1. **Per-app specs may reference global specs**; global specs do not reference per-app specs.
2. **No duplicated content.** If two per-app specs say the same thing about a cross-cutting concern, promote to global and have both reference it.
3. **Per-app specs that shadow a global topic open with a "Read first" pointer.** They state only the per-app deltas.
4. **App-specific limits live in per-app specs**, even though the *meta-rule* for declaring limits lives in the global development guidelines. Concrete values are app concerns; rules about declaring values are repo concerns.

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
- **Don't speculate about future work** in the body. Future work belongs in Open questions, or in a separate plan document handled by another skill.
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
