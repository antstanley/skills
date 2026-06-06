# Task 09 — Migrate existing flat plans

**Plan:** [plan.md](plan.md) · **Status:** Todo · **Certificate:** [certificates/09-migrate_existing_flat_plans.md](certificates/09-migrate_existing_flat_plans.md)

**Implements:** [2026-06-05-kanban_plan_folder_layout.md](../../changes/2026-06-05-kanban_plan_folder_layout.md) §H (legacy-flat migration) and Merge-plan step 4 (migrate the seven existing `.specs/plans/` folders in place)
**Depends on:** 01
**Produces:** the seven existing flat plan folders under `.specs/plans/` migrated in place to the kanban layout — each plan.md stamped `**Layout:** kanban`, every task file filed into the subfolder its old `Status:` maps to (with the per-task `Status` field dropped), and the one `certificates/` subfolder (benchmark) relocated to co-located `done/NN-*-certificate.md` files — so the seven plans match the contract task 01 defines and the builder (task 04) reads
**Pointers:** `.specs/plans/` (the seven folders); the mapping rule lives in §H of the change spec. This task edits **only** `.specs/plans/**` (not the new plan folder being authored here, which the build migrates by the same rule when it runs)

## Mapping (from the folder inventory)

| Plan folder | Task files → subfolder | `certificates/`? | plan.md |
|---|---|---|---|
| `2026-05-27-spec_workflow_benchmark` | 22 files (`01, 02, 04–23`; **no `03`**), all `Done` → `done/` | **yes** — 22 files → relocate to `done/NN-*-certificate.md` | stamp `Layout: kanban`; plan `Status: Done` kept |
| `2026-05-28-close_group_a_spec_code_gaps` | 01–05 (`Done`) → `done/` | no | stamp marker |
| `2026-05-28-add_live_container_verification` | 01–03 (`Done`) → `done/` | no | stamp marker |
| `2026-05-30-implement_eval_judge_harness` | 01–08 (`Todo`) → `backlog/` | no | stamp marker; plan `Status: Draft` kept |
| `2026-05-28-add_lighter_precanned_arm` | 01–02 (`Proposed`) → `backlog/` | no | stamp marker (non-standard status → `backlog/`) |
| `2026-05-28-raise_recursive_arm_timeout_budget` | none (single-task, inline) | no | stamp marker only — no subfolders |
| `2026-05-29-tolerate_markdown_verdict_lines` | none (single-task, inline) | no | stamp marker only — no subfolders |

**Rule for off-nominal cases:** any task `Status` that is not `Done` or `In progress` (`Todo`, `Proposed`, `Draft`, or absent) files to `backlog/`. A plan with no task files gets the `**Layout:** kanban` marker and nothing else (no empty subfolders — git/jj do not track them). No task starts in `blocked/` (it is created only when a build parks a task).

## Steps

- [ ] Re-confirm each task file's current `**Status:**` value before moving it (do not assume from the table — read the header), so the mapping reflects the file, not this plan's snapshot.
- [ ] For each plan with task files: create the needed subfolders, `git`/`jj`-move each `NN-*.md` into `done/`/`in-progress/`/`backlog/` per its status, and remove the per-task `**Status:**` field from each moved file's header (folder is now status).
- [ ] For `2026-05-27-spec_workflow_benchmark`: move all 22 task files (`01, 02, 04–23` — there is no `03`, an append-only gap from a retired task) into `done/`; relocate each `certificates/NN-*.md` to `done/NN-*-certificate.md` (rename with the `-certificate` suffix, co-located beside its task); remove the now-empty `certificates/` subfolder.
- [ ] For the two single-task plans (`raise_recursive_arm_timeout_budget`, `tolerate_markdown_verdict_lines`): add only the `**Layout:** kanban` marker to plan.md; create no subfolders.
- [ ] Add `**Layout:** kanban` to all seven plan.md headers (keep each plan-level `**Status:**` as-is — it is a different axis and does not move).
- [ ] Verify each migrated plan: every task file is in exactly one subfolder; no `certificates/` subfolder remains anywhere; no per-task `**Status:**` field remains; each plan.md carries the marker.
- [ ] Confirm `scripts/check.sh` passes (`.specs/plans/**` is outside the synced `skills/` tree and outside Python — the gate stays green).

## Definition of done

- [ ] All seven plan.md headers carry `**Layout:** kanban`; each plan-level `Status` is unchanged.
- [ ] Every task file is filed into the subfolder its real `Status:` maps to (Done→`done/`, In progress→`in-progress/`, anything else→`backlog/`), with the per-task `Status` field removed; each task is in exactly one subfolder.
- [ ] The benchmark plan's `certificates/` subfolder is gone, its 22 certificates (`01, 02, 04–23`) relocated to co-located `done/NN-*-certificate.md` beside their tasks; no `certificates/` subfolder remains in any of the seven.
- [ ] The two task-file-less plans carry the marker and no subfolders.
- [ ] `scripts/check.sh` passes (these are `.specs/` files, not synced; the gate is green).
- [ ] Meets the repo definition of done (Conventional Commits, `scripts/check.sh` green — see plan.md baseline; use `jj`-aware moves so the working copy stays consistent).
- [ ] Reviewable: `ls -R` of each migrated plan shows the kanban board (task files filed by status, co-located `NN-*-certificate.md`, no `certificates/` subfolder); a `grep` for a per-task `**Status:**` header across `.specs/plans/**` returns nothing; `scripts/check.sh` is green.
