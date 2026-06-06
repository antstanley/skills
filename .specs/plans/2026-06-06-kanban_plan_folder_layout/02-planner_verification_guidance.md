# Task 02 — Planner verification + decomposition guidance

**Plan:** [plan.md](plan.md) · **Status:** Todo · **Certificate:** [certificates/02-planner_verification_guidance.md](certificates/02-planner_verification_guidance.md)

**Implements:** [2026-06-05-kanban_plan_folder_layout.md](../../changes/2026-06-05-kanban_plan_folder_layout.md) §B/§D/§E (checklist side), §C (checklist done-certificates section), §H, and the `task-decomposition.md` reconciliation of `NN`-as-identity with folder moves
**Depends on:** 01
**Produces:** `checklist.md` and `task-decomposition.md` conformed to the kanban contract — the pre-handoff checklist verifies four subfolders, number-keyed references, the `../../../` depth, and co-located `NN-task-certificate.md` files; the decomposition guidance reconciles "one numbered file per task" with files that move between subfolders while keeping their number as identity
**Pointers:** `plugins/spec-planner/skills/spec-planner/references/checklist.md` — Folder/document structure (file-count L10, `plan.md` header L11, task-open L15), Graph coherence (L23–25), Cross-links (L63), Done certificates (L72, L74); `plugins/spec-planner/skills/spec-planner/references/task-decomposition.md` — output framing (L5), `NN`-assignment paragraph (L20), worked example (L93–110), build-order note (L125)

## Steps

- [ ] In `checklist.md` Folder-and-document-structure: change "a `plan.md` plus one `NN-…md` file per task" (L10) to the `plan.md`-at-root + four-subfolder shape; remove the per-task `Status` checks from the `plan.md` header item (L11) and the task-file-open item (L15), and re-depth the task back-link to `[../plan.md](../plan.md)`.
- [ ] In Graph coherence: update "every task number has a matching `NN-…md` file" (L24) to "in one of the four subfolders"; change "each table row links to its task file" (L25) to "references a task by number; the file is found by glob across the subfolders".
- [ ] In Cross-links (L63): re-depth the spec-page link rule to `../../../foo.md` (global) / `../../../<package>/specs/NN-name.md` (per-package), matching `plan-template.md` from task 01 **verbatim**. The same L63 item also carries a *per-package-plan* sub-clause (a plan under `.specs/<package>/plans/…`: own spec `../../specs/…`, global `../../../…`) — re-depth it by one level too (`../../../specs/…` / `../../../../…`); block E of the change spec omits this case (see plan.md Open questions).
- [ ] In the Done-certificates section: change the certificate location (L72) from `certificates/NN-…md` to a co-located `NN-snake_case_task-certificate.md` in the same subfolder as its task; update the two-way-link check (L74) to same-directory (`[NN-…md](NN-…md)`) + `[../plan.md](../plan.md)` and the task header `**Certificate:** [NN-…-certificate.md](NN-…-certificate.md)`.
- [ ] In `task-decomposition.md`: update the output-framing line (L5) and the `NN`-assignment paragraph (L20) so the file moves between `backlog/`/`in-progress/`/`blocked/`/`done/` while `NN` stays its immutable identity everywhere (table, graph, cross-refs, certificate name).
- [ ] Update the build-order note (L125): files sort by `NN` *within* each subfolder; the folder indicates current status, not build sequence — reconcile the old "the files sort in build order" rationale with `NN`-as-identity.
- [ ] Update the worked example (L93–110) to match the canonical journal-app example in `plan-template.md` (task 01) **identically** (the shared-worked-example invariant).
- [ ] Run `scripts/sync-skills.sh` and confirm `scripts/check.sh` passes.

## Definition of done

- [ ] `checklist.md` verifies the four-subfolder structure, number-keyed references, the `../../../` depth, and co-located `NN-task-certificate.md` files, with no per-task `Status`/`certificates/`-subfolder checks remaining.
- [ ] `task-decomposition.md` reconciles `NN`-as-identity with folder moves and updates the build-order rationale; no flat-layout wording remains.
- [ ] The `../../../` depth rule reads **identically** to `plan-template.md` (task 01), and the worked example matches it **identically** (the two cross-file invariants).
- [ ] `scripts/sync-skills.sh` was re-run and `scripts/check.sh` passes (no `skills/` drift).
- [ ] Meets the repo definition of done (Conventional Commits, `scripts/check.sh` green — see plan.md baseline).
- [ ] Reviewable: a reader runs the checklist mentally against a kanban plan and every check resolves to the four-subfolder layout; `diff` of the depth rule and worked example against task 01 shows no divergence; `scripts/check.sh` is green.
