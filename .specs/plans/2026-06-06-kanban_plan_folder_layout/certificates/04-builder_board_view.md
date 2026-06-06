# Done Certificate — Task 04: Builder board view

**Task:** [04-builder_board_view.md](../04-builder_board_view.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-06-06 — unverified

> This certificate is a verification protocol for Task 04. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 04) ≡ every obligation O1…O6 below holds, each backed by the evidence the obligation
names (a file location, a grep/command result, or an execution trace) — not by assertion.

## Premises

- **P1 — Goal.** The task produces `spec-builder`'s `SKILL.md` + `orchestration.md` rewritten so the
  builder enumerates the full task set as the union of `backlog/`/`in-progress/`/`blocked/`/`done/`
  (missing folder = empty), builds the DAG from `plan.md`'s number-keyed dependency table, derives
  ready/running/parked/done from folder membership, recomputes `plan.md`'s plan-level `Status` from the
  subfolders after each transition, and detects kanban via the `**Layout:** kanban` marker (or a
  `backlog/` subfolder) while migrating a legacy-flat plan in place.
- **P2 — Obligations.** The task is done iff O1…O6 all hold. One Oi per definition-of-done item, in
  DoD order; O6 is the `Reviewable:` item.
- **P3 — Invariants.** Must not break: (a) the `semi-formal-review` skill and the reasoning-method
  triangle, which this task explicitly does not edit; (b) the contract fixed by task 01 (the four-folder
  board, the `**Layout:** kanban` marker, number-only references, the one-level-deeper link depth,
  certificate co-location) — task 04 conforms to it, it does not redefine it; (c) the synced `skills/`
  tree, which is a regenerated copy of `plugins/` and must not drift.

## Obligations

- **O1 — Both files describe union enumeration, folder-derived scheduling, `Status` recompute, and legacy-flat migrate-in-place.**
  - *Claim:* `SKILL.md` and `orchestration.md` describe enumerating the union of the four subfolders,
    deriving ready/running/blocked/done from folder membership, recomputing `plan.md`'s `Status` from the
    subfolders, and detecting + migrating a legacy-flat plan in place.
  - *Evidence to collect:* read `plugins/spec-builder/skills/spec-builder/SKILL.md` at the rewritten
    sites — rule 3 (L35–37), the "optimised for" line (L57–60), Phase 1 read (L115–120), Phase 4
    status-write (L148–151); and `plugins/spec-builder/skills/spec-builder/references/orchestration.md` —
    "Reading the plan" (L36–50), the wave-scheduler sets (L54–85), §Status bookkeeping (L140–161).
    Confirm each of the four behaviours appears: (1) the task set is the *union* of `backlog/`/
    `in-progress/`/`blocked/`/`done/` with missing = empty; (2) `ready` = `backlog/` whose `Depends-on` ⊆
    `done/`, `running` = `in-progress/`, parked = `blocked/`, `done` = `done/`; (3) `plan.md` `Status` is
    recomputed from the subfolders after each transition; (4) a legacy-flat plan (no marker, no `backlog/`,
    task files at root) is detected and migrated in place (create subfolders, move each task by its
    `Status:` value, relocate `certificates/NN-*.md` to a co-located `NN-*-certificate.md`, drop the
    per-task `Status` field, stamp `**Layout:** kanban`).
  - *Checks:* diff the four-folder enumeration and the `**Layout:** kanban` / `backlog/` detection rule
    against task 01's contract file (the planner authoring contract named in plan.md M1); confirm the
    bucket names and marker spelling are identical, not a reworded variant.
  - *Status:* ☐ unverified

