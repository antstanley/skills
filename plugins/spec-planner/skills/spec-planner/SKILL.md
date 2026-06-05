---
name: spec-planner
description: Build an implementation plan from a specification — decompose a spec into a dependency-ordered graph of reviewable task packages, each with a definition of done. Triggers on "plan the implementation", "create an implementation plan", "plan out this spec", "break this spec into tasks", "build a task plan", "sequence the work", "how should we build this", "turn this change spec into a plan", or "what's the build order for X". Consumes a canonical spec set, a change spec, or an external/framework spec; produces a plan folder at .specs/plans/YYYY-MM-DD-snake_case_title/ (a plan.md task graph plus one hybrid task file per package).
---

# Spec Planner

A skill for turning a specification into a buildable plan: a dependency-ordered graph of task packages, each an independently reviewable slice of work with a clear definition of done.

## Core principle

**A plan is a buildable, reviewable decomposition of a spec — not a restatement of it.** The spec says *what* the system should be; the plan says *what to build, in what order, and how each piece is judged done*. Its unit is the **task package**: a coherent slice of work that, when merged, leaves the system in a state a reviewer can evaluate on its own.

Two rules follow from this and shape every plan:

1. **Order for reviewability, not just for dependencies.** A topological sort is necessary but not sufficient. Among the work that *could* come next, pick what unlocks the most reviewable surface area. If a feature is gated behind auth, build auth early so the gated feature can be reviewed end to end. A plan that builds ten back-end packages before anything is demonstrable is a worse plan than one that ships a thin reviewable path first.
2. **Every task package carries a definition of done.** The DoD is drawn from the repo's own development guidelines (its testing bar, its limits discipline, its lint/format gates) plus the task-specific acceptance — the reviewable outcome that proves the package works. A task without a DoD is a wish, not a plan.

The plan is **forward-looking** — it describes work that does not yet exist, in future/imperative voice (the inverse of a canonical spec, the same stance as a change spec). But it inherits spec-creator's discipline for uncertainty: assumptions, decisions, and open questions go in the closing block, never hedged into the body.

## Relationship to spec-creator

This skill is a companion to **spec-creator**: it consumes that skill's specs and follows its voice and closing-block conventions. Read [`spec-creator`'s `SKILL.md`](../../../spec-creator/skills/spec-creator/SKILL.md) if you have not — this skill assumes the canonical-vs-change distinction and the `Assumptions / Decisions / Open questions` block, and does not restate them.

It is not *limited* to spec-creator output: a plan can be built from any specification — a canonical spec set, a change spec, or an external format (PRD, RFC, Gherkin, OpenAPI). The source shapes Phase 1 (how the spec is read); the rest of the workflow is the same.

The boundaries between the companions:

- **spec-creator** writes the spec; **spec-planner** plans how to build it.
- **development-guidelines** writes the rules of the road, including the `Definition of done` section that spec-planner *reads* to derive each task's DoD.
- **spec-reviewer** checks specs against code. spec-planner may invoke it in Phase 1 (R2 / R3) to learn what is already built. It ships in the **spec-creator** plugin and is *optional* — when absent, the Phase 1 code read covers the same ground (a fallback, not a skipped step).
- **done-certificates** authors the verification protocol for a task's DoD; a *separate* validating agent runs it. See [§Adding done certificates](#adding-done-certificates).

## When to apply this skill

- The user has a spec (canonical, change, or external) and asks how to build it — "plan the implementation", "break this into tasks", "what's the build order".
- The user wants a change spec's `Implementation notes` expanded into a sequenced, reviewable task graph.
- The user wants existing planned work re-sequenced for earlier review checkpoints.

Skip when:

- The change is small and self-contained — a single change spec with a three-line `Implementation notes` block is already its own plan; do not wrap it in ceremony. Say so and point at the change spec.
- The request is to *write or change the spec* (that is spec-creator) or to *review* spec-vs-code (that is spec-reviewer).
- The request is for a runbook, a tutorial, or a project schedule with calendar dates. A plan sequences work by dependency and reviewability, not by date.

## Workflow

Five phases, sequential. The value of a plan comes from understanding the spec and the code *before* drawing the graph; do not skip Phase 1.

### Phase 1 — Read the spec and establish the rules of the road

