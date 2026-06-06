# Pre-handoff checklist

Run through this before declaring a plan done. It enforces the core principle (reviewable decomposition, a definition of done on every package) and the structural conventions. Mistakes here are easy to introduce and hard to spot once the plan is shared.

---

## Folder and document structure

- [ ] The plan is a **folder** at `.specs/plans/YYYY-MM-DD-snake_case_title/` — or `.specs/<package>/plans/…` (or a co-located `<package-location>/.specs/plans/…`) for a per-package plan — with an ISO date prefix and lowercase snake_case title, not a single file.
- [ ] The folder has `plan.md` at its root plus the task subfolders of the kanban board: `backlog/` (always), and `in-progress/`, `blocked/`, `done/` once a build has moved tasks into them. A freshly authored plan has **every task in `backlog/`** and no other subfolder yet.
- [ ] Each task is **one `NN-snake_case_task.md` file in exactly one subfolder**, beside its `NN-snake_case_task-certificate.md`; there is no per-task `Status` field and no `certificates/` subfolder.
- [ ] `plan.md` header is `**Status:** … · **Layout:** kanban · **Date:** … · **Owner:** … · **Source spec:** …`; Status is one of `Draft`, `Accepted`, `In progress`, `Done`.
- [ ] `plan.md` has a `Source and definition-of-done baseline` section naming the spec, what is already built, and where the per-task DoD comes from.
- [ ] `plan.md` holds no task bodies — only the graph, the order/milestones, and the closing block; bodies live in the task files.
- [ ] `plan.md`'s closing `## Assumptions and open questions` block is present with all three subheadings; `(None at this stage.)` where empty.
- [ ] Each task file opens with `# Task NN — <title>` and a `**Plan:** [plan.md](../plan.md) · **Certificate:** [NN-snake_case_task-certificate.md](NN-snake_case_task-certificate.md)` line, and carries **no `Status:` field** (its subfolder is its status).

---

## Graph coherence

- [ ] The `## Task graph` section in `plan.md` has both a Mermaid `graph TD` block and a dependency table.
- [ ] **The Mermaid edges and the dependency table agree.** Walk both: every edge in one appears in the other. The table is the source of truth; fix the graph if they diverge.
- [ ] Mermaid node ids are the task numbers (`01`, `02`, …), identical to the file prefixes and table keys.
- [ ] **Every task number in the table has a matching `NN-…md` file in one of the four subfolders, and every task file has a table row.**
- [ ] Each table row references its task by **number** (no path link — the file is found by glob across the subfolders, `*/NN-*.md`); each task file's `Plan:` line links back to `../plan.md`.
- [ ] **Every `Depends on` references a lower task number** — the property of numbering in implementation order. A dependency on a higher number means the order or the dependency is wrong.
- [ ] **The graph is a DAG — no cycle.** A cycle means a mis-cut package; re-slice rather than dropping an edge.
- [ ] Each dependency names its edge kind (build / data / contract / review).

---

## Task files

- [ ] Every task file has `Implements`, `Depends on`, `Produces`, and `Pointers`.
- [ ] Every task file has a `## Steps` checklist and a `## Definition of done` checklist.
- [ ] **Every task's DoD ends with a `Reviewable:` line** naming the concrete action a reviewer takes to sign off.
- [ ] Every DoD references the repo baseline (tests, lint/format, named-constant limits) plus task-specific acceptance — not one or the other.
- [ ] No task is so large its DoD exceeds ~6 items or so small it is a one-line change folded better into a neighbour.
- [ ] Tasks are vertical slices (a path that works end to end) rather than horizontal layers, wherever the spec allows it.

---

## Coverage

- [ ] **Every in-scope spec section maps to at least one task file** (forward coverage). Walk the spec; for each section, find the task file whose `Implements` names it.
- [ ] **Every task file names the spec section it implements** (reverse coverage).
- [ ] Work the code already provides is listed under `Already built` in `plan.md` as a precondition, not scheduled as a task.
- [ ] Any spec section with no task, or any task with no spec section, is either resolved or recorded in `plan.md`'s Open questions and flagged to the user.

---

## Ordering

- [ ] The stated `Order` respects every edge in the dependency table (it is a valid topological order).
- [ ] The order is biased for reviewability: enablers that are reviewed-through (auth, app shell, schema, seed data, CI) lead, even where a naive sort would defer them.
- [ ] Milestones each end at a reviewable state, with a named `Demonstrable when complete` and a `Review gate`.

---

## Cross-links

- [ ] **`.specs/README.md` lists the plan** under a Plans section, pointed at the folder's `plan.md` (the index was created if absent). A plan the index does not reference is invisible.
- [ ] Every link to a spec page resolves from the task's subfolder (one level deeper than the plan root) — from a repo-wide plan, `../../../foo.md` for a global page and `../../../<package>/specs/NN-name.md` for a per-package page; from a per-package plan at `.specs/<package>/plans/…`, the package's own spec is `../../../specs/…` and a global page `../../../../…`. Because `backlog/`, `in-progress/`, `blocked/`, and `done/` are all at the same depth, these links are authored once and stay correct as a task moves.
- [ ] `file:line` pointers in task files point at real paths in the current branch.

---

## Done certificates

Authoring done certificates is the **default** — included unless the user declined (prompted in an interactive session, auto-included otherwise; see the skill's Phase 4.5). This section applies **when certificates were authored**; if they were skipped, confirm `plan.md` records that they were not authored and move on.

- [ ] **Every task file has a matching certificate** co-located as `NN-snake_case_task-certificate.md` in the **same subfolder** as its task (no `certificates/` subfolder), the `NN` identical to the task it certifies, and every certificate maps back to a real task file.
- [ ] Each certificate's **obligations are one-to-one with the task's `Definition of done`**, in the same order, the last obligation being the task's `Reviewable:` item.
- [ ] **The certificate ↔ task links resolve both ways** — the certificate links same-directory to `[NN-…md](NN-…md)` and to `[plan.md](../plan.md)`; the task file header carries a `**Certificate:** [NN-…-certificate.md](NN-…-certificate.md)` line.
- [ ] Each certificate is **authored, not discharged** — statuses are `☐ unverified` and `VERDICT`/`CONFIDENCE`/`SUMMARY` are blank. spec-planner does not run the validation; a separate agent does.
- [ ] Each obligation names **specific evidence to collect** (file:line, a named test, a trace) rather than "verify it works", and the conclusion carries the verdict rubric.

## Voice

- [ ] No emoji, no exclamation points.
- [ ] No "easily", "simply", "just", "powerful", "robust", "seamlessly".
- [ ] Steps and `Produces` use future/imperative voice; the body does not restate the spec's prose.
- [ ] Decisions use past tense or "we chose" framing; Open questions use question form.
- [ ] No calendar dates or effort estimates in the body unless the user asked for them.

---

## When the checklist finds a problem

1. **Typo or broken pointer** — fix in place, re-check.
2. **Mermaid ↔ table mismatch** — make the graph match the table (the table is canonical), re-check.
3. **Cycle in the graph** — re-cut the packages; a cycle is never resolved by deleting an edge.
4. **Coverage gap** — add the missing task file, or record the gap in `plan.md`'s Open questions and flag it to the user.
5. **Missing DoD or `Reviewable:` line** — add it; a task without one is not a plan, it is a wish.
6. **`Depends on` references a higher number** — re-check the order; either the sequence is wrong or the edge is. Renumber only if the plan has not yet been executed against (otherwise append-only).

Run the checklist again after fixes. Fresh eyes catch what mid-fix eyes miss.
