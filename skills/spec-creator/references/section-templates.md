# Section templates

Detailed skeletons for the common spec page types. Each is a starting point — adapt to the actual code being specified. The header (Status / Date / Owner) and closing block (Assumptions / Decisions / Open questions) are mandatory on every page; the body sections vary.

---

## Overview (`00-overview.md`)

```markdown
# <Project> — <Surface> Design Overview

**Status:** Draft · **Date:** YYYY-MM-DD · **Owner:** <Name>

The **<surface>** (`<path>`) is <one-sentence description>. It is <a tenant of / part of / an entry to> <larger context>.

This document is the entry point for <surface>'s design. It states the problem, the goals, the system shape, and the scope. Detail pages are linked from each section.

---

## Problem

<Two short paragraphs. What does the system solve? Why are existing options unsatisfactory?>

---

## Goals

1. <What the code achieves, today, in concrete user-facing terms.>
2. <Capability 2.>
3. <Capability 3.>

## Non-goals

- <Thing the system deliberately doesn't do.>
- <Thing 2.>
- <Thing 3.>

---

## System shape

```
<ASCII diagram. Box-and-arrow with annotations. Show data flow.>
```

<One paragraph describing each major box in the diagram, in plain language. End with where the spec's detail pages cover each.>

---

## Detail pages

| Page | Topic |
|---|---|
| [01-domain-model.md](01-domain-model.md) | Entities, IDs, lifecycles |
| [02-…](02-….md) | … |
| [canonical-types.schema.json](canonical-types.schema.json) | Domain entity shapes as JSON Schema |

(If shadowing a global spec, add a paragraph explaining the per-package/global layering.)

---

## Scope summary

| Area | Implementation | Notes |
|---|---|---|
| <Area 1> | <What's in the code> | <Constraints / known gaps> |
| <Area 2> | <…> | <…> |

(This table replaces the older "MVP cut" matrix. It describes implementation, not roadmap.)

---

## Assumptions and open questions

**Assumptions**

- …

**Decisions**

- *<short label>.* **<choice>.** <one to two sentences of why>

**Open questions**

- *<short label>.* <question + what's blocking resolution>
```

---

## Domain model (`01-domain-model.md`)

```markdown
# 01 — Domain Model

This page defines the entities <surface> manages, how they relate, how they are identified, and what queries the persistence layer must support. The wire / storage shape of these entities is formalised in [`canonical-types.schema.json`](canonical-types.schema.json).

---

## ID scheme

All persistent entities have a string ID of the form:

```
<prefix>_<uuid>
```

- **prefix** is a short lowercase tag identifying the entity type (2–4 chars).
- **uuid** is a v7 UUID (RFC 9562).

Prefixes are stable. Adding a new entity adds a new prefix; never reuse one.

| Prefix | Entity |
|---|---|
| `<pfx>_` | <Entity name> |

---

## Entities

### <Entity> (`<pfx>_`)

<One-paragraph description of what this entity represents.>

Carries:

- `id` — <description>
- `<field>` — <type, description>
- ...

(Repeat per entity.)

---

## Relationships

```
<ASCII diagram showing 1:1, 1:*, *:* relationships and any self-references>
```

---

## Lifecycle / state machine

```
<ASCII state-machine diagram>
```

<Bullet list explaining each state and what triggers transitions.>

---

## Required query patterns

| Query | Access pattern |
|---|---|
| <Description> | <How it's served — index, scan, etc.> |

---

## Assumptions and open questions

(standard closing block)
```

---

## Per-component spec (`02-…`, `03-…`, etc.)

```markdown
# NN — <Component>

<One-paragraph intro: what this component is, what page documents the higher-level frame.>

---

## Responsibilities

1. <What this component owns.>
2. <…>

The component does **not** own: <list of explicit non-responsibilities. Useful for cross-cutting clarity.>

---

## <Contract / API / Routes / Surface>

<Adapted to component type. Examples:>

### Routes

| Method | Path | Purpose | Source |
|---|---|---|---|
| GET | `/foo` | <…> | `<file>` |

### API

```ts
publicSurface(args): ReturnType
```

<Description of each export.>

### Configuration

| Option | Type | Default | Use |
|---|---|---|---|

---

## <Flow / Lifecycle>

```
<ASCII flow diagram>
```

<Numbered list explaining each step in the flow.>

---

## <Implementation layout>

```
<file tree showing where the component's source lives>
```

<Pointer to where each piece is implemented.>

---

## Assumptions and open questions

(standard closing block)
```

