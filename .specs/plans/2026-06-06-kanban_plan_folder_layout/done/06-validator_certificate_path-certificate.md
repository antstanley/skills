# Done Certificate — Task 06: Validator certificate path

**Task:** [06-validator_certificate_path.md](06-validator_certificate_path.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-06-06 — unverified

> This certificate is a verification protocol for Task 06. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 06) ≡ every obligation O1…O6 below holds, each backed by the evidence the obligation
names (a file location, a grep result, or a command result) — not by assertion.

## Premises

- **P1 — Goal.** The `validate-done-certificate` skill reads the certificate (and its task) as
  the co-located `NN-snake_case_task-certificate.md` sitting in the task's current kanban
  subfolder on the orchestrator's main tree — not from a `certificates/` path and not from a
  sub-agent's stale workspace copy.
- **P2 — Obligations.** Done iff O1…O6 all hold. One Oi per definition-of-done item, in DoD
  order; O6 is the `Reviewable:` item.
- **P3 — Invariants.** Must not break: the `State:`-field handling and the verdict-write location
  in the validation flow; the untouched `semi-formal-review` skill and the reasoning-method
  triangle; the drift gate (`skills/` must remain a faithful copy of `plugins/`).

## Obligations

- **O1 — `validation-protocol.md` and `SKILL.md` name a co-located certificate in the task's current subfolder on the main tree; no `certificates/` path remains; no workspace-local assumption.**
  - *Claim:* both files describe the certificate path as `.specs/plans/<plan>/<current-subfolder>/NN-<task>-certificate.md` (where `<current-subfolder>` is whichever of `backlog/`/`in-progress/`/`blocked/`/`done/` holds the task), read from the orchestrator's main tree; the task file is the same-subfolder sibling `<current-subfolder>/NN-<task>.md`; the no-certificate fallback reflects co-location.
  - *Evidence to collect:* read `plugins/spec-builder/skills/validate-done-certificate/references/validation-protocol.md` Inputs certificate path (was L19), task-file path (was L21), and no-certificate fallback (was L92); read `plugins/spec-builder/skills/validate-done-certificate/SKILL.md` main-tree-view statement (was L41–43) and open-the-certificate step (was L69). Confirm each names the current-subfolder co-located `NN-<task>-certificate.md` on the main tree.
  - *Checks:* run `grep -n 'certificates/' plugins/spec-builder/skills/validate-done-certificate/SKILL.md plugins/spec-builder/skills/validate-done-certificate/references/validation-protocol.md` — expect zero hits (no residual `certificates/`-subfolder path). Run `grep -ni 'workspace' plugins/spec-builder/skills/validate-done-certificate/references/validation-protocol.md` over the certificate-path lines — confirm the read is anchored to the orchestrator's main tree, not a sub-agent workspace copy.
  - *Status:* ☐ unverified

- **O2 — The certificate naming/co-location matches task 03; `State:` handling and verdict-write location unchanged.**
  - *Claim:* the certificate name carries the `-certificate.md` suffix and co-locates beside the task in the same subfolder, identical to task 03's done-certificates contract; the `State:` field handling and the verdict-write location are unchanged from before this task.
  - *Evidence to collect:* read task 03's Produces line and §Where the certificate lives in `plugins/spec-planner/skills/done-certificates/SKILL.md` (anchors in `03-certificate_colocation.md` Pointers: SKILL.md L87–92); confirm task 06's naming (`NN-<task>-certificate.md`, co-located, moves with the task) matches. In `validation-protocol.md` and `SKILL.md`, locate the `State:`-field handling and the verdict-write step; confirm they are unchanged versus the prior version (`git diff` / `jj diff` the two files and confirm the diff touches only the certificate-path / task-path / fallback lines, not the `State:` or verdict-write lines).
  - *Checks:* diff the certificate-naming string (`-certificate.md` suffix + co-location wording) in `validate-done-certificate` against task 03's contract in `done-certificates/SKILL.md`; confirm identical naming and co-location rule.
  - *Status:* ☐ unverified

