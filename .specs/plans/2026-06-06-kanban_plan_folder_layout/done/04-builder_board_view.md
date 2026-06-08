# Task 04 — Builder board view

**Plan:** [plan.md](../plan.md) · **Certificate:** [04-builder_board_view-certificate.md](04-builder_board_view-certificate.md)

**Implements:** [2026-06-05-kanban_plan_folder_layout.md](../../../changes/2026-06-05-kanban_plan_folder_layout.md) §G (planner→builder discovery contract), §H (builder side — `Layout:` marker inference + legacy-flat migrate-in-place), §F (read side — bookkeeping reads folder membership), §B (recompute `plan.md` `Status` from subfolders)
**Depends on:** 01
**Produces:** spec-builder's `SKILL.md` + `orchestration.md` describe enumerating the full task set as the **union** of `backlog/`/`in-progress/`/`blocked/`/`done/` (missing folder = empty), building the DAG from `plan.md`'s number-keyed dependency table, deriving `ready` = `backlog/` tasks whose `Depends-on` are all in `done/`, `running` = `in-progress/`, parked = `blocked/`, `done` = `done/`; recomputing `plan.md`'s plan-level `Status` from the subfolders after each transition; and detecting kanban via the `**Layout:** kanban` marker (or a `backlog/` subfolder) while migrating a legacy-flat plan in place
**Pointers:** `plugins/spec-builder/skills/spec-builder/SKILL.md` — core principle rule 3 (L35–37), "optimised for" line (L57–60), Phase 1 read (L115–120), Phase 4 status-write (L148–151), and **all** `certificates/` mentions (L59 and L115 — update, do not keep); `plugins/spec-builder/skills/spec-builder/references/orchestration.md` — Reading the plan (L36–50), wave-scheduler sets (L54–85), §Status bookkeeping (L140–161)

## Steps

- [ ] `grep -n 'certificates/\|Status:' ` the two files first to enumerate every flat-layout mention (the change spec's anchors are not exhaustive — `SKILL.md` references `certificates/` at L59 and L115 beyond the named sites); fix all of them.
- [ ] In `SKILL.md` rule 3 (L35–37): the plan folder is a board of folders; tasks move between `backlog/`/`in-progress/`/`blocked/`/`done/` as status changes and `plan.md`'s plan-level `Status` is recomputed from the subfolder union; progress is `ls`-legible and resume reads folder membership.
- [ ] Update the "optimised for" line (L57–60): the builder reads the number-keyed dependency table as the source of truth and the `**Layout:** kanban` marker (or a `backlog/` subfolder) that distinguishes kanban from legacy-flat; the per-task `Status` field is gone (status is the subfolder).
- [ ] Update Phase 1 read (L115–120): enumerate the union of the four subfolders (missing = empty); detect layout via the marker / `backlog/`; on a legacy-flat plan (no marker, no `backlog/`, task files at the root) migrate in place — create the subfolders, move each task by its `Status:` value (`Done`→`done/`, `In progress`→`in-progress/`, else `backlog/`), relocate each `certificates/NN-*.md` to a co-located `NN-*-certificate.md`, drop the per-task `Status` field, and stamp `**Layout:** kanban` — rather than reading two shapes or globbing it empty.
- [ ] Update Phase 4 status-write (L148–151): replace "update the task file `Status`" with the folder move (`in-progress/` → `done/` on success, → `blocked/` on park) and "recompute `plan.md` `Status` from the subfolders" (`In progress` once any task left `backlog/`; `Done` once every task is in `done/`).
- [ ] In `orchestration.md` "Reading the plan" (L36–50): enumerate the union; treat `done/` tasks as preconditions; resume from the current folder membership; include the legacy-flat detect-and-migrate step.
- [ ] Update the wave-scheduler sets (L54–85): `ready` = `backlog/` whose `Depends-on` ⊆ `done/`; `running` = `in-progress/`; parked = `blocked/`; `done` = `done/` — pop the highest-reviewability ready task *from `backlog/`*; on both gates pass move it `in-progress/`→`done/`; on park move it `in-progress/`→`blocked/`.
- [ ] Rewrite §Status bookkeeping (L140–161): the "Task file `Status`" subsection becomes "task location (subfolder)" with the move semantics; the `plan.md` `Status` subsection becomes "recomputed from the subfolders after each transition, the only field the builder writes to `plan.md`"; the resume note reads `done` = tasks in `done/`. Certificate `State` and the build log are unchanged.
- [ ] Do **not** edit `semi-formal-review` or the reasoning-method triangle.
- [ ] Run `scripts/sync-skills.sh` and confirm `scripts/check.sh` passes.

## Definition of done

- [ ] `SKILL.md` + `orchestration.md` describe enumerating the union of the four subfolders, deriving ready/running/blocked/done from folder membership, recomputing `plan.md`'s `Status` from the subfolders, and detecting + migrating a legacy-flat plan in place.
- [ ] **Every** `certificates/` mention and per-task `Status`-field flip in the two files is converted (verified by a clean `grep` for `certificates/` and a per-task `Status:` field); the union enumeration names all four buckets including `blocked/`.
- [ ] `semi-formal-review` and the reasoning-method triangle are untouched (verified by a clean `git diff` scope).
- [ ] `scripts/sync-skills.sh` was re-run and `scripts/check.sh` passes (no `skills/` drift).
- [ ] Meets the repo definition of done (Conventional Commits, `scripts/check.sh` green — see plan.md baseline).
- [ ] Reviewable: a reader follows the builder reading a kanban plan and a legacy-flat plan and sees, in both, a single coherent enumeration → schedule → recompute path with no flat-layout residue; `scripts/check.sh` is green.