1. **Read the source specification end to end.** For a canonical spec set, read `.specs/README.md` then every page in scope and the schema sidecar. For a change spec, read it and the canonical pages it targets. For an external spec, read the whole document and note its structure.
2. **Establish the definition-of-done baseline.** Find the repo's development guidelines — `.specs/development-guidelines.md` (the page the `development-guidelines` skill produces) is the first choice; its `Definition of done` and `Limits and bounds` sections set the per-task bar. If absent, fall back to repo signals (`CONTRIBUTING.md`, CI config, test setup) and, failing that, **ask the user** what "done" means for a task here. Record the source in the plan's header note.
3. **Learn what already exists.** A plan must not re-plan finished work. Walk the code the spec describes; where the spec set has drifted from the code, delegate to **spec-reviewer** (R2 for a canonical spec, R3 for a change spec) to enumerate what is already implemented. spec-reviewer ships with the **spec-creator** plugin — when it is not installed, do the equivalent code read by hand (it is the same enumeration, not an optional step). Built work becomes a precondition in the plan, not a task.
4. **Surface ambiguity early.** Anything the spec leaves undecided that blocks sequencing (an unspecified auth model when half the features are gated) is flagged to the user now and captured for the Open questions block.

### Phase 2 — Decompose into task packages

Slice the spec into coherent, independently reviewable packages. Each package produces **one reviewable artifact** and carries a definition of done. The decomposition heuristics, the dependency edge types, and the slicing rules live in [`references/task-decomposition.md`](references/task-decomposition.md) — read it before decomposing; do not reconstruct the method from memory.

The essentials:

- **One package = one coherent reviewable slice.** Small enough to review in one sitting, large enough to stand on its own. Prefer thin vertical slices (a path that works end to end) over horizontal layers (all models, then all routes).
- **Give each package a working label** during decomposition; the final two-digit task number `NN` is assigned in Phase 4, following the implementation order from Phase 3.
- **Name the spec sections each package implements.** Every package points back at the spec page(s) and heading(s) it satisfies, so coverage is checkable.

### Phase 3 — Build the graph and order for reviewability

1. **Draw the dependency edges** between packages — build, data, contract, and *review* dependencies (see [`references/task-decomposition.md`](references/task-decomposition.md) for the edge types). The result is a DAG; if you find a cycle, the slice is wrong — re-cut the packages.
2. **Topologically sort, then bias for reviewability.** Among packages whose dependencies are met, schedule first the ones that unlock the most downstream review — foundational enablers (auth, persistence schema, app shell, seed data, CI) that later work is *reviewed through*. This is the auth-before-gated-features rule.
3. **Group into milestones.** Each milestone ends at a reviewable state — a point where a reviewer can exercise something coherent. Name what is demonstrable at each milestone.

### Phase 4 — Write the plan

