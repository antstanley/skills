# Done Certificate — Task 09: Migrate existing flat plans

**Task:** [09-migrate_existing_flat_plans.md](../09-migrate_existing_flat_plans.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-06-06 — unverified

> This certificate is a verification protocol for Task 09. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 09) ≡ every obligation O1…O7 below holds, each backed by the evidence the obligation
names (a file location, a grep result, a directory listing, or a command result) — not by assertion.

## Premises

- **P1 — Goal.** The task migrates the seven existing flat plan folders under `.specs/plans/` in
  place to the kanban layout: each plan.md stamped `**Layout:** kanban`, every task file filed into
  the subfolder its old `Status:` maps to (per-task `Status` dropped), and the benchmark plan's
  `certificates/` subfolder relocated to co-located `done/NN-*-certificate.md` files — so the seven
  plans match the contract task 01 defines and the builder (task 04) reads.
- **P2 — Obligations.** The task is done iff O1…O7 all hold. One Oi per definition-of-done item, in
  DoD order; O7 is the `Reviewable:` item.
- **P3 — Invariants.** Must not break: the mapping rule from §H of the change spec
  (`Done`→`done/`, `In progress`→`in-progress/`, anything else→`backlog/`); each plan-level
  `**Status:**` axis (separate from the per-task status that becomes the folder); the
  `scripts/check.sh` gate (these are `.specs/plans/**` files, outside the synced `skills/` tree and
  outside Python — it stays green); and the task inventory of each migrated plan (the union of its
  subfolders must still enumerate every task once, with none dropped or duplicated).

## Obligations

- **O1 — All seven plan.md headers carry `**Layout:** kanban`; each plan-level Status unchanged.**
  - *Claim:* every one of the seven `.specs/plans/<folder>/plan.md` headers contains
    `**Layout:** kanban`, and each plan's pre-existing `**Status:**` value is unchanged.
  - *Evidence to collect:* run `grep -rl 'Layout:.*kanban' .specs/plans/*/plan.md` over the seven
    folders — expect all seven plan.md paths listed
    (`2026-05-27-spec_workflow_benchmark`, `2026-05-28-close_group_a_spec_code_gaps`,
    `2026-05-28-add_live_container_verification`, `2026-05-30-implement_eval_judge_harness`,
    `2026-05-28-add_lighter_precanned_arm`, `2026-05-28-raise_recursive_arm_timeout_budget`,
    `2026-05-29-tolerate_markdown_verdict_lines`). Then run
    `grep -n '\*\*Status:\*\*' .specs/plans/*/plan.md` and confirm the benchmark plan still reads
    `Status: Done` and the eval-judge plan still reads `Status: Draft` (mapping table rows in
    `.specs/plans/2026-06-06-kanban_plan_folder_layout/09-migrate_existing_flat_plans.md:14,17`).
  - *Status:* ☐ unverified

- **O2 — Every task file is filed into the subfolder its real Status maps to, with the per-task Status field removed; each task is in exactly one subfolder.**
  - *Claim:* each `NN-*.md` task file sits in exactly one of `done/`/`in-progress/`/`backlog/`
    matching its old `Status:` (`Done`→`done/`, `In progress`→`in-progress/`, anything else
    including `Todo`/`Proposed`/`Draft`/absent→`backlog/`), and no moved task file retains a
    per-task `**Status:**` header.
  - *Evidence to collect:* `ls -R` the four plans with task files and confirm filings match the
    mapping table at
    `.specs/plans/2026-06-06-kanban_plan_folder_layout/09-migrate_existing_flat_plans.md:14-18`:
    benchmark 01, 02, 04–23 (no 03) in `done/`; close_group_a 01–05 in `done/`; add_live_container 01–03 in `done/`;
    eval_judge 01–08 in `backlog/`; add_lighter_precanned 01–02 in `backlog/`. Then run
    `grep -rn '^\*\*Status:\*\*\|· \*\*Status:\*\*' .specs/plans/*/done/ .specs/plans/*/in-progress/ .specs/plans/*/backlog/`
    over the migrated task files — expect zero hits (per-task status now encoded by folder).
  - *Checks:* spot-read one off-nominal task header (an `add_lighter_precanned` task,
    old `Status: Proposed`) before/after to confirm a non-standard status routed to `backlog/`, not
    dropped or mis-routed; confirm no task lands in `in-progress/` (no plan had an in-progress task).
  - *Status:* ☐ unverified

- **O3 — The benchmark plan's certificates/ subfolder is gone, its 22 certificates relocated to co-located done/NN-*-certificate.md; no certificates/ subfolder remains in any of the seven.**
  - *Claim:* `2026-05-27-spec_workflow_benchmark/certificates/` no longer exists; its 22 certificate
    files are now `done/NN-*-certificate.md` co-located beside their task files; no
    `certificates/` subfolder remains anywhere under the seven plans.
  - *Evidence to collect:* run `ls -d .specs/plans/2026-05-27-spec_workflow_benchmark/certificates`
    — expect "No such file or directory". Run
    `ls .specs/plans/2026-05-27-spec_workflow_benchmark/done/*-certificate.md | wc -l` — expect 22.
    Run `find .specs/plans -type d -name certificates` over all seven flat plans — expect zero
    output. Spot-check one task (e.g. `01`) and confirm both `done/01-*.md` and
    `done/01-*-certificate.md` are present and co-located.
  - *Status:* ☐ unverified

