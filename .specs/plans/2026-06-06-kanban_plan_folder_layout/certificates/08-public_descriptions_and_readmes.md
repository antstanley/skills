# Done Certificate — Task 08: Public descriptions + READMEs

**Task:** [08-public_descriptions_and_readmes.md](../08-public_descriptions_and_readmes.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-06-06 — unverified   <!-- validator sets: Validated YYYY-MM-DD -->

> This certificate is a verification protocol for Task 08. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 08) ≡ every obligation O1…O6 below holds, each backed by the evidence the obligation
names (a file location, a grep result, or a command result) — not by assertion.

## Premises

- **P1 — Goal.** The task produces both `.claude-plugin/plugin.json` descriptions and both plugin
  `README.md` files reworded from the flat "live board / `Status` / optional `certificates/`
  subfolder" framing to folder-as-status with co-located certificates — a surface
  `scripts/sync-skills.sh` does not regenerate and `scripts/check.sh` does not gate, so it must be
  hand-edited or it goes silently stale.
- **P2 — Obligations.** The task is done iff O1…O6 all hold. One Oi per definition-of-done item,
  in DoD order; O6 is the `Reviewable:` item.
- **P3 — Invariants.** Must not break: the layout contract authored in task 01
  (`plan-template.md` / planner `SKILL.md`) that this prose must agree with — the four status
  folders (`backlog/`/`in-progress/`/`blocked/`/`done/`), no per-task `Status:` field, certificates
  co-located as `NN-task-certificate.md`; and the `scripts/check.sh` green baseline (the four edited
  files sit outside the synced `skills/<name>/` tree and outside Python, so the gate must stay green
  regardless).

## Obligations

- **O1 — `spec-builder`'s `plugin.json` description and `README.md` describe folder-as-status with co-located certificates.**
  - *Claim:* `spec-builder`'s `plugin.json` description and `README.md` describe the orchestrator
    moving task files between `backlog/`/`in-progress/`/`blocked/`/`done/` with certificates
    co-located per task as `NN-task-certificate.md` — no "live board", no "optional `certificates/`
    subfolder", no per-task `Status`-field framing.
  - *Evidence to collect:* read `plugins/spec-builder/.claude-plugin/plugin.json` L4 (description),
    `plugins/spec-builder/README.md` L5 (intro/pipeline) and L29 (optimised-for); confirm each now
    states folder-as-status (the four named subfolders, folder location = status) and co-located
    `NN-task-certificate.md`. Then run
    `grep -n 'live board\|optional `certificates/`\|certificates/ subfolder\|\*\*Status:\*\*\|per-task `Status`' plugins/spec-builder/.claude-plugin/plugin.json plugins/spec-builder/README.md`
    — expect zero hits.
  - *Checks:* diff the four-folder names and the `NN-task-certificate.md` certificate-naming against
    task 01's `plan-template.md` (folder tree L5–12, co-located certificate naming); confirm the
    README/description use the same folder set and same certificate filename shape, not a divergent
    wording.
  - *Status:* ☐ unverified

- **O2 — `spec-planner`'s `plugin.json` + `README.md` are verified against the new layout, updated where stale, left untouched where neutral, with a clean grep across all four files.**
  - *Claim:* `spec-planner`'s `plugin.json` (L4) and `README.md` are reworded wherever flat-layout /
    `Status`-field / `certificates/`-subfolder framing appears and left unchanged where already
    neutral; a grep for the flat-layout phrases over all four task-08 files returns nothing stale.
  - *Evidence to collect:* read `plugins/spec-planner/.claude-plugin/plugin.json` L4 and
    `plugins/spec-planner/README.md` (recon flagged these largely neutral — note L32, L34 reference
    the certificate-template skill path, which is layout-neutral and should stay). Then run
    `grep -n 'certificates/\|live board\|\*\*Status:\*\*\|NN-task\b' plugins/spec-builder/.claude-plugin/plugin.json plugins/spec-builder/README.md plugins/spec-planner/.claude-plugin/plugin.json plugins/spec-planner/README.md`
    — expect zero hits describing the *plan-folder* layout in flat terms (hits that are unrelated
    skill/file paths, e.g. `skills/done-certificates/...`, are not stale and do not count).
  - *Checks:* for any spec-planner hit, resolve whether it describes the plan-folder layout (must be
    fixed) or an unrelated skill artefact path (must be left). Confirm no neutral prose was reworded
    needlessly.
  - *Status:* ☐ unverified

