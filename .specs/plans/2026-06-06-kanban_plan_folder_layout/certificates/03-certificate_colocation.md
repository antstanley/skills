# Done Certificate — Task 03: Certificate co-location

**Task:** [03-certificate_colocation.md](../03-certificate_colocation.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-06-06 — unverified

> This certificate is a verification protocol for Task 03. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 03) ≡ every obligation O1…O6 below holds, each backed by the evidence the obligation
names (a file location, a grep, or a command result) — not by assertion.

## Premises

- **P1 — Goal.** The done-certificates skill authors a certificate **beside** its task as
  `NN-snake_case_task-certificate.md` (no `certificates/` subfolder), into `backlog/` alongside the
  still-unbuilt task, with same-directory `[NN-…md](NN-…md)` + `[plan.md](../plan.md)` cross-links
  that survive every move, a next-free-`NN` spanning the four subfolders, and an ownership boundary
  where done-certificates authors content and spec-builder owns moving the file with its task.
- **P2 — Obligations.** The task is done iff O1…O6 all hold. One Oi per definition-of-done item, in
  DoD order; O6 is the `Reviewable:` item.
- **P3 — Invariants.** Must not break: the regenerated `skills/spec-planner/skills/done-certificates/`
  copy stays in sync with `plugins/` (drift gate); the shared journal-app worked example stays
  identical to task 01's canonical copy; the certificate-naming and link-depth contract defined by
  task 01 stays the single source the template conforms to.

## Obligations

