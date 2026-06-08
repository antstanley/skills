# Task 01 — Planner authoring contract

**Plan:** [plan.md](../plan.md) · **Certificate:** [01-planner_authoring_contract-certificate.md](01-planner_authoring_contract-certificate.md)

**Implements:** [2026-06-05-kanban_plan_folder_layout.md](../../../changes/2026-06-05-kanban_plan_folder_layout.md) §A (board of folders), §B (status is folder location — planner side), §D (tasks referenced by number), §E (link depth +1), §H (`Layout:` marker — planner side), and the planner side of §C (certificates authored into `backlog/`)
**Depends on:** —
**Produces:** the canonical kanban layout fully specified in the planner `SKILL.md` and `plan-template.md` — the four-folder tree (`plan.md` at root + `backlog/`/`in-progress/`/`blocked/`/`done/`), no per-task `**Status:**` field, a dependency table that keys tasks by number (no path link), `../../../` spec-link depth authored once, a `**Layout:** kanban` header field, and certificates co-located beside their tasks — so a planner author can author a kanban plan
**Pointers:** `plugins/spec-planner/skills/spec-planner/SKILL.md` — frontmatter description (L3), Phase 4 (L73–83), Phase 4.5 (L87–89), Phase 5 step 2 (L96), Phase 5 done-cert verify (L99), §Adding done certificates (L113–121); `plugins/spec-planner/skills/spec-planner/references/plan-template.md` — folder tree (L5–12), Status lifecycle (L20–37), `plan.md` header (L46), dependency table (L81–91), task-file skeleton (L130–159), Notes (L170)

## Steps

- [ ] In `plan-template.md`, replace the flat folder tree (L5–12) with the kanban tree from §A: `plan.md` at the root, then `backlog/` (holding `NN-task.md` + co-located `NN-task-certificate.md`), `in-progress/`, `blocked/`, and `done/`; add the prose that a task's status is the subfolder it sits in, that a new plan has every task in `backlog/`, and that spec-planner creates `backlog/` while spec-builder lazily creates the other three.
- [ ] Rewrite the Status-lifecycle section (L20–37): keep the `plan.md` `Status` table (Draft → Accepted → In progress → Done) but note spec-builder recomputes it from the subfolders; **remove the per-task `Status` table** and replace it with the folder-as-status mapping (`backlog/`=Todo → `in-progress/` → `done/`, or `blocked/` when parked, with a `**Blocked:** <reason>` header line).
- [ ] Add `**Layout:** kanban` to the `plan.md` skeleton header (L46) per §H.
- [ ] Rewrite the dependency-table block (L81–91) per §D: each row references a task by number and title (`01 · passphrase lock`), **not** a path hyperlink; state that a task's file is found by globbing across the four subfolders (`*/NN-*.md`); keep the "`Depends on` references a lower number" rule.
- [ ] Rewrite the task-file skeleton (L130–159) per §B/§C/§E: drop the `**Status:**` field; make the back-link `[plan.md](../plan.md)`; add `**Certificate:** [NN-…-certificate.md](NN-…-certificate.md)`; re-depth the `Implements` spec links to `../../../` (global) / `../../../<package>/specs/…` (per-package).
- [ ] Rewrite the Notes "Status fields make the folder a live board" item (L170) into folder-membership terms (spec-builder moves files between subfolders; `plan.md`'s `Status` is recomputed from them).
- [ ] In `SKILL.md`, update Phase 4 (L73–83): create `backlog/` and author every task into it; the task file carries a `**Plan:**` back-link and `**Certificate:**` link but no `Status:` field.
- [ ] Update Phase 4.5 (L87–89) and §Adding done certificates (L113–121): certificates are authored into `backlog/` beside their tasks as `NN-snake_case_task-certificate.md` (no `certificates/` subfolder); the two-way links are same-directory + `../plan.md`; redraw the ownership line (done-certificates authors into `backlog/` and owns content; spec-builder owns moving them).
- [ ] Update Phase 5 step 2 (L96) per §D/§E: spec-page links resolve from a task subfolder (`../../../foo.md`), authored once and move-stable; dependency-table rows reference tasks by number, found by glob across the four subfolders; verify against the current subfolders. Also re-depth the Phase 5 done-certificate verify (L99) to the co-located `NN-…-certificate.md` found across the four subfolders (no `certificates/` path).
- [ ] Update the frontmatter description (L3) to name the new shape (`plan.md` at root + four task subfolders that files move between).
- [ ] Run `scripts/sync-skills.sh` and confirm `scripts/check.sh` passes (no `skills/` drift).

## Definition of done

- [ ] `plan-template.md` and `SKILL.md` describe the four-folder board, drop the per-task `Status:` field, key the dependency table by number, carry the `**Layout:** kanban` header, use `../../../` spec-link depth, and co-locate certificates — with no residual flat-layout/`certificates/`-subfolder/`Status:`-field wording in either file.
- [ ] The folder tree, the worked-example task/certificate names, and the `../../../` depth in `plan-template.md` are stated so tasks 02 (checklist/decomposition), 03 (certificate-template), and 07 (planner eval) can match them verbatim (the two cross-file invariants in plan.md).
- [ ] `scripts/sync-skills.sh` was re-run and `scripts/check.sh` passes (no `skills/` drift; Python suite unaffected and green).
- [ ] Meets the repo definition of done (Conventional Commits subject, `jj` front end, `scripts/check.sh` green — see plan.md baseline; no Python touched).
- [ ] Reviewable: a reader opens the edited `SKILL.md` + `plan-template.md` and finds a self-consistent description of authoring a kanban plan — four subfolders, number-keyed table, `../../../` links, `Layout: kanban`, co-located certificates — and `scripts/check.sh` is green.
