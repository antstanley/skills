# Done Certificate — Task 05: Builder transitions + isolation

**Task:** [05-builder_transitions_and_isolation.md](05-builder_transitions_and_isolation.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-06-06 — unverified   <!-- validator sets: Validated YYYY-MM-DD -->

> This certificate is a verification protocol for Task 05. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 05) ≡ every obligation O1…O7 below holds, each backed by the evidence the obligation
names (a file location, a grep, or a command result) — not by assertion.

## Premises

- **P1 — Goal.** The task produces `build-loop.md`, `subagent-brief.md`, `workspaces.md`, and
  `portability.md` rewritten so a status transition is a single serialized main-tree file move
  (task + its `-certificate.md`) into `in-progress/`, `done/`, or `blocked/`; the spec-link depth
  gains one `../`; and sub-agents never touch the plan folder.
- **P2 — Obligations.** Done iff O1…O7 all hold. One Oi per definition-of-done item, in DoD
  order; O7 is the `Reviewable:` item.
- **P3 — Invariants.** Must not break: `semi-formal-review` and the vendored
  `semiformal-method.md` ↔ `method.md` ↔ `reasoning-semiformally` reasoning-method triangle (must
  stay byte-identical); the `skills/` regenerated tree (must match `plugins/` after sync); the
  link-depth invariant shared with `plan-template.md` (01) and `checklist.md` (02).

## Obligations

- **O1 — `build-loop.md` steps 1, 3, 4 and parking are folder moves of task + certificate; certificate read from main; Invariants reflect folder-as-status.**
  - *Claim:* in `plugins/spec-builder/skills/spec-builder/references/build-loop.md`, step 1 moves
    `backlog/NN-*.md` and its `NN-*-certificate.md` into `in-progress/` on the main tree; step 3
    reads the certificate from the task's current subfolder on the main tree (never a sub-agent
    workspace copy); step 4 moves the task file and its `-certificate.md` from `in-progress/` into
    `done/` as the commit point after merge, then recomputes `plan.md`'s `Status` from the
    subfolders; parking moves the task into `blocked/` and adds a `**Blocked:** <reason>` header
    line (no longer "stays In progress with a note"), leaving the workspace intact; Invariants
    restate "Done" as "task file in `done/` after merge", state folder membership is authoritative
    on resume, and state a task is in exactly one of the four subfolders.
  - *Evidence to collect:* read `build-loop.md` around step 1 (was L22), step 3 certificate path
    (was L50), step 4 mark-done (was L63–73), parking (was L91), and Invariants (was L104–114).
    Confirm each named transition is described as a file move of both the task file and its
    `-certificate.md`. Run `grep -n 'Status: Done\|Status: In progress\|stays In progress\|certificates/'`
    over `build-loop.md` — expect zero hits (no per-task `Status:`-field write, no
    `certificates/`-subfolder path, no "stays In progress" parking residue). Run
    `grep -n 'backlog/\|in-progress/\|blocked/\|done/\|\*\*Blocked:\*\*' build-loop.md` — expect the
    move targets and the `**Blocked:**` header line present.
  - *Checks:* confirm the certificate read in step 3 resolves to the task's *current* subfolder on
    the main tree (e.g. `in-progress/NN-*-certificate.md`), not a workspace path and not a
    `certificates/NN-*.md` path — flag if it points into a sub-agent workspace.
  - *Status:* ☐ unverified

- **O2 — `subagent-brief.md` spec-link depth gains one `../` and reads identically to `plan-template.md`/`checklist.md`; certificate path is the current-subfolder sibling on main.**
  - *Claim:* in `plugins/spec-builder/skills/spec-builder/references/subagent-brief.md`, the
    spec-link depth/resolution rule (was L37–40) gains one `../` — global page `../../../foo.md`,
    per-package `../../../<package>/specs/…` — matching `plan-template.md`/`checklist.md` verbatim;
    and the certificate path (was L29) is the task's current-subfolder sibling read from main.
  - *Evidence to collect:* read `subagent-brief.md` around the spec-link rule (was L37–40) and the
    certificate path (was L29). Run `grep -n '\.\./\.\./\.\./' subagent-brief.md` — expect the
    `../../../` depth present and no remaining `../../` (one-level-shallower) global/per-package
    link.
  - *Checks:* diff the `../../../` depth rule and the global/per-package wording in
    `subagent-brief.md` against the same rule in
    `plugins/spec-planner/skills/spec-planner/references/plan-template.md` (01) and
    `plugins/spec-planner/skills/spec-planner/references/checklist.md` (02); confirm identical
    (the link-depth invariant). Flag any divergence in depth or in the
    global-vs-per-package phrasing.
  - *Status:* ☐ unverified

- **O3 — `workspaces.md` asserts plan-folder moves are main-tree-only by the orchestrator; `portability.md` sequential fallback performs the same moves.**
  - *Claim:* `plugins/spec-builder/skills/spec-builder/references/workspaces.md` carries a newly
    added statement (near the Core principle / lifecycle, was ~L15–16) that plan-folder file moves
    (`backlog/`→`in-progress/`→`blocked/`/`done/`) are a main-tree-only operation by the
    orchestrator — task workspaces hold code, never the plan folder, and never move task files;
    and `portability.md`'s sequential fallback (was L78) "update the plan board" becomes the same
    folder moves (task + certificate into `done/`, or `blocked/` on park) performed on the main
    tree.
  - *Evidence to collect:* read `workspaces.md` near the Core principle (was ~L15–16) for the new
    main-tree-only assertion; read `portability.md` around the sequential fallback (was L78).
    Run `grep -n 'main tree\|main-tree\|backlog/\|in-progress/\|blocked/\|done/' workspaces.md` —
    expect the main-tree-only move assertion present. Run
    `grep -n 'update the plan board\|done/\|blocked/' portability.md` — expect the fallback now
    describes the folder moves, not a `Status:`-field write.
  - *Status:* ☐ unverified