- **O1 — `SKILL.md` §Where the certificate lives describes co-located `NN-snake_case_task-certificate.md`.**
  - *Claim:* §Where the certificate lives (was L87–92) describes a co-located
    `NN-snake_case_task-certificate.md` with same-directory + `../plan.md` links, authored into
    `backlog/`, and no `certificates/` subfolder anywhere in the file.
  - *Evidence to collect:* read `plugins/spec-planner/skills/done-certificates/SKILL.md`
    §Where the certificate lives; confirm the naming `NN-snake_case_task-certificate.md`, the
    `backlog/` authoring location, the same-directory task link and `../plan.md` plan link. Then run
    `grep -n 'certificates/' plugins/spec-planner/skills/done-certificates/SKILL.md` — expect zero
    hits (no flat-layout `certificates/` subfolder residue).
  - *Checks:* `grep -n 'certificates/' over the file resolves to zero hits.
  - *Status:* ☐ unverified

- **O2 — Ownership boundary and four-subfolder next-free-`NN`.**
  - *Claim:* the ownership boundary reads: done-certificates authors into `backlog/` and owns content;
    spec-builder owns moving certificates with their tasks. The next-free-`NN` scan spans the four
    subfolders, not a single `certificates/` folder.
  - *Evidence to collect:* read `plugins/spec-planner/skills/done-certificates/SKILL.md`
    §When invoked / ownership (was L94–96) and the next-free-`NN` logic (was L92); confirm the
    author-vs-mover split and confirm the scan enumerates the union of
    `backlog/`, `in-progress/`, `blocked/`, `done/`. Run
    `grep -n 'owns the .certificates/. subfolder\|certificates/ subfolder'
    plugins/spec-planner/skills/done-certificates/SKILL.md` — expect zero hits.
  - *Checks:* `grep` for the removed "done-certificates owns the `certificates/` subfolder" wording
    resolves to zero hits.
  - *Status:* ☐ unverified

- **O3 — `certificate-template.md` header links are same-directory + `../plan.md`; worked example matches task 01 identically.**
  - *Claim:* the skeleton header link (was L40) and the worked-example header link (was L121) are
    same-directory to the task (`[NN-…md](NN-snake_case_task.md)`,
    `[01-passphrase_lock.md](01-passphrase_lock.md)`) plus `· **Plan:** [plan.md](../plan.md)`; the
    worked example matches task 01's journal-app example **identically** (the shared-worked-example
    invariant), and the certificate-naming matches task 01's planner contract.
  - *Evidence to collect:* read
    `plugins/spec-planner/skills/done-certificates/references/certificate-template.md` skeleton header
    and worked-example header; confirm both task links are same-directory and both plan links are
    `../plan.md`. Run
    `grep -n '\.\./NN-snake_case_task\|\.\./01-passphrase_lock'
    plugins/spec-planner/skills/done-certificates/references/certificate-template.md` — expect zero
    hits (no `../` task-link residue).
  - *Checks:* diff the worked-example block (the journal-app passphrase-lock certificate and its DoD)
    against the canonical copy in task 01's `plan-template.md`; confirm identical. Diff the
    certificate-naming (`NN-snake_case_task-certificate.md`) and the `../plan.md` / same-directory
    link-depth rule against task 01's planner contract; confirm they match.
  - *Status:* ☐ unverified

- **O4 — Sync re-run; `scripts/check.sh` passes (no `skills/` drift).**
  - *Claim:* `scripts/sync-skills.sh` was re-run and `scripts/check.sh` passes; the regenerated
    `skills/` tree carries the same edits as `plugins/`.
  - *Evidence to collect:* run `scripts/sync-skills.sh --check` — expect it reports the flat
    `skills/` tree matches `plugins/` (no drift). Then run `scripts/check.sh` — expect exit 0.
  - *Checks:* `scripts/sync-skills.sh --check` exits clean (both edited files —
    `SKILL.md` and `references/certificate-template.md` — are inside the synced tree, so a missing
    re-sync surfaces here as drift).
  - *Status:* ☐ unverified

- **O5 — Meets the repo definition of done.**
  - *Claim:* Conventional Commits subject; `scripts/check.sh` green; no Python touched (Python items
    satisfied by staying untouched and green).
  - *Evidence to collect:* run `scripts/check.sh` — expect exit 0 (its live assertion here is
    `scripts/sync-skills.sh --check`). Confirm the commit subject is Conventional Commits form.
    Confirm the diff touches only `plugins/spec-planner/skills/done-certificates/SKILL.md` and
    `references/certificate-template.md` plus their regenerated `skills/` copies — no Python.
  - *Status:* ☐ unverified

- **O6 — Reviewable: a certificate's links stay valid from authoring through a move (Reviewable).**
  - *Claim:* a reader traces a certificate from authoring (`backlog/NN-…-certificate.md`) through a
    move and confirms its `[NN-…md](NN-…md)` task link and `[plan.md](../plan.md)` plan link stay
    valid in every subfolder; `scripts/check.sh` is green.
  - *Evidence to collect:* read the §Where the certificate lives prose and follow the link recipe: an
    authored certificate `backlog/03-foo-certificate.md` links to `03-foo.md` (same dir) and
    `../plan.md`; reason about the same certificate after a move to `in-progress/`, `blocked/`, and
    `done/` — since both the certificate and its task move together as one unit, the same-directory
    task link and the `../plan.md` plan link resolve unchanged in each subfolder. Run
    `scripts/check.sh` — expect exit 0.
  - *Checks:* confirm the prose states certificate and task move together as one unit (so the
    same-directory link never breaks) and that the plan link is one level up (`../plan.md`) from any
    task subfolder.
  - *Status:* ☐ unverified

## Regression check

For each surface the task touched, the validator traces one downstream consumer:

- The regenerated copy `skills/spec-planner/skills/done-certificates/` (SKILL.md +
  references/certificate-template.md) must match `plugins/` after the edit. Trace:
  `scripts/sync-skills.sh --check` over the synced tree → expect the flat tree matches `plugins/`
  (no drift) : ☐ (PRESERVED / REGRESSION)
- Task 01 (`plan-template.md`) is the contract this template conforms to; tasks 02
  (`task-decomposition.md`) and 07 (the four eval fixtures) reproduce the same journal-app worked
  example. Trace: the worked example edited here is byte-identical to task 01's canonical copy so no
  conformer reintroduces the flat layout → expect identical : ☐ (PRESERVED / REGRESSION)

## Residue

Notes for the validator: tasks 01, 02, and 07 also carry the shared worked example; this task only
asserts the `certificate-template.md` slice — full cross-file identity is the reviewer's whole-plan
check, not an obligation of Task 03. The eval golden outputs (07) are updated after every skill
conversion, so a temporary mismatch against 07 before 07 lands is expected and not a regression here.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐ <one sentence deriving the verdict from the statuses>