- **O4 — The two task-file-less plans carry the marker and no subfolders.**
  - *Claim:* `2026-05-28-raise_recursive_arm_timeout_budget` and
    `2026-05-29-tolerate_markdown_verdict_lines` each have `**Layout:** kanban` in plan.md and no
    `done/`/`in-progress/`/`backlog/`/`certificates/` subfolders.
  - *Evidence to collect:* `ls -R .specs/plans/2026-05-28-raise_recursive_arm_timeout_budget
    .specs/plans/2026-05-29-tolerate_markdown_verdict_lines` — expect each to contain plan.md (and
    its inline task content) and no status subfolders. Confirm O1's grep already listed both plan.md
    files as carrying the marker.
  - *Status:* ☐ unverified

- **O5 — `scripts/check.sh` passes (these are `.specs/` files, not synced; the gate is green).**
  - *Claim:* the repo gate is green after migration; because `.specs/plans/**` lies outside the
    synced `skills/` tree and outside Python, the move does not change any synced or linted artefact.
  - *Evidence to collect:* run `scripts/check.sh` from the repo root — expect exit 0. Run
    `scripts/sync-skills.sh --check` — expect it reports the synced tree matches `plugins/` (no drift
    from this task, which touches only `.specs/plans/**`).
  - *Status:* ☐ unverified

- **O6 — Meets the repo definition of done.**
  - *Claim:* the change uses `jj`-aware moves so the working copy stays consistent, commits follow
    Conventional Commits, and `scripts/check.sh` is green (plan.md baseline).
  - *Evidence to collect:* run `scripts/check.sh` and `scripts/sync-skills.sh --check` — expect both
    clean (gate stays green for un-synced `.specs/plans/**`). Inspect the working-copy/VCS status
    (`jj status` or `git status`) — expect the task-file relocations show as renames/moves (tracked),
    not delete+add of untracked content, and no stray files left behind. Confirm the commit
    message(s) follow Conventional Commits per `plan.md` baseline.
  - *Status:* ☐ unverified

- **O7 — Reviewable: `ls -R` shows the kanban board; a grep for a per-task `**Status:**` header across `.specs/plans/**` returns nothing; `scripts/check.sh` is green. (Reviewable)**
  - *Claim:* a reviewer can list each migrated plan and see the kanban board (task files filed by
    status, co-located `NN-*-certificate.md`, no `certificates/` subfolder), confirm no per-task
    `**Status:**` header survives anywhere under `.specs/plans/**`, and see the gate green.
  - *Evidence to collect:* run `ls -R .specs/plans/2026-05-27-spec_workflow_benchmark` and
    `ls -R .specs/plans/2026-05-28-close_group_a_spec_code_gaps` — expect the board shape (status
    subfolders holding task files; `done/` also holding `NN-*-certificate.md` for the benchmark; no
    `certificates/`). Run
    `grep -rn '^\*\*Status:\*\*\|· \*\*Status:\*\*' .specs/plans/2026-05-2* .specs/plans/2026-05-30*`
    across the seven migrated flat plans — expect zero hits (plan-level Status lines may appear in
    plan.md and are a different axis; confirm any hit is a plan.md plan-level line, not a per-task
    header). Run `scripts/check.sh` — expect exit 0.
  - *Status:* ☐ unverified

## Regression check

For each consumer the migration touches, the validator traces it:

- The builder (task 04) reads each migrated plan as a board: trace one migrated plan
  (`2026-05-27-spec_workflow_benchmark`) and confirm the union of its `backlog/` + `in-progress/` +
  `done/` subfolders enumerates every task (`01`, `02`, `04`–`23`; no `03`) exactly once — none dropped, none duplicated by
  the move : ☐ (PRESERVED / REGRESSION)
- The contract task 01 defines (`.specs/plans/2026-06-06-kanban_plan_folder_layout/01-planner_authoring_contract.md`):
  confirm the migrated layout (status subfolders, co-located `NN-*-certificate.md`, `**Layout:**
  kanban` marker) matches what task 01 specifies, so the seven plans conform to the same contract the
  planner now emits : ☐ (PRESERVED / REGRESSION)

## Residue

Notes for the validator: the new plan folder authored here
(`2026-06-06-kanban_plan_folder_layout`) is explicitly out of scope — the task edits only
`.specs/plans/**` legacy folders; the build migrates the new folder by the same rule when it runs
(task file lines 8). `blocked/` is never created by this task (only a parked build creates it). Empty
subfolders are intentionally absent (git/jj do not track them). These are not obligations — the DoD
is the contract.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐ <one sentence deriving the verdict from the statuses>
