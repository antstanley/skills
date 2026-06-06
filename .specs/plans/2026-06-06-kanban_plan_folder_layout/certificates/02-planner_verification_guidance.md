# Done Certificate — Task 02: Planner verification + decomposition guidance

**Task:** [02-planner_verification_guidance.md](../02-planner_verification_guidance.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-06-06 — unverified

> This certificate is a verification protocol for Task 02. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 02) ≡ every obligation O1…O6 below holds, each backed by the evidence the obligation
names (a file location, a grep result, or a command result) — not by assertion.

## Premises

- **P1 — Goal.** The task produces `checklist.md` and `task-decomposition.md` conformed to the
  kanban contract — the pre-handoff checklist verifies four subfolders, number-keyed references,
  the `../../../` depth, and co-located `NN-task-certificate.md` files, and the decomposition
  guidance reconciles "one numbered file per task" with files that move between subfolders while
  keeping `NN` as identity.
- **P2 — Obligations.** Done iff O1…O6 all hold. One Oi per definition-of-done item, in DoD order;
  O6 is the `Reviewable:` item.
- **P3 — Invariants.** Must not break the regression surface this task touches: the synced
  flat copy of these two references under `plugins/spec-planner/skills/spec-planner/references/`
  (sync drift), and the cross-file contract with task 01's `plan-template.md` (the shared
  `../../../` depth rule and the journal-app worked example) that conformer tasks 02/03/04/07
  all match.

## Obligations

- **O1 — `checklist.md` verifies the four-subfolder structure, number-keyed references, the `../../../` depth, and co-located `NN-task-certificate.md` files, with no per-task `Status`/`certificates/`-subfolder checks remaining.**
  - *Claim:* the Folder-and-document-structure, Graph-coherence, Cross-links, and Done-certificates
    sections of `checklist.md` describe `plan.md`-at-root + four subfolders, reference tasks by
    number (found by glob across subfolders), use the `../../../` spec-page depth and the
    `[../plan.md](../plan.md)` back-link, and locate certificates as co-located
    `NN-snake_case_task-certificate.md`; no per-task `Status` check and no `certificates/` subfolder
    reference survive.
  - *Evidence to collect:* read
    `plugins/spec-planner/skills/spec-planner/references/checklist.md` Folder/document structure
    (around L10, L11, L15), Graph coherence (around L23–25), Cross-links (around L63), Done
    certificates (around L72, L74); confirm each reads as the kanban shape above. Then run
    `grep -n 'certificates/\|Status:\|per task\|NN-…md file per task' plugins/spec-planner/skills/spec-planner/references/checklist.md`
    — expect zero hits proving flat-layout residue (no `certificates/` subfolder path, no per-task
    `Status` check). Confirm the four subfolder names `backlog/`/`in-progress/`/`blocked/`/`done/`
    and the co-located `NN-…-certificate.md` form are present.
  - *Status:* ☐ unverified

- **O2 — `task-decomposition.md` reconciles `NN`-as-identity with folder moves and updates the build-order rationale; no flat-layout wording remains.**
  - *Claim:* the output-framing line (L5) and the `NN`-assignment paragraph (L20) state the file
    moves between `backlog/`/`in-progress/`/`blocked/`/`done/` while `NN` is its immutable identity
    everywhere (table, graph, cross-refs, certificate name); the build-order note (L125) says files
    sort by `NN` within each subfolder and the folder indicates current status, not build sequence.
  - *Evidence to collect:* read
    `plugins/spec-planner/skills/spec-planner/references/task-decomposition.md` at L5, L20, and L125;
    confirm the `NN`-as-identity-plus-folder-move framing and the revised build-order rationale.
    Then run
    `grep -n 'sort in build order\|one numbered file per task\|certificates/\|file per task' plugins/spec-planner/skills/spec-planner/references/task-decomposition.md`
    — expect zero hits for the old flat-layout wording (no "the files sort in build order" rationale,
    no `certificates/` reference).
  - *Status:* ☐ unverified