A plan is a **folder**, not a single file. Create `.specs/plans/YYYY-MM-DD-snake_case_title/` (ISO date prefix — today's date — then a lowercase snake_case short title, e.g. `.specs/plans/2026-05-22-add_auth_flow/`). Inside it:

- **`plan.md`** — the overview: header, summary, the source/DoD baseline, the task graph, the implementation order and milestones, and the closing block. It carries no task bodies — it links to them.
- **One file per task package**, named `NN-snake_case_task.md` — a two-digit number prefix (assigned in **implementation order**, so the files sort the way the work is sequenced) plus a short snake_case description, e.g. `01-passphrase_lock.md`, `02-entry_store.md`. The number is the task's id everywhere else in the plan (the dependency table, the Mermaid graph). Numbers are append-only once the plan is shared — a task added later takes the next free number and records its true position in the order table, rather than renumbering and breaking cross-references.

Follow the two skeletons in [`references/plan-template.md`](references/plan-template.md) — one for `plan.md`, one for a task file. The load-bearing rules the body keeps inline:

- **`plan.md`** holds the header, the source/DoD baseline note, the **Task graph**, the implementation-order/milestones section, and the closing block — but no task bodies. The graph is a Mermaid `graph TD` plus a **dependency table that is the source of truth**: if the two disagree, the table wins.
- **Each task file** (`NN-snake_case_task.md`) is `hybrid` form: header + `**Plan:**`/`**Status:**` line, a structure block (`Implements`, `Depends on`, `Produces`, `Pointers`), a step checklist, and a `Definition of done` checklist whose last item is always a `Reviewable:` line.

Voice: future/imperative for the work, past tense in Decisions, question form in Open questions — the same voice rules as spec-creator. No marketing words, no emoji, no exclamation points.

### Phase 4.5 — Author done certificates (default; prompt when interactive)

Once the task files exist, delegate to **done-certificates** to author one certificate per task. This is **on by default**; the prompt-vs-include behavior and the delegation mechanics are in [§Adding done certificates](#adding-done-certificates) below.

### Phase 5 — Cross-link and verify

Mandatory, and easy to skip:

1. **Update `.specs/README.md`** (creating it if absent) — add a **Plans** section listing the plan folder under `.specs/plans/`, pointed at its `plan.md`. A plan the index does not reference is invisible.
2. **Verify every link resolves.** Spec-page links resolve from the plan folder (so `../../foo.md` for a global page — now at the `.specs/` root — and `../../<package>/specs/NN-name.md` for a per-package page, which keeps its `specs/` segment). Each dependency-table row links to a real task file in the folder, and each task file's `Plan:` link points back at `plan.md`.
3. **Verify the graph is coherent** — the Mermaid edges and the dependency table agree, every task number in the table has a matching `NN-…md` file and vice versa, and the DAG has no cycle.
4. **Verify coverage** — every in-scope spec section maps to at least one task file, and every task file names the spec section it implements. Gaps go in `plan.md`'s Open questions, flagged to the user.
5. **Verify the done certificates** (when included) — every task file has a matching `certificates/NN-…md`, the obligations are one-to-one with the task's `Definition of done`, and the certificate ↔ task links resolve both ways. See the checklist's *Done certificates* section.
6. **Run the checklist** at [`references/checklist.md`](references/checklist.md) before declaring the plan done.

## What NOT to do

- **Don't restate the spec.** The plan references spec sections by path and heading; it does not reproduce them. A reader opens the spec alongside the plan.
- **Don't plan finished work.** Code that already exists is a precondition, not a task. Confirm with a code read or a spec-reviewer pass.
- **Don't order by layer when you can order by reviewable slice.** "All the data models, then all the endpoints, then the UI" defers every review to the end. Cut vertically.
- **Don't omit a definition of done.** Every package's DoD ties back to the repo's development guidelines plus a task-specific reviewable outcome.
- **Don't hedge in the body.** Undecided design goes in Open questions, not as a "we might…" sentence in a task package.
- **Don't put calendar dates or effort estimates in the body** unless asked. A plan sequences by dependency and reviewability; estimates are a separate concern and belong, if anywhere, in the closing block.
- **Don't put task bodies in `plan.md`.** It holds the graph, the order, and the closing block; the hybrid package bodies live in the per-task `NN-…md` files. `plan.md` links to them.
- **Don't renumber task files on edit.** Numbers are assigned in implementation order at authoring and are append-only afterward — a renumber breaks every cross-reference in the graph and table.

## Adding done certificates

A task's `Definition of done` is a *claim*; a **done certificate** is the *protocol that proves it* — a task-specific semi-formal reasoning certificate the companion **done-certificates** skill authors, that a *validating agent* later runs against the code. spec-planner writes the DoD; done-certificates writes the protocol; a validator discharges it.

**When to author.** On by default (Phase 4.5). In an **interactive session, prompt first** — a single yes/no defaulting to yes ("Author a done certificate per task? (default: yes)"); honour an explicit "no". In a **non-interactive run**, include them without prompting unless the request said to skip. An outright "add done certificates" is just an explicit yes.

**Mechanics.** Delegate to done-certificates after Phase 4. It writes **one certificate per task** into the plan folder's `certificates/` subfolder (`.specs/plans/YYYY-MM-DD-title/certificates/NN-…md`, mirroring the task numbers), obligations drawn from each task's DoD with evidence/checks named but status and verdict left blank, and adds a two-way `**Certificate:**` link to each task header. spec-planner owns the plan and its Phase 5 cross-link pass; done-certificates owns the `certificates/` subfolder; a separate validating agent (neither skill) discharges each certificate as its task is built.

If certificates are skipped, the Phase 5 *Done certificates* checklist section does not apply — note in `plan.md` that they were not authored so a later pass can add them.

## When invoked by spec-creator

spec-creator may delegate here after drafting or merging a change spec, when the user asks "and how do we build it". In that case the spec set, owner, and the development-guidelines source are already established — skip the redundant parts of Phase 1, confirm the DoD baseline, and produce the plan. spec-creator owns any spec edits; spec-planner owns the plan and its cross-link pass.

## Reference files

- [`references/task-decomposition.md`](references/task-decomposition.md) — How to slice a spec into reviewable task packages, the four dependency edge types (build / data / contract / review), the reviewability-ordering method, and milestone grouping. Read before Phases 2–3.
- [`references/plan-template.md`](references/plan-template.md) — The two plan skeletons: `plan.md` (header, source/DoD note, Mermaid + table task graph, implementation-order section, closing block) and the per-task `NN-…md` file (header, hybrid structure + step checklist + definition of done). Read before Phase 4.
- [`references/checklist.md`](references/checklist.md) — Pre-handoff checklist: graph coherence (Mermaid ↔ table, no cycles), coverage (every spec section mapped), DoD present on every package, voice, cross-links. Read after writing, before declaring done.
