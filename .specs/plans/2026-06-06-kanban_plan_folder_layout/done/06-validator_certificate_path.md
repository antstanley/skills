# Task 06 — Validator certificate path

**Plan:** [plan.md](../plan.md) · **Certificate:** [06-validator_certificate_path-certificate.md](06-validator_certificate_path-certificate.md)

**Implements:** [2026-06-05-kanban_plan_folder_layout.md](../../../changes/2026-06-05-kanban_plan_folder_layout.md) §C (certificate read from the task's current subfolder, not `certificates/`) — the validate-done-certificate side
**Depends on:** 03
**Produces:** the validate-done-certificate skill reads the certificate (and its task) as the co-located `NN-snake_case_task-certificate.md` sitting in the task's **current** kanban subfolder on the orchestrator's main tree — not from a `certificates/` path and not from a sub-agent's stale workspace copy
**Pointers:** `plugins/spec-builder/skills/validate-done-certificate/SKILL.md` — main-tree-view statement (L41–43), open-the-certificate step (L69); `plugins/spec-builder/skills/validate-done-certificate/references/validation-protocol.md` — Inputs certificate path (L19), Inputs task-file path (L21), no-certificate fallback (L92)

## Steps

- [ ] In `validation-protocol.md` Inputs (L19): change the certificate path from `.specs/plans/<plan>/certificates/NN-<task>.md` to `.specs/plans/<plan>/<current-subfolder>/NN-<task>-certificate.md`, where `<current-subfolder>` is whichever of `backlog/`/`in-progress/`/`blocked/`/`done/` holds the task; state it is read from the orchestrator's main tree.
- [ ] Update the task-file Input (L21) so the task file is the certificate's same-subfolder sibling (`<current-subfolder>/NN-<task>.md`).
- [ ] Update the no-certificate fallback (L92) only as needed to reflect co-location (the certificate, when present, sits beside the task); keep the `State:` field handling and the verdict-write location unchanged.
- [ ] In `SKILL.md` (L41–43 / L69): make explicit that the validator locates the certificate by the task's current subfolder on the main tree (not a `certificates/` path, not a workspace copy); the certificate name carries the `-certificate.md` suffix; `State:` handling is unchanged.
- [ ] Confirm the certificate naming and co-location match task 03's done-certificates contract.
- [ ] Do **not** edit `semi-formal-review` or the reasoning-method triangle.
- [ ] Run `scripts/sync-skills.sh` and confirm `scripts/check.sh` passes.

## Definition of done

- [ ] `validation-protocol.md` and `SKILL.md` name the certificate as a co-located `NN-<task>-certificate.md` in the task's current subfolder on the main tree; no `certificates/` path remains, and no assumption of a workspace-local certificate.
- [ ] The certificate naming/co-location matches task 03; the `State:` field handling and verdict-write location are unchanged.
- [ ] `semi-formal-review` and the reasoning-method triangle are untouched.
- [ ] `scripts/sync-skills.sh` was re-run and `scripts/check.sh` passes (no `skills/` drift).
- [ ] Meets the repo definition of done (Conventional Commits, `scripts/check.sh` green — see plan.md baseline).
- [ ] Reviewable: a reader follows the validator locating a certificate for a task in, say, `in-progress/`, and confirms it reads `in-progress/NN-<task>-certificate.md` from the main tree; `scripts/check.sh` is green.