- **O3 — The `../../../` depth rule reads identically to `plan-template.md` (task 01), and the worked example matches it identically (the two cross-file invariants).**
  - *Claim:* the Cross-links spec-page depth rule (`../../../foo.md` global /
    `../../../<package>/specs/NN-name.md` per-package) and the worked example (L93–110 of
    `task-decomposition.md`) are byte-identical to their counterparts in task 01's `plan-template.md`.
  - *Evidence to collect:* read the Cross-links depth rule in
    `plugins/spec-planner/skills/spec-planner/references/checklist.md` (around L63) and the
    corresponding depth rule in
    `plugins/spec-planner/skills/spec-planner/references/plan-template.md`; read the worked example
    in `task-decomposition.md` (L93–110) and the canonical journal-app worked example in
    `plan-template.md`.
  - *Checks:* diff the `../../../` depth rule wording in `checklist.md`/`task-decomposition.md`
    against the same rule in `plan-template.md` (task 01); confirm identical. Diff the
    `task-decomposition.md` worked example against the journal-app worked example in
    `plan-template.md`; confirm identical. Any divergence (different depth count, different example
    task names/paths) fails this obligation.
  - *Status:* ☐ unverified

- **O4 — `scripts/sync-skills.sh` was re-run and `scripts/check.sh` passes (no `skills/` drift).**
  - *Claim:* the synced flat copy of the two edited references matches the `plugins/` source, and
    the check gate is green.
  - *Evidence to collect:* run `scripts/sync-skills.sh --check` — expect it reports the synced tree
    matches `plugins/` (no drift) for `checklist.md` and `task-decomposition.md`. Run
    `scripts/check.sh` — expect exit 0. Both edited files are inside the synced tree, so a stale
    `skills/` copy would surface here.
  - *Status:* ☐ unverified

- **O5 — Meets the repo definition of done (Conventional Commits, `scripts/check.sh` green — see plan.md baseline).**
  - *Claim:* the change satisfies the repo's definition of done: Conventional Commit message and a
    green `scripts/check.sh`.
  - *Evidence to collect:* run `scripts/check.sh` — expect exit 0. Inspect the task's commit
    subject; expect a Conventional Commit prefix (e.g. `docs(spec-planner):` or `refactor(...)`).
    Confirm `scripts/sync-skills.sh --check` is clean per O4.
  - *Status:* ☐ unverified

- **O6 — Reviewable: a reader runs the checklist mentally against a kanban plan and every check resolves to the four-subfolder layout; `diff` of the depth rule and worked example against task 01 shows no divergence; `scripts/check.sh` is green. (Reviewable).**
  - *Claim:* a reviewer reading `checklist.md` against a kanban plan finds every check resolving to
    the four-subfolder layout (number-keyed references, `../../../` depth, co-located certificates);
    a `diff` of the depth rule and worked example against task 01 shows no divergence; and
    `scripts/check.sh` is green.
  - *Evidence to collect:* read
    `plugins/spec-planner/skills/spec-planner/references/checklist.md` end to end and confirm every
    structural check names the four subfolders / number-keyed reference / `../../../` depth /
    co-located certificate, with no flat-layout check remaining (cross-check the O1 grep returned
    zero hits). Re-run the O3 diffs of the depth rule and worked example against
    `plan-template.md` and confirm no divergence. Run `scripts/check.sh` — expect exit 0.
  - *Status:* ☐ unverified

## Regression check

For each touched reference, the validator traces one downstream consumer:

- `checklist.md` / `task-decomposition.md` are synced to
  `plugins/spec-planner/skills/spec-planner/references/` (the flat synced tree consumed at runtime).
  Trace `scripts/sync-skills.sh --check`: expect the synced flat copies match the `plugins/`
  source after the edit : ☐ (PRESERVED / REGRESSION)
- Task 01's `plan-template.md` is the contract these references conform to, and conformer tasks
  02/03/04/07 must all match the same `../../../` depth and journal-app worked example. Trace the
  depth-rule and worked-example diff against `plan-template.md`: expect this task's wording stays in
  lock-step with task 01 (no drift that would split the conformers) : ☐ (PRESERVED / REGRESSION)

## Residue

Notes for the validator: the migration of existing flat plans is task 09's obligation, not this
task's; if a kanban-shaped sample plan does not yet exist to "mentally run" the O6 checklist
against, reason against the layout `plan-template.md` defines. The number-keyed-glob mechanism the
checklist describes is exercised concretely by the builder (task 04); that wiring is out of scope
here. These are not obligations — the DoD is the contract.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐ <one sentence deriving the verdict from the statuses>