---

## Architecture principles (global)

```markdown
# Architecture Principles

**Status:** Draft · **Date:** YYYY-MM-DD · **Owner:** <Name> · **Scope:** Repo-wide

This page defines **how** the <repo> code is organised. It is the canonical reference for "the runtime", "the experience", "ports", and "adapters" everywhere in the repo.

---

## <Architectural pattern>

<E.g., hexagonal layering rules. State the principle, then list what goes where.>

### What goes where

| Concern | Layer |
|---|---|
| <…> | <core / adapter / composition root> |

---

## Monorepo layout

```
<file tree showing apps/, packages/, docs/>
```

### Package roles

- **<package>** — <description and rules>

---

## Dependency graph

```
<ASCII showing allowed dependency directions>
```

Rules:
- <…>

---

## TypeScript / language configuration

<Standard settings, project references, strictness>

---

## Cross-cutting conventions

### Errors / Async / IDs / Time / Logging

<Each as its own subsection with rules>

---

## Frontend / backend stack

<List of sanctioned tools and versions>

---

## Per-package specs

<Pointer to where per-package specs layer on top of this document>

---

## Assumptions and open questions

(standard closing block)
```

---

## Development guidelines (global)

The `development-guidelines.md` page is **not templated here.** It is authored by the companion
`development-guidelines` skill (see [`../../development-guidelines/SKILL.md`](../../development-guidelines/SKILL.md)),
which detects the repo's languages and coding style and assembles the page from per-language
templates. spec-creator's Phase 3 invokes that skill rather than hand-writing the page — so the
page skeleton lives there, with the templates, not duplicated here where it would drift.

---

## Canonical-types schema (`canonical-types.schema.json`)

JSON Schema Draft 2020-12. Two-layer pattern: global schema for shared types, per-package schemas that `$ref` it.

### Global schema skeleton

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://<project>.dev/schemas/canonical-types.schema.json",
  "title": "<repo> shared canonical types",
  "description": "Repo-wide shared shapes referenced by every per-package schema.",
  "$defs": {
    "Id": {
      "description": "Generic entity id of the form <prefix>_<uuid7>.",
      "type": "string",
      "pattern": "^[a-z]{2,4}_[0-9a-f-]{36}$"
    },
    "Timestamp": {
      "description": "RFC3339 timestamp in UTC.",
      "type": "string",
      "format": "date-time"
    },
    "NonEmptyString": {
      "type": "string",
      "minLength": 1,
      "pattern": "\\S"
    },
    "Url": {
      "type": "string",
      "format": "uri",
      "pattern": "^[a-z][a-z0-9+.-]*://"
    },
    "ErrorEnvelope": {
      "type": "object",
      "required": ["code", "message"],
      "additionalProperties": false,
      "properties": {
        "code": { "type": "string", "pattern": "^[a-z][a-z0-9-]*$" },
        "message": { "$ref": "#/$defs/NonEmptyString" },
        "details": { "type": "object", "additionalProperties": true }
      }
    }
  }
}
```

### Per-package schema skeleton

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://<project>.dev/schemas/<package>-canonical-types.schema.json",
  "title": "<package> canonical types",
  "description": "Authoritative shapes for <package>'s domain entities.",
  "$defs": {
    "<Entity>": {
      "type": "object",
      "required": ["id", "..."],
      "additionalProperties": false,
      "properties": {
        "id": { "$ref": "https://<project>.dev/schemas/canonical-types.schema.json#/$defs/Id" },
        "createdAt": { "$ref": "https://<project>.dev/schemas/canonical-types.schema.json#/$defs/Timestamp" }
      }
    }
  }
}
```

A type belongs in the **global** schema only when at least two apps reference it. Promote on demand, not speculatively.
