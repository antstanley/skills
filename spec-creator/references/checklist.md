# Pre-handoff checklist

Run through this list before declaring a spec done. The checklist enforces the **describes-what-exists** rule and the structural conventions; mistakes here are easy to introduce and hard to spot once the doc is shipped.

---

## Branch reality

- [ ] Every body section describes code, configuration, or contracts that exist in the current branch.
- [ ] No body section uses "MVP", "deferred", "for now", "at MVP", "for the moment", or "in the next iteration".
- [ ] Aspirational content lives **only** in the closing `Assumptions / Decisions / Open questions` block.
- [ ] If the spec describes a thing the code doesn't have, the gap is captured as an Open question and flagged to the user.

---

## File structure

- [ ] Per-app spec files are numbered `NN-name.md` (two-digit prefix, kebab-case suffix).
- [ ] Global spec files (in `docs/specs/`) are **not** numbered.
- [ ] An overview (`00-overview.md`) exists for any spec set with two or more files.
- [ ] A `canonical-types.schema.json` sidecar exists if the spec describes typed entities.

## Headers

- [ ] Every markdown spec file opens with `**Status:** … · **Date:** YYYY-MM-DD · **Owner:** …`.
- [ ] Status is `Draft`, `Implemented`, or `Deprecated` — no other values.
- [ ] Date reflects today's date (or the meaningful revision date) in `YYYY-MM-DD`.
- [ ] Global specs and any per-app spec that shares a name with a global one have a `· **Scope:** …` qualifier.

## Closing block

- [ ] Every markdown spec file ends with a `## Assumptions and open questions` section.
- [ ] The section has three subheadings: `**Assumptions**`, `**Decisions**`, `**Open questions**`.
- [ ] No subheading is omitted; if there are no items, write `(None at this stage.)`.
- [ ] Decisions follow the format `*<label>.* **<choice>.** <rationale>.` — italic label, bold choice, prose why.
- [ ] No Decision uses superlatives ("best", "easiest", "most powerful") in place of rationale.

---

## Layered structure

- [ ] If the per-app spec set covers a topic also covered by a global spec, the per-app file opens with a **Read first** pointer and only documents per-app deltas.
- [ ] No per-app spec restates a global rule. Global rules are referenced, not duplicated.
- [ ] No global spec references a per-app file (the dependency runs one way).
- [ ] App-specific limit values live in per-app dev guidelines; the meta-rule lives in the global one.

---

## Schema sidecar

- [ ] `canonical-types.schema.json` uses `$schema: https://json-schema.org/draft/2020-12/schema`.
- [ ] Per-app schemas `$ref` the global schema for shared types (`Id`, `Timestamp`, `Url`, etc.) rather than redefining them.
- [ ] Every entity referenced in the spec body has a definition in the schema.
- [ ] Schema fields match what the code actually persists / sends — no "reserved for next iteration" fields that don't exist.

---

## Cross-links

- [ ] Every internal link `(some-spec.md)` resolves to a real file in the same directory.
- [ ] Every cross-directory link uses a relative path that resolves (`../specs/foo.md` from a per-app spec).
- [ ] **`docs/README.md` lists every new file you wrote.** Walk the diff: for each new path under `docs/`, confirm the index references it. Adding a new file without indexing it is the most common miss; check it twice. If the index didn't exist, you created it.
- [ ] If this spec set is per-app, `docs/<app>/README.md` exists and opens with a pointer at the global specs at `docs/specs/`, then lists the per-app set.
- [ ] If this work **promoted** content from per-app to a new global spec, both:
  - The new `docs/specs/<name>.md` is listed in `docs/README.md`'s global section, AND
  - The per-app file's "Read first" pointer goes to the new global spec.

---

## Voice

- [ ] No emoji.
- [ ] No exclamation points.
- [ ] No "easily", "simply", "just", "powerful", "robust", "scalable", "seamlessly".
- [ ] Body uses present tense for what exists.
- [ ] Decisions use past tense or "we chose" framing.
- [ ] Open questions use question form.

---

## Length and rhythm

- [ ] Each spec file is roughly 100–300 lines (architecture-principles and development-guidelines may exceed this).
- [ ] No paragraph longer than ~4 sentences (split or convert to a list).
- [ ] Tables for any list with parallel structure (routes, fields, tokens).
- [ ] ASCII diagrams for shapes (system, state machines, dependency graphs).

---

## When the checklist finds a problem

For each unchecked item:

1. If it's a **typo or missing pointer** — fix in place, re-check.
2. If it's a **structural gap** (missing closing block, missing schema entity) — fix in place.
3. If it's a **branch-reality violation** ("the spec describes thing X that doesn't exist") — flag to the user and either remove from the body (move to Open questions) or open a separate plan to bring the code in line.
4. If it's a **voice violation** in many places — pass through the file once with the voice rules in mind; rewrite, don't patch.

Run the checklist again after fixes. Fresh eyes catch things mid-fix eyes miss.