- **O2 — Every `certificates/` mention and per-task `Status:`-field flip is converted; the union names all four buckets including `blocked/`.**
  - *Claim:* no flat-layout residue remains in the two files — every `certificates/` reference and every
    per-task `Status:`-field flip is converted, and the union enumeration names all four buckets including
    `blocked/`.
  - *Evidence to collect:* run
    `grep -n 'certificates/\|Status:' plugins/spec-builder/skills/spec-builder/SKILL.md plugins/spec-builder/skills/spec-builder/references/orchestration.md`.
    Expect: zero hits describing a `certificates/` *subfolder* of the plan or a per-task `Status:` *field*
    on a task file (certificate `State` and the build-log `Status` are legitimately retained — see the
    task's final step; confirm any surviving `Status:` hit is one of those, not a per-task field).
    Note: L47 and L59 of `SKILL.md` carry `certificates/` mentions beyond the change-spec anchors — confirm
    both are converted. Then grep both files for `blocked/`; expect the union enumeration to name
    `backlog/`, `in-progress/`, `blocked/`, and `done/` together.
  - *Checks:* the "no residual flat wording" check resolves to zero hits — the grep above must return no
    line describing a plan-level `certificates/` subfolder or a per-task `Status:` field.
  - *Status:* ☐ unverified

- **O3 — `semi-formal-review` and the reasoning-method triangle are untouched.**
  - *Claim:* the task changed neither the `semi-formal-review` skill nor the reasoning-method triangle.
  - *Evidence to collect:* run `git diff --name-only` (or `jj diff --name-only`) for the task's change and
    confirm the touched paths are limited to
    `plugins/spec-builder/skills/spec-builder/SKILL.md`,
    `plugins/spec-builder/skills/spec-builder/references/orchestration.md`, and their regenerated
    `skills/` copies. Confirm no path under a `semi-formal-review` skill directory and no
    reasoning-method-triangle file appears in the diff.
  - *Status:* ☐ unverified

- **O4 — `scripts/sync-skills.sh` was re-run and `scripts/check.sh` passes (no `skills/` drift).**
  - *Claim:* the regenerated `skills/` copy matches the edited `plugins/` source; the drift gate is green.
  - *Evidence to collect:* run `scripts/sync-skills.sh --check`; expect it to report the synced `skills/`
    tree matches `plugins/` (no drift). Then run `scripts/check.sh`; expect exit 0. Because this task edits
    two *synced* plugin files, `sync-skills.sh` must have been re-run before the gate or `check.sh` fails on
    `skills/` drift.
  - *Checks:* confirm the `skills/` copy of both edited files contains the same converted wording as
    `plugins/` — `diff plugins/spec-builder/skills/spec-builder/SKILL.md skills/spec-builder/skills/spec-builder/SKILL.md`
    (and the `orchestration.md` pair) resolve to no difference.
  - *Status:* ☐ unverified

- **O5 — Meets the repo definition of done.**
  - *Claim:* Conventional Commits subject; `scripts/check.sh` green (plan.md baseline); Python suite stays
    green and untouched (this is a markdown-only change).
  - *Evidence to collect:* per plan.md's §Source and definition-of-done baseline, run `scripts/check.sh`
    and expect exit 0 (its live assertion here is `scripts/sync-skills.sh --check`). Confirm the commit
    subject follows Conventional Commits. The Python items (ruff/pyright/pytest) are satisfied by staying
    green and untouched — confirm the diff touches no Python.
  - *Status:* ☐ unverified

- **O6 — Reviewable: a reader follows the builder reading both a kanban plan and a legacy-flat plan and sees one coherent enumerate → schedule → recompute path with no flat-layout residue; `scripts/check.sh` is green (Reviewable).**
  - *Claim:* a reviewer can read `SKILL.md` + `orchestration.md` end to end and trace, for a kanban plan
    *and* for a legacy-flat plan, a single coherent enumeration → schedule → recompute path with no
    flat-layout residue, and `scripts/check.sh` is green.
  - *Evidence to collect:* read `SKILL.md` Phase 1 (L115–120) and `orchestration.md` "Reading the plan"
    (L36–50) and trace two readings: (1) kanban plan — detect via `**Layout:** kanban` / `backlog/`,
    enumerate the union, schedule from `backlog/`⊆`done/`, recompute `plan.md` `Status`; (2) legacy-flat
    plan — no marker, no `backlog/`, task files at root → detect, migrate in place, then the same
    enumerate → schedule → recompute path. Confirm both readings land on one path with no flat-layout
    wording. Run `scripts/check.sh`; expect exit 0.
  - *Status:* ☐ unverified

## Regression check

For each surface the task touched, the validator traces one downstream consumer:

- The regenerated `skills/spec-builder/skills/spec-builder/SKILL.md` and `.../orchestration.md` copies are
  the `cp -R` output of the edited `plugins/` files. Trace `scripts/sync-skills.sh --check` over the synced
  tree → expect the flat `skills/` tree matches `plugins/` (no drift) : ☐ (PRESERVED / REGRESSION)
- Task 01 is the contract this task conforms to (plan.md M1). Trace the four-folder enumeration, the
  `**Layout:** kanban` marker, and certificate co-location in the edited files against task 01's contract →
  expect identical bucket names, marker spelling, and migration semantics : ☐ (PRESERVED / REGRESSION)

## Residue

Notes for the validator: the legitimate retained `Status:` occurrences (certificate `State`, build-log
`Status`) are called out in the task's final step and are *not* per-task task-file fields — the O2 grep
must not flag them as residue. The downstream conformers that build on this view (task 05 transition/
isolation mechanics, task 09 migration) are out of this task's file ownership and are not obligations
here. (Or: none further noted at authoring.)

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐ <one sentence deriving the verdict from the statuses>