- **O3 — `semi-formal-review` and the reasoning-method triangle are untouched.**
  - *Claim:* this task changed no file under `semi-formal-review` and no reasoning-method-triangle content.
  - *Evidence to collect:* run `jj diff --name-only` (or `git diff --name-only`) for this task's change; confirm no path under `plugins/spec-builder/skills/semi-formal-review/` and no reasoning-method-triangle file appears in the changed set.
  - *Status:* ☐ unverified

- **O4 — `scripts/sync-skills.sh` was re-run and `scripts/check.sh` passes (no `skills/` drift).**
  - *Claim:* the regenerated `skills/validate-done-certificate/` copy matches the edited `plugins/spec-builder/skills/validate-done-certificate/` source; the drift gate is green.
  - *Evidence to collect:* run `scripts/sync-skills.sh --check` — expect clean (no drift reported). If it reports drift, the sync was not re-run after editing the plugin files. Then run `scripts/check.sh` — expect exit 0.
  - *Checks:* `grep -rn 'certificates/' skills/validate-done-certificate/` — expect zero hits, confirming the regenerated copy carries the same kanban path as the edited plugin source (no stale flat path in the synced tree).
  - *Status:* ☐ unverified

- **O5 — Meets the repo definition of done (Conventional Commits, `scripts/check.sh` green — see plan.md baseline).**
  - *Claim:* the change satisfies the plan's DoD baseline: `scripts/check.sh` green, internal coherence with no residual flat-layout/`certificates/`-subfolder wording, Conventional Commits subject.
  - *Evidence to collect:* run `scripts/check.sh` — expect exit 0 (its live assertion here is `scripts/sync-skills.sh --check`; the Python suite stays green and untouched as this change touches no Python). Confirm the commit subject for this task follows Conventional Commits. Run `grep -ni 'certificates/\|Status:' plugins/spec-builder/skills/validate-done-certificate/SKILL.md plugins/spec-builder/skills/validate-done-certificate/references/validation-protocol.md` — expect zero flat-layout residue (no `certificates/` path, no per-task `Status:`-field assumption); a `State:` certificate-field match is not flat-layout residue.
  - *Status:* ☐ unverified

- **O6 — Reviewable: a reader follows the validator locating a certificate for a task in, say, `in-progress/`, and confirms it reads `in-progress/NN-<task>-certificate.md` from the main tree; `scripts/check.sh` is green. (Reviewable)**
  - *Claim:* a reviewer reading `validation-protocol.md` Inputs and the `SKILL.md` open-the-certificate step, for a task that currently sits in `in-progress/`, can trace the validator to read `.specs/plans/<plan>/in-progress/NN-<task>-certificate.md` from the orchestrator's main tree; the gate is green.
  - *Evidence to collect:* read the certificate-path Input in `validation-protocol.md` and the open-the-certificate step in `SKILL.md`; substitute `in-progress/` for `<current-subfolder>` and confirm the resolved path is `in-progress/NN-<task>-certificate.md` on the main tree (not `certificates/`, not a workspace copy). Run `scripts/check.sh` — expect exit 0.
  - *Status:* ☐ unverified

## Regression check

For each module the task touched, the validator traces one downstream consumer:

- The regenerated `skills/validate-done-certificate/` copy is the drift consumer of the edited
  `plugins/spec-builder/skills/validate-done-certificate/` source. Trace: `scripts/sync-skills.sh --check`
  compares the flat `skills/` tree against `plugins/` → expect the regenerated copy matches the
  edited source (the kanban certificate path present in both) : ☐ (PRESERVED / REGRESSION)
- Cross-task conformance: task 03 (done-certificates) authors the certificate as a co-located
  `NN-<task>-certificate.md`; this task's validator-side read must consume that exact name and
  co-location. Trace: the certificate-naming + co-location rule in `validate-done-certificate`
  against task 03's contract → expect identical naming so the validator finds what the author wrote
  : ☐ (PRESERVED / REGRESSION)

## Residue

Notes for the validator: this task edits only `validate-done-certificate` files, which sit inside
the synced tree, so `scripts/check.sh` exercises the drift gate directly (no `evals.json` /
`plugin.json` / README / `.specs/plans` JSON-lint or `ls -R` step applies here). The migration of
existing flat plans and the eval golden outputs are out of scope (tasks 07 and 09). These are not
obligations — the DoD is the contract.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐ <one sentence deriving the verdict from the statuses>
