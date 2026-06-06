# Task 03 — Certificate co-location

**Plan:** [plan.md](plan.md) · **Status:** Todo · **Certificate:** [certificates/03-certificate_colocation.md](certificates/03-certificate_colocation.md)

**Implements:** [2026-06-05-kanban_plan_folder_layout.md](../../changes/2026-06-05-kanban_plan_folder_layout.md) §C (a certificate co-locates with its task and moves with it)
**Depends on:** 01
**Produces:** the done-certificates skill authors a certificate **beside** its task as `NN-snake_case_task-certificate.md` (no `certificates/` subfolder), into `backlog/` alongside the still-unbuilt task; same-directory cross-links (`[NN-…md](NN-…md)` to the task, `[plan.md](../plan.md)` to the plan) that survive every move; a next-free-`NN` that spans all four subfolders; and an ownership boundary where done-certificates authors content while spec-builder owns moving the file with its task
**Pointers:** `plugins/spec-planner/skills/done-certificates/SKILL.md` — §Where the certificate lives (L87–92), §When invoked / ownership (L94–96), next-free-`NN` logic (L92); `plugins/spec-planner/skills/done-certificates/references/certificate-template.md` — skeleton header link (L40), worked-example header link (L121)

## Steps

- [ ] In `SKILL.md` §Where the certificate lives (L87–92): replace the `certificates/` subfolder + `NN-snake_case_task.md` naming with co-location — the certificate is written beside its task as `NN-snake_case_task-certificate.md` (the `-certificate` suffix avoids colliding with the task's own file), authored into `backlog/` and moving with the task through `in-progress/`/`blocked/` into `done/` as one unit.
- [ ] Update the cross-link wording: certificate → task is same-directory `[NN-…md](NN-…md)`; certificate → plan is `[plan.md](../plan.md)`; the task header carries `**Certificate:** [NN-…-certificate.md](NN-…-certificate.md)`.
- [ ] Update §When invoked / ownership (L94–96): done-certificates authors certificates into `backlog/` and owns their content; spec-builder owns moving them (with their tasks) between subfolders. Remove "done-certificates owns the `certificates/` subfolder".
- [ ] Update the next-free-`NN` logic (L92): the scan spans the union of `backlog/`, `in-progress/`, `blocked/`, and `done/`, not a single `certificates/` folder.
- [ ] In `certificate-template.md`, change the skeleton header link (L40) from `[NN-…md](../NN-snake_case_task.md)` to same-directory `[NN-…md](NN-snake_case_task.md)`, keeping `· **Plan:** [plan.md](../plan.md)`.
- [ ] Change the worked-example header link (L121) the same way (`[01-passphrase_lock.md](01-passphrase_lock.md)`), and make the worked example match the canonical journal-app example in `plan-template.md` (task 01) **identically**.
- [ ] Run `scripts/sync-skills.sh` and confirm `scripts/check.sh` passes.

## Definition of done

- [ ] `SKILL.md` §Where the certificate lives describes a co-located `NN-snake_case_task-certificate.md` with same-directory + `../plan.md` links, authored into `backlog/`, and no `certificates/` subfolder anywhere in the file.
- [ ] The ownership boundary reads: done-certificates authors into `backlog/` and owns content; spec-builder owns moving certificates with their tasks. The next-free-`NN` scan spans the four subfolders.
- [ ] `certificate-template.md`'s skeleton and worked-example header links are same-directory to the task + `../plan.md`; the worked example matches task 01's **identically** (the shared-worked-example invariant) and the certificate-naming matches task 01's planner contract.
- [ ] `scripts/sync-skills.sh` was re-run and `scripts/check.sh` passes (no `skills/` drift).
- [ ] Meets the repo definition of done (Conventional Commits, `scripts/check.sh` green — see plan.md baseline).
- [ ] Reviewable: a reader traces a certificate from authoring (`backlog/NN-…-certificate.md`) through a move and confirms its `[NN-…md](NN-…md)` + `[../plan.md](../plan.md)` links stay valid in every subfolder; `scripts/check.sh` is green.