- **O4 — `semi-formal-review` and the reasoning-method triangle are untouched.**
  - *Claim:* `plugins/spec-builder/skills/semi-formal-review/**` and the vendored
    `semiformal-method.md` ↔ `method.md` ↔ `reasoning-semiformally` triangle are byte-for-byte
    unchanged by this task.
  - *Evidence to collect:* run
    `git diff --name-only HEAD -- plugins/spec-builder/skills/semi-formal-review plugins/spec-builder/skills/spec-builder/references/semiformal-method.md plugins/reasoning-semiformally`
    (and any `method.md` under the triangle) — expect zero files listed. If a base ref is
    available, `git diff --stat` over those paths — expect empty.
  - *Status:* ☐ unverified

- **O5 — `scripts/sync-skills.sh` re-run and `scripts/check.sh` passes (no `skills/` drift).**
  - *Claim:* the regenerated `skills/spec-builder/**` copy matches the edited `plugins/spec-builder/**`
    source; `scripts/check.sh` is green with no drift.
  - *Evidence to collect:* run `scripts/sync-skills.sh --check` — expect it reports the flat
    `skills/` tree matches `plugins/` (no drift). Then run `scripts/check.sh` — expect exit 0.
    If `--check` reports drift, the sync was not re-run after editing the four reference files.
  - *Status:* ☐ unverified

- **O6 — Meets the repo definition of done.**
  - *Claim:* Conventional Commits subject; `scripts/check.sh` green (the operative per-task gate
    per plan.md baseline); the kanban wording is internally coherent with no residual flat-layout
    residue.
  - *Evidence to collect:* run `scripts/sync-skills.sh --check` and `scripts/check.sh` — expect
    both clean (the Python ruff/pyright/pytest items stay green and untouched; this task touches
    only markdown). Run
    `grep -rn 'certificates/\|Status: Done\|Status: In progress\|stays In progress' plugins/spec-builder/skills/spec-builder/references/build-loop.md plugins/spec-builder/skills/spec-builder/references/subagent-brief.md plugins/spec-builder/skills/spec-builder/references/workspaces.md plugins/spec-builder/skills/spec-builder/references/portability.md`
    — expect zero hits (no flat-layout `certificates/` path, no per-task `Status:`-field write, no
    "stays In progress" parking residue). Confirm the commit subject follows Conventional Commits.
  - *Checks:* the "no residual flat wording" grep above must resolve to zero hits across the four
    owned files.
  - *Status:* ☐ unverified

- **O7 — Reviewable: a reader traces one task dispatch→merge→park and sees a single main-tree move of task + certificate at each step, depth matching task 01/02, and no in-workspace plan-folder mutation; `scripts/check.sh` green (Reviewable).**
  - *Claim:* a reviewer reading `build-loop.md`, `subagent-brief.md`, `workspaces.md`, and
    `portability.md` can trace one task from dispatch to merge to (alternatively) park and observe,
    at each step, one serialized main-tree file move of the task file together with its
    `-certificate.md`; the spec-link depth rule matches task 01 (`plan-template.md`) and task 02
    (`checklist.md`); no step mutates the plan folder inside a sub-agent workspace; and
    `scripts/check.sh` is green.
  - *Evidence to collect:* read `build-loop.md` end-to-end and follow one task: dispatch (move into
    `in-progress/`) → both gates pass + merge (move into `done/`) → park alternative (move into
    `blocked/` with a `**Blocked:**` line). Confirm each transition names a move of the task file
    and its `-certificate.md` on the main tree and that none mutates a workspace copy of the plan
    folder. Diff the `subagent-brief.md` depth rule against `plan-template.md` and `checklist.md`
    (per O2 check) — confirm identical. Run `scripts/check.sh` — expect exit 0.
  - *Status:* ☐ unverified

## Regression check

For each module the task touched, the validator traces one downstream consumer:

- The regenerated `skills/spec-builder/skills/spec-builder/references/{build-loop,subagent-brief,workspaces,portability}.md`
  copies consume the edited `plugins/` source via `scripts/sync-skills.sh`. Trace: run
  `scripts/sync-skills.sh --check` → expect the flat `skills/` tree matches `plugins/`
  (no drift) : ☐ (PRESERVED / REGRESSION)
- Task 01's `plan-template.md` and task 02's `checklist.md` are the conformers to the shared
  link-depth invariant. Trace: diff the `../../../` depth rule + global/per-package wording in
  `subagent-brief.md` against both → expect identical depth and phrasing : ☐ (PRESERVED / REGRESSION)
- The spec-builder orchestrator (task 04) enumerates the task set as the union of the four
  subfolders. Trace: the transitions O1 defines move each task into exactly one of
  `in-progress/`/`blocked/`/`done/` (out of `backlog/`) → expect the union still enumerates every
  task once with no task left in two folders : ☐ (PRESERVED / REGRESSION)

## Residue

Notes for the validator: this task edits only spec-builder reference files (un-`.specs/`-tracked
in the synced tree but inside the drift-checked `plugins/`→`skills/` surface), so the operative
gate is `scripts/sync-skills.sh --check` + `scripts/check.sh`; the Python suite is out of scope
(no executable code changes). The lazy-folder-creation rule (no `.gitkeep`) and the migration of
this plan's own folder are owned by tasks 04 and 09 respectively, not by this task's DoD. These
are not obligations — the DoD is the contract.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐ <one sentence deriving the verdict from the statuses>
