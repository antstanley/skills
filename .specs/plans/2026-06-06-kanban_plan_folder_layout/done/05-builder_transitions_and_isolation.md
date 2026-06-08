# Task 05 — Builder transitions + isolation

**Plan:** [plan.md](../plan.md) · **Certificate:** [05-builder_transitions_and_isolation-certificate.md](05-builder_transitions_and_isolation-certificate.md)

**Implements:** [2026-06-05-kanban_plan_folder_layout.md](../../../changes/2026-06-05-kanban_plan_folder_layout.md) §F (orchestrator moves files on the main tree as one transaction), §B (status writes become moves; park → `blocked/`), §E (subagent-brief spec-link depth +1), §C (build-loop reads the co-located certificate)
**Depends on:** 01, 03, 04
**Produces:** spec-builder's `build-loop.md`, `subagent-brief.md`, `workspaces.md`, and `portability.md` describe a status transition as a single serialized file move the orchestrator performs **on the main tree** — on dispatch `backlog/NN-*.md` (and its `-certificate.md`) → `in-progress/`; on both-gates-pass-and-merge → `done/`; on park → `blocked/` with a `**Blocked:** <reason>` header line — never inside a task workspace; the certificate is read from the task's current subfolder on main; spec-link depth gains one `../`; and the sequential fallback performs the same moves
**Pointers:** `plugins/spec-builder/skills/spec-builder/references/build-loop.md` — step 1 mark-in-progress (L22), step 3 certificate path (L50), step 4 mark-done (L63–73), parking (L91), Invariants (L104–114); `subagent-brief.md` — certificate path (L29), spec-link depth (L37–40); `workspaces.md` — add a main-tree-only-moves assertion (none exists today; ~Core principle, L15–16); `portability.md` — sequential fallback "update the plan board" (L78)

## Steps

- [ ] `build-loop.md` step 1 (L22): "Mark the task In progress" becomes "move `backlog/NN-*.md` and its `NN-*-certificate.md` into `in-progress/` (on the main tree)".
- [ ] `build-loop.md` step 3 (L50): the certificate read path becomes the task's sibling in its current subfolder (`in-progress/NN-*-certificate.md`), read from the **main tree**, never a sub-agent's workspace copy.
- [ ] `build-loop.md` step 4 (L63–73): "Set the task file `Status: Done`" becomes "move the task file and its `-certificate.md` from `in-progress/` into `done/`" — the move into `done/` is the commit point, the last action *after* the code merges into the integration point; then recompute `plan.md`'s `Status` from the subfolders.
- [ ] `build-loop.md` parking (L91): a task parked past its retry bound moves into `blocked/` and gains a `**Blocked:** <reason>` header line (it no longer "stays In progress with a note"); the workspace is left intact.
- [ ] `build-loop.md` Invariants (L104–114): restate "Done" as "task file in `done/` after merge"; add that folder membership is authoritative on resume and a task is in exactly one of the four subfolders.
- [ ] `subagent-brief.md`: the spec-link depth/resolution rule (L37–40) gains one `../` (global page `../../../foo.md`, per-package `../../../<package>/specs/…`) — matching the canonical depth in `plan-template.md` (task 01, an upstream dependency via 03/04) **verbatim**, which the checklist (02) and planner eval (07) also anchor to. Re-depth the *per-package-plan* sub-clause in the same rule (the `.specs/<package>/plans/…` case) by one level too — block E omits it (see plan.md Open questions). The certificate path (L29) is the task's current subfolder sibling read from main.
- [ ] `workspaces.md`: add an assertion (near the Core principle / lifecycle, ~L15–16) that plan-folder file moves (`backlog/`→`in-progress/`→`blocked/`/`done/`) are a main-tree-only operation by the orchestrator; task workspaces hold code, never the plan folder, and never move task files.
- [ ] `portability.md` (L78): the sequential fallback's "update the plan board" becomes the same folder moves (task + certificate into `done/`, or `blocked/` on park), performed by the orchestrator on the main tree.
- [ ] Do **not** edit `semi-formal-review` or the reasoning-method triangle.
- [ ] Run `scripts/sync-skills.sh` and confirm `scripts/check.sh` passes.

## Definition of done

- [ ] `build-loop.md` steps 1, 3, 4 and parking are folder moves of the task **and** its `-certificate.md` (dispatch → `in-progress/`, merge → `done/`, park → `blocked/` + `**Blocked:**` line); the certificate is read from the main-tree current subfolder; Invariants reflect folder-as-status and one-folder-per-task.
- [ ] `subagent-brief.md`'s spec-link depth gains one `../` and reads **identically** to the canonical `plan-template.md` depth from task 01 (the link-depth invariant; the per-package-plan sub-clause re-depthed too); its certificate path is the current-subfolder sibling on main.
- [ ] `workspaces.md` asserts plan-folder moves are main-tree-only by the orchestrator (a newly added statement); `portability.md`'s sequential fallback performs the same moves.
- [ ] `semi-formal-review` and the reasoning-method triangle are untouched.
- [ ] `scripts/sync-skills.sh` was re-run and `scripts/check.sh` passes (no `skills/` drift).
- [ ] Meets the repo definition of done (Conventional Commits, `scripts/check.sh` green — see plan.md baseline).
- [ ] Reviewable: a reader traces one task from dispatch to merge to (alternatively) park and sees a single serialized main-tree move of task + certificate at each step, the depth rule matching task 01/02, and no in-workspace plan-folder mutation; `scripts/check.sh` is green.
