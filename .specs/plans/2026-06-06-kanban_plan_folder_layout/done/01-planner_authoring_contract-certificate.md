# Done Certificate — Task 01: Planner authoring contract

**Task:** [01-planner_authoring_contract.md](01-planner_authoring_contract.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-06-06 — unverified   <!-- validator sets: Validated YYYY-MM-DD -->

> This certificate is a verification protocol for Task 01. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 01) ≡ every obligation O1…O5 below holds, each backed by the evidence the obligation
names (a file location, a grep result, or a command result) — not by assertion.

## Premises

- **P1 — Goal.** The task produces the canonical kanban layout fully specified in the planner
  `SKILL.md` and `plan-template.md` — the four-folder tree (`plan.md` at root +
  `backlog/`/`in-progress/`/`blocked/`/`done/`), no per-task `**Status:**` field, a dependency
  table keyed by task number (no path link), `../../../` spec-link depth authored once, a
  `**Layout:** kanban` header field, and certificates co-located beside their tasks — so a
  planner author can author a kanban plan.
- **P2 — Obligations.** Done iff O1…O5 all hold. One Oi per definition-of-done item, in DoD
  order; O5 is the `Reviewable:` item.
- **P3 — Invariants.** Must not break: the regenerated `skills/spec-planner/` copy (sync drift —
  it is a `cp -R` of `plugins/spec-planner/`, drift-gated by `scripts/check.sh`); the two
  cross-file invariants in `plan.md` that downstream conformers (02/03/04/07) match against
  (link depth `../../../`, the journal-app worked example); and the Python suite, which this
  task does not touch and must stay green.

## Obligations

- **O1 — Both files describe the kanban board with no residual flat-layout wording.**
  - *Claim:* `plan-template.md` and `SKILL.md` describe the four-folder board, drop the per-task
    `Status:` field, key the dependency table by number, carry the `**Layout:** kanban` header,
    use `../../../` spec-link depth, and co-locate certificates — with no residual
    flat-layout / `certificates/`-subfolder / `Status:`-field wording in either file.
  - *Evidence to collect:* read `plugins/spec-planner/skills/spec-planner/references/plan-template.md`
    at the folder tree (was L5–12), Status lifecycle (was L20–37), `plan.md` header (was L46),
    dependency table (was L81–91), task-file skeleton (was L130–159), Notes (was L170); confirm
    each section now states the kanban shape per the Steps. Read
    `plugins/spec-planner/skills/spec-planner/SKILL.md` frontmatter description (was L3), Phase 4
    (was L73–83), Phase 4.5 (was L87–89), Phase 5 step 2 (was L96), §Adding done certificates
    (was L113–121); confirm each now names the four task subfolders, the `**Plan:**` back-link
    with no `Status:` field, and certificates authored into `backlog/`. Confirm the task-file
    skeleton's back-link is `[plan.md](../plan.md)` and carries
    `**Certificate:** [NN-…-certificate.md](NN-…-certificate.md)`.
  - *Checks:* run `grep -n 'certificates/\|Status:' plugins/spec-planner/skills/spec-planner/references/plan-template.md plugins/spec-planner/skills/spec-planner/SKILL.md`
    — expect zero hits that denote the old flat layout (a `certificates/` subfolder path or a
    per-task `**Status:**` field). The retained `plan.md`-level `Status` table
    (Draft → Accepted → In progress → Done) is permitted; confirm any surviving `Status` match
    is that plan-level table, not a per-task field.
  - *Status:* ☐ unverified

- **O2 — Folder tree, worked-example names, and `../../../` depth are stated so tasks 02/03/07 match verbatim.**
  - *Claim:* the four-folder tree, the worked-example task/certificate names, and the `../../../`
    depth in `plan-template.md` are stated so tasks 02 (checklist/decomposition), 03
    (certificate-template), and 07 (planner eval) can match them verbatim (the two cross-file
    invariants in `plan.md`).
  - *Evidence to collect:* read the folder tree, the `../../../` spec-link depth rule, and the
    journal-app worked example (`01-passphrase_lock …`) in `plan-template.md`; confirm all three
    are present and unambiguous (a global page resolves as `../../../foo.md`, a per-package page
    as `../../../<package>/specs/NN-name.md`).
  - *Checks:* diff the `../../../` depth rule and the journal-app worked example in
    `plan-template.md` against the same in `plan.md` Cross-file invariants (lines 17–18); confirm
    identical. (Tasks 02/03/07 conform later against this same statement — at this task's
    authoring those files are not yet converted, so the resolution check is against the contract
    source, not the conformers.)
  - *Status:* ☐ unverified