- **O3 — The four files are consistent with the layout in task 01 and the build loop in tasks 04/05.**
  - *Claim:* the folder-as-status description, the four subfolder names, and the co-located
    certificate naming in all four files match the contract in task 01 and the build-loop /
    status-transition prose produced by tasks 04 and 05.
  - *Evidence to collect:* read `.specs/plans/2026-06-06-kanban_plan_folder_layout/01-planner_authoring_contract.md`
    (Produces line: four-folder tree, co-located certificates) and the produced
    `plugins/spec-builder/skills/spec-builder/SKILL.md` board-view / transitions prose (tasks 04/05);
    compare the four task-08 files against them.
  - *Checks:* diff the subfolder set (`backlog/`/`in-progress/`/`blocked/`/`done/`) and the
    `NN-task-certificate.md` naming in the spec-builder README/description against task 01's
    `plan-template.md` and the task-04/05 SKILL.md board prose; confirm identical naming and that the
    README's status-flip wording is folder moves, not `Status`-field flips.
  - *Status:* ☐ unverified

- **O4 — `scripts/check.sh` passes (un-synced, un-drift-checked files; the gate is green regardless).**
  - *Claim:* `scripts/check.sh` is green; the four edited files are outside the synced `skills/<name>/`
    tree and outside Python, so they do not affect the gate.
  - *Evidence to collect:* run `scripts/check.sh` — expect green. Note that the four edited files
    (`plugins/*/README.md`, `plugins/*/.claude-plugin/plugin.json`) are outside the synced tree, so
    `scripts/sync-skills.sh --check` does not regenerate or drift-check them — `check.sh` stays green
    because the edits are confined to un-synced surface.
  - *Status:* ☐ unverified

- **O5 — Meets the repo definition of done.**
  - *Claim:* Conventional Commits subject, `scripts/check.sh` green (hand-edited surface, per plan.md
    baseline); the commit notes these four files are not covered by `sync-skills.sh` / `check.sh` and
    were edited by hand.
  - *Evidence to collect:* run `scripts/check.sh` — expect green. Inspect the task's commit
    subject — expect a Conventional Commits prefix. Confirm the commit body notes the four files are
    hand-edited and outside `skills/<name>/` (so `sync-skills.sh` was not run expecting them to
    propagate). Because these files are un-synced, `scripts/sync-skills.sh --check` is not the gate
    for them; `check.sh` is, and stays green.
  - *Status:* ☐ unverified

- **O6 — Reviewable: a reader finds the kanban layout described consistently; grep for "live board" / "`certificates/`" returns nothing stale; `scripts/check.sh` is green (Reviewable).**
  - *Claim:* a reviewer reads both READMEs and both plugin descriptions and finds the kanban layout
    described consistently with the skills; a grep for "live board" / "`certificates/`" returns
    nothing stale; `scripts/check.sh` is green.
  - *Evidence to collect:* read `plugins/spec-builder/README.md`,
    `plugins/spec-builder/.claude-plugin/plugin.json`, `plugins/spec-planner/README.md`,
    `plugins/spec-planner/.claude-plugin/plugin.json` end to end — observe a self-consistent
    folder-as-status description matching the skills. Run
    `grep -rn 'live board\|certificates/ subfolder\|optional `certificates/`' plugins/spec-builder plugins/spec-planner`
    — expect zero plan-layout hits. Run `scripts/check.sh` — expect green.
  - *Status:* ☐ unverified

## Regression check

The four edited files are outside the synced `skills/<name>/` tree, so there is no regenerated
`skills/` copy to drift-check; the downstream consumer is a human reader and the layout contract,
not code.

- The layout contract in task 01 (`plan-template.md` four-folder tree + `NN-task-certificate.md`
  naming) is the upstream that this public prose must restate: trace the spec-builder README/
  description folder set and certificate naming back to task 01's `plan-template.md` → expect
  identical subfolder names and certificate filename shape (no divergent wording) :
  ☐ (PRESERVED / REGRESSION)
- `scripts/sync-skills.sh --check`: confirm it reports no drift attributable to this task — i.e. the
  task touched only un-synced files (`plugins/*/README.md`, `plugins/*/.claude-plugin/plugin.json`)
  and no `skills/<name>/` source, so the synced flat tree still matches `plugins/` :
  ☐ (PRESERVED / REGRESSION)

## Residue

Notes for the validator: O2's "left untouched where already neutral" is a judgement call — a hit in
the spec-planner files that points at a skill artefact path (e.g. `skills/done-certificates/...`) is
layout-neutral and must NOT be reworded; only plan-folder-layout descriptions are in scope. The DoD
does not require touching files beyond the four named. These are not obligations — the DoD is the
contract.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐ <one sentence deriving the verdict from the statuses>
