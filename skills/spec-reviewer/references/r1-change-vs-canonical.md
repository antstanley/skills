# Review Template R1: Change Spec vs Canonical Spec

This template tells you exactly what to do at each step. Follow it literally. Do not skip steps. Do not summarize — write out each step's result before moving to the next. It is a semi-formal certificate procedure: state premises, resolve every reference through a fixed sequence, trace concrete claims, then deliver a verdict by rubric.

Use when reviewing a single change-spec document (under `.specs/changes/`) against the canonical pages it targets. The change spec is the artifact under review. You are verifying that its proposed delta references real canonical anchors and contradicts nothing that stays in force.

## Procedure

**Step 1: State premises.**
Write exactly three lines:

```
P1: The change spec targets [list every canonical page + heading named in its Affected spec pages table].
P2: The intended delta is [one sentence: what the change spec proposes to change].
P3: Must not contradict [one sentence: the canonical claims that remain in force after the change].
```

**Step 2: Reference resolution.**
For EACH entry in the `Affected spec pages` table AND each `Proposed changes` block, resolve its target through this exact sequence. Write out each sub-step:

1. Does the named canonical file exist at the given relative path (resolved from `.specs/changes/`)? If no → UNRESOLVED (broken target). STOP.
2. Does the named section / heading exist on that page? If no → UNRESOLVED (heading not found). STOP.
3. For a **Modify** or **Remove** block: does the canonical section currently contain the text the block claims to change or delete? If no → STALE REFERENCE (the canonical page has moved on since the change spec was drafted). STOP.
4. For an **Add** block: does the canonical section already contain an equivalent claim? If yes → DUPLICATE (the change adds what already exists). STOP.
5. Otherwise → RESOLVED.

Then check coverage in both directions. Write one line per mismatch:

- An `Affected spec pages` entry with no matching `Proposed changes` block → "COVERAGE GAP: [page] listed but no block addresses it."
- A `Proposed changes` block touching a page absent from the `Affected spec pages` table → "UNLISTED TARGET: [block] changes a page not in the Affected table."

**Step 3: Consistency trace.**
For each RESOLVED block, compare the proposed prose against the current canonical prose. Write:

```
[page → heading] ([Add | Modify | Remove]):
  Canonical now: [one line — what the page currently says here]
  Change proposes: [one line — the merged-form prose the block carries]
  → [CONSISTENT | CONTRADICTS: <which canonical claim, and how it conflicts>]
```

Then check the change spec against itself. Write:

```
INTERNAL: [do any two Proposed-changes blocks disagree? does a block describe an entity differently from the Type changes fragment? → list each, or "consistent"]
```

**Step 4: Schema check.**
For the `Type changes` `$defs` fragment (skip if the change touches no entities):

```
- $ref resolution: every $ref points to a global shared type or a $def in this fragment → [all RESOLVED | UNRESOLVED: <which>].
- Modified entity base: the fragment's base shape matches the canonical entity's current shape, so the diff is real and not a silent full rewrite → [MATCHES | DRIFT: <field>].
- Prose/schema parity: every entity named in Proposed-changes prose has a $def, and every $def is referenced in prose → [MATCHED | ORPHAN: <which>].
```

**Step 5: Open issues / edge cases.**
List 1–3 things the change spec leaves ambiguous or unhandled (an entity it references but never schematizes; a relationship it changes on one page but not its mirror page; a `Merge plan` step that targets a section not in `Proposed changes`). If none exist, write: "No unhandled gaps identified."

**Step 6: Verdict.**
Use this decision rubric:

- INCONSISTENT: Step 2 found UNRESOLVED or STALE REFERENCE, OR Step 3 found CONTRADICTS (against canonical or internal), OR Step 4 found an UNRESOLVED `$ref` or DRIFT.
- CONCERNS: Step 2 found DUPLICATE / COVERAGE GAP / UNLISTED TARGET, OR Step 4 found ORPHAN, OR Step 5 found gaps that could break the merge.
- LIKELY_CONSISTENT: all steps passed but you could not read every referenced canonical page (incomplete context).
- CONSISTENT: all steps passed and the full canonical context was available.

Write exactly:

```
VERDICT: [CONSISTENT | LIKELY_CONSISTENT | CONCERNS | INCONSISTENT]
CONFIDENCE: [high | medium | low]
SUMMARY: [one sentence explaining the verdict]
SUGGESTIONS:
- [one actionable fix per issue — the edit that resolves it]
```

## Worked Example

**Input:** A change spec `.specs/changes/2026-05-21-add_tagging_to_entries.md` proposing to add a `Tag` entity. Its `Affected spec pages` table lists `.specs/editor/specs/01-domain-model.md` (Entities, Relationships) and `.specs/editor/specs/04-persistence.md` (object stores). The canonical `01-domain-model.md` has an `## Entities` heading and a `## Relationships` heading. The canonical `04-persistence.md` was recently renamed to `04-persistence-and-export.md` and the change spec still points at the old name.

**Correct output:**

```
P1: The change spec targets .specs/editor/specs/01-domain-model.md (Entities, Relationships) and .specs/editor/specs/04-persistence.md (object stores).
P2: The intended delta is to add a Tag entity, an Entry*—*Tag relationship, and a tags object store.
P3: Must not contradict the existing Entry entity definition or the current object-store list.

REFERENCE RESOLUTION:
- 01-domain-model.md → Entities (Add):
  1. File exists at .specs/editor/specs/01-domain-model.md? YES.
  2. Heading "## Entities" exists? YES.
  3. Add block — does Entities already define Tag? NO.
  4. → RESOLVED.
- 01-domain-model.md → Relationships (Modify):
  1. File exists? YES. 2. "## Relationships" exists? YES.
  3. Modify block claims to change the Entry relationships line — does that line exist? YES.
  → RESOLVED.
- 04-persistence.md → object stores (Add):
  1. File exists at .specs/editor/specs/04-persistence.md? NO — the canonical page is 04-persistence-and-export.md.
  → UNRESOLVED (broken target).

COVERAGE: every Affected-pages entry has a matching Proposed-changes block; no unlisted targets.

CONSISTENCY TRACE:
- 01-domain-model.md → Entities (Add):
  Canonical now: defines Entry, Workspace. No Tag.
  Change proposes: adds Tag (tag_<uuid7>, name, createdAt).
  → CONSISTENT.
- 01-domain-model.md → Relationships (Modify):
  Canonical now: "Entry *—1* Workspace".
  Change proposes: adds "Entry *—* Tag" alongside it.
  → CONSISTENT.
INTERNAL: the Tag fields in the Entities block (name, createdAt) match the Type changes fragment. consistent.

SCHEMA CHECK:
- $ref resolution: Tag.id $refs Id, Tag.name $refs NonEmptyString, Tag.createdAt $refs Timestamp — all RESOLVED.
- Modified entity base: Entry gains tagIds; fragment shows Entry with its current fields plus tagIds → MATCHES.
- Prose/schema parity: Tag named in prose and present in fragment → MATCHED.

OPEN ISSUES:
- The Merge plan references "the tags object store in 04-persistence" but the Proposed-changes block for persistence cannot land — its target page does not exist under that name.

VERDICT: INCONSISTENT
CONFIDENCE: high
SUMMARY: The delta is internally sound, but the persistence block targets a renamed page (04-persistence.md → 04-persistence-and-export.md), so it cannot merge as written.
SUGGESTIONS:
- Update the Affected spec pages table, the persistence Proposed-changes block heading, and the Merge plan to point at .specs/editor/specs/04-persistence-and-export.md.
- Re-verify the "object stores" heading exists on the renamed page before re-running the review.
```

## Common Mistakes to Avoid

1. **Skipping reference resolution.** Do not assume a `Proposed changes` block points at a heading that exists. Walk the file → heading → current-text sequence every time; renamed pages and edited headings are the most common merge-breakers.
2. **Editing instead of suggesting.** The reviewer surfaces issues and proposes the edit. Authoring the fix to a canonical page or a change spec is spec-creator's job — hand back rather than rewriting unprompted.
3. **Vague verdicts.** Every issue in SUGGESTIONS must name a concrete anchor (a path, a heading, a field) and the edit that resolves it — not "some references look off".