- **O3 — Re-synced and `scripts/check.sh` passes (no `skills/` drift).**
  - *Claim:* `scripts/sync-skills.sh` was re-run and `scripts/check.sh` passes — no `skills/`
    drift, Python suite unaffected and green.
  - *Evidence to collect:* run `scripts/sync-skills.sh --check` from the repo root — expect it to
    report the flat `skills/` tree matches `plugins/` (no drift). Then run `scripts/check.sh` —
    expect exit 0. Because this task edits a synced plugin tree (`SKILL.md` + reference file), a
    drift here means `sync-skills.sh` was not re-run after the edits.
  - *Status:* ☐ unverified

- **O4 — Meets the repo definition of done.**
  - *Claim:* Conventional Commits subject, `jj` front end, `scripts/check.sh` green per the
    `plan.md` baseline; no Python touched.
  - *Evidence to collect:* run `scripts/check.sh` — expect exit 0 (its live assertion here is
    `scripts/sync-skills.sh --check`). Confirm the commit subject is a Conventional Commits line.
    Confirm no file under a Python path was modified (so ruff/pyright/pytest are satisfied by
    staying untouched and green).
  - *Status:* ☐ unverified

- **O5 — Reviewable: a reader finds a self-consistent kanban-authoring description and check.sh is green (Reviewable).**
  - *Claim:* a reader opens the edited `SKILL.md` + `plan-template.md` and finds a self-consistent
    description of authoring a kanban plan — four subfolders, number-keyed table, `../../../`
    links, `Layout: kanban`, co-located certificates — and `scripts/check.sh` is green.
  - *Evidence to collect:* open
    `plugins/spec-planner/skills/spec-planner/SKILL.md` and
    `plugins/spec-planner/skills/spec-planner/references/plan-template.md`; read end to end and
    confirm a reader can author a kanban plan from them with no contradiction between the two
    files (the SKILL phases and the template skeleton agree on the four subfolders, the
    number-keyed dependency table, the `../../../` link depth, the `**Layout:** kanban` header,
    and certificates authored into `backlog/` beside their tasks). Run `scripts/check.sh` —
    expect exit 0.
  - *Status:* ☐ unverified

## Regression check

For each surface the task touched, the validator traces one downstream consumer:

- `scripts/sync-skills.sh --check`: the regenerated `skills/spec-planner/` copy must match the
  edited `plugins/spec-planner/` source after re-sync. Trace: run the check → expect the flat
  tree matches `plugins/` (no drift introduced by the `SKILL.md` + `plan-template.md` edits) :
  ☐ (PRESERVED / REGRESSION)
- Conformer tasks 02/03/04/07: each must match task 01's `../../../` depth rule and journal-app
  worked example. Trace: at this task's authoring they are not yet converted, so confirm the
  contract this task states is the single source they will diff against (link depth + worked
  example as fixed in `plan.md` lines 17–18) — no conflicting second statement of either exists
  in the two edited files : ☐ (PRESERVED / REGRESSION)
- Python suite: this task touches no Python. Trace: `scripts/check.sh` runs the suite as part of
  the gate → expect green and unchanged : ☐ (PRESERVED / REGRESSION)

## Residue

Notes for the validator: tasks 02–09 are the conformers and migration that build *against* this
contract; their conformance is validated by their own certificates, not here. This certificate
covers only the two files this task owns (`SKILL.md` + `plan-template.md`) and the sync gate over
them. The actual verbatim match by 02/03/07 cannot be checked at this task's authoring because
those files are not yet converted — that match is each conformer's obligation. None other noted
at authoring.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐ <one sentence deriving the verdict from the statuses>
