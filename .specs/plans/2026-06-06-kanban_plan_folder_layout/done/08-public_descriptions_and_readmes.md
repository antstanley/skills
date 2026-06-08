# Task 08 — Public descriptions + READMEs

**Plan:** [plan.md](../plan.md) · **Certificate:** [08-public_descriptions_and_readmes-certificate.md](08-public_descriptions_and_readmes-certificate.md)

**Implements:** [2026-06-05-kanban_plan_folder_layout.md](../../../changes/2026-06-05-kanban_plan_folder_layout.md) — the "Both `plugin.json` descriptions" and "Both plugin `README.md` files" rows (manual edit — not synced, not checked)
**Depends on:** 01, 04, 05
**Produces:** both `.claude-plugin/plugin.json` descriptions and both plugin `README.md` files reworded from the flat "live board / `Status` / optional `certificates/` subfolder" framing to folder-as-status with co-located certificates — the surface `scripts/sync-skills.sh` does not regenerate and `scripts/check.sh` does not gate, so it must be hand-edited or it goes silently stale
**Pointers:** `plugins/spec-builder/.claude-plugin/plugin.json` — description (L4, "live board"); `plugins/spec-builder/README.md` — intro/pipeline (L5, "optional `certificates/` subfolder" + "live board"), optimised-for (L29, "reads … the `certificates/` subfolder"); `plugins/spec-planner/.claude-plugin/plugin.json` (L4) and `plugins/spec-planner/README.md` — verify (recon found these largely neutral; touch only where the flat framing appears)

## Steps

- [ ] `grep -n 'certificates/\|live board\|Status\|NN-task' ` across the four files to find every stale passage (the recon anchors are a starting point, not exhaustive).
- [ ] `plugins/spec-builder/.claude-plugin/plugin.json` (L4): reword "keeping the plan folder current as a live board" to folder-as-status — the orchestrator moves task files between `backlog/`/`in-progress/`/`blocked/`/`done/` as they progress.
- [ ] `plugins/spec-builder/README.md` (L5): replace "the `NN-task.md` files, and the optional `certificates/` subfolder" + "live board" with the four status folders holding `NN-task.md` + co-located `NN-task-certificate.md`, where folder location is status.
- [ ] `plugins/spec-builder/README.md` (L29): replace "reads … the `certificates/` subfolder" with certificates co-located per task as `NN-task-certificate.md`; align any build-loop status-flip prose with folder moves.
- [ ] `plugins/spec-planner/.claude-plugin/plugin.json` (L4) and `plugins/spec-planner/README.md`: verify against the new layout and update **only** where flat-layout / `Status`-field / `certificates/`-subfolder framing appears; leave already-neutral prose unchanged.
- [ ] Note in the commit that these four files are not covered by `sync-skills.sh` / `check.sh` and were edited by hand; do **not** run `sync-skills.sh` expecting them to propagate (they live outside `skills/<name>/`).
- [ ] Confirm `scripts/check.sh` still passes (these files are outside the synced tree and outside Python — the gate stays green).

## Definition of done

- [ ] `spec-builder`'s `plugin.json` description and `README.md` describe folder-as-status with co-located certificates — no "live board", no "optional `certificates/` subfolder", no per-task `Status`-field framing.
- [ ] `spec-planner`'s `plugin.json` + `README.md` are verified against the new layout and updated wherever stale (and left untouched where already neutral), with a clean `grep` for the flat-layout phrases across all four files afterward.
- [ ] The four files are consistent with the layout defined in task 01 and the build loop in tasks 04/05.
- [ ] `scripts/check.sh` passes (these are un-synced, un-drift-checked files; the gate is green regardless).
- [ ] Meets the repo definition of done (Conventional Commits, `scripts/check.sh` green — see plan.md baseline; hand-edited surface).
- [ ] Reviewable: a reader reads both READMEs and both plugin descriptions and finds the kanban layout described consistently with the skills; a `grep` for "live board" / "`certificates/`" returns nothing stale; `scripts/check.sh` is green.
