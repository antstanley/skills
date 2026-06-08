# Done Certificate — Task 07: Eval fixtures assert kanban

**Task:** [07-eval_fixtures_kanban.md](07-eval_fixtures_kanban.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-06-06 — unverified   <!-- validator sets: Validated YYYY-MM-DD -->

> This certificate is a verification protocol for Task 07. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 07) ≡ every obligation O1…O6 below holds, each backed by the evidence the obligation
names (a file location, a grep result, or a command result) — not by assertion.

## Premises

- **P1 — Goal.** The task produces all four `evals.json` golden `expected_output`s rewritten to
  assert the kanban layout — the four-folder board (`backlog/`/`in-progress/`/`blocked/`/`done/`),
  co-located `NN-task-certificate.md` files (no `certificates/` subfolder), task references by
  number, folder-move transitions (not `Status:`-field flips), `**Layout:** kanban`, the
  four-bucket enumeration, and `../../../` spec-link depth — with the shared journal-app worked
  example updated identically across them.
- **P2 — Obligations.** Done iff O1…O6 all hold. One Oi per definition-of-done item, in DoD
  order; O6 is the `Reviewable:` item.
- **P3 — Invariants.** Must not break: the two cross-file invariants in `plan.md` (lines 17–18 —
  the `../../../` link depth and the `01-passphrase_lock …` journal-app worked example) that this
  task's golden outputs must match against tasks 01/02/03; the eval-case skeleton of each fixture
  (`id`/`name`/`prompt`/`files` — only `expected_output`/description prose may change); and
  `scripts/check.sh` (the `evals/` files are stripped from the synced `skills/` tree, so this
  edit produces no `skills/` drift, and the Python suite, untouched, must stay green).

## Obligations

- **O1 — All four golden outputs assert the kanban layout with no flat-layout residue.**
  - *Claim:* all four golden `expected_output`s assert the four-folder board, co-located
    `NN-task-certificate.md` certificates, number-keyed references, folder-move transitions,
    `**Layout:** kanban`, the four-bucket enumeration (incl. `blocked/`), and `../../../` depth —
    with no flat-layout / `certificates/`-subfolder / `Status:`-flip assertions remaining.
  - *Evidence to collect:* read the golden outputs in
    `plugins/spec-planner/skills/spec-planner/evals/evals.json` (the L8 "one `NN-…md` file per
    task" + `(../../)` depth case and the L15 flat task-file list),
    `plugins/spec-planner/skills/done-certificates/evals/evals.json` (the L7 worked-example case
    and the L8 `certificates/` path + `../NN-…md` depth case),
    `plugins/spec-builder/skills/spec-builder/evals/evals.json` (the L7 `certificates/` subfolder
    + worked-example case and the L8/L15/L22 `Status:`-flip transition cases), and
    `plugins/spec-builder/skills/validate-done-certificate/evals/evals.json` (the L7
    `certificates/NN-…md` path cases); confirm each now states the kanban shape per the Steps —
    the four subfolders, co-located `NN-task-certificate.md`, number-keyed references, folder-move
    transitions (`backlog/`→`in-progress/`→`done/`, park → `blocked/`), the `**Layout:** kanban`
    header, the four-bucket enumeration, and `../../../` depth.
  - *Checks:* run `grep -n 'certificates/\|Status:\|(\.\./\.\.)' plugins/spec-planner/skills/spec-planner/evals/evals.json plugins/spec-planner/skills/done-certificates/evals/evals.json plugins/spec-builder/skills/spec-builder/evals/evals.json plugins/spec-builder/skills/validate-done-certificate/evals/evals.json`
    — expect zero hits that denote the old flat layout (a `certificates/` subfolder path, a
    per-task `Status:`-field flip, or a `(../../)` two-level spec-link depth). Any surviving
    `Status` match must be the permitted `plan.md`-level `Status` table (Draft → Accepted →
    In progress → Done), not a per-task field flip; confirm by reading each hit in context.
  - *Status:* ☐ unverified

- **O2 — The shared worked example is identical across the four fixtures and matches tasks 01/02/03.**
  - *Claim:* the `01-passphrase_lock …` journal-app worked example is identical across the four
    `evals.json` fixtures and matches the same example as fixed in tasks 01/02/03 (the
    shared-worked-example invariant).
  - *Evidence to collect:* extract the `01-passphrase_lock …` worked-example text from the golden
    outputs of all four fixtures (the spec-planner, done-certificates, spec-builder, and
    validate-done-certificate `evals.json`); confirm the four occurrences are byte-identical to
    each other (same task/certificate names, same folder placement, same `../../../` depth).
  - *Checks:* diff the four extracted worked-example blocks against the journal-app worked example
    as fixed in `plan.md` Cross-file invariants (line 18) and the source statements in
    `plugins/spec-planner/skills/spec-planner/references/plan-template.md` (task 01),
    `plugins/spec-planner/skills/spec-planner/references/task-decomposition.md` (task 02), and
    `plugins/spec-planner/skills/done-certificates/references/certificate-template.md` (task 03);
    confirm all identical — no stale copy reintroduces the flat layout (no `certificates/`
    subfolder, no per-task `Status:` field, `../../../` depth throughout).
  - *Status:* ☐ unverified

- **O3 — Each `evals.json` is valid JSON with its case skeleton intact.**
  - *Claim:* each `evals.json` is valid JSON and its `id`/`name`/`prompt`/`files` structure is
    intact — only the golden `expected_output` / description prose changed.
  - *Evidence to collect:* run `python -m json.tool` on each of the four files
    (`plugins/spec-planner/skills/spec-planner/evals/evals.json`,
    `plugins/spec-planner/skills/done-certificates/evals/evals.json`,
    `plugins/spec-builder/skills/spec-builder/evals/evals.json`,
    `plugins/spec-builder/skills/validate-done-certificate/evals/evals.json`) — expect each to
    parse with exit 0 (well-formed JSON). Then diff each file against its pre-edit revision (e.g.
    `jj diff` / `git diff` over the four paths) and confirm every changed line lies inside an
    `expected_output` or a description field — the `id`, `name`, `prompt`, and `files` keys and
    their values are unchanged, and the case count per file is preserved (3 / 3 / 4 / 2).
  - *Status:* ☐ unverified

- **O4 — `scripts/check.sh` passes (no drift, Python green).**
  - *Claim:* `scripts/check.sh` passes — no `skills/` drift (the `evals/` files are not synced)
    and the Python suite is green.
  - *Evidence to collect:* run `scripts/sync-skills.sh --check` from the repo root — expect it to
    report the flat `skills/` tree matches `plugins/` (no drift; `evals/` is stripped from the
    synced tree, so editing the four `evals.json` introduces none). Then run `scripts/check.sh` —
    expect exit 0 (its live assertion here is `scripts/sync-skills.sh --check`, plus the
    untouched Python suite staying green).
  - *Status:* ☐ unverified

- **O5 — Meets the repo definition of done.**
  - *Claim:* Conventional Commits subject, `jj` front end, `scripts/check.sh` green per the
    `plan.md` baseline; these fixtures are hand-edited, not synced, so no Python is touched.
  - *Evidence to collect:* run `scripts/check.sh` — expect exit 0. Confirm the commit subject is a
    Conventional Commits line. Confirm no file under a Python path was modified (the four edited
    files are all `evals/evals.json` data, outside the synced tree and outside Python — so
    ruff/pyright/pytest are satisfied by staying untouched and green, and the gate stays green
    despite these files sitting outside the drift-checked `skills/` tree).
  - *Status:* ☐ unverified

- **O6 — Reviewable: each golden output reads as kanban, a JSON-lint passes, and check.sh is green (Reviewable).**
  - *Claim:* a reviewer diffs each golden output and sees it now describes the kanban layout; a
    JSON-lint of all four passes; `scripts/check.sh` is green.
  - *Evidence to collect:* diff each of the four `evals.json` golden outputs against its pre-edit
    revision and read each — confirm each now describes the kanban layout (four-folder board,
    co-located `NN-task-certificate.md`, number-keyed references, folder-move transitions,
    `**Layout:** kanban`, four-bucket enumeration, `../../../` depth) and none retains a
    flat-layout / `certificates/`-subfolder / `Status:`-flip assertion. Run `python -m json.tool`
    on all four — expect each to parse (exit 0). Run `scripts/check.sh` — expect exit 0.
  - *Status:* ☐ unverified

## Regression check

For each surface the task touched, the validator traces one downstream consumer:

- The eval harness: each `evals.json` is consumed by the repo's eval runner, which parses the
  file and matches the model output against the golden `expected_output`. Trace: run
  `python -m json.tool` on each of the four files → expect each to parse (a broken edit would make
  the harness fail to load the file), and confirm the `id`/`name`/`prompt`/`files` keys are
  unchanged so the harness still keys each case as before : ☐ (PRESERVED / REGRESSION)
- Contract source tasks 01/02/03: each fixture's golden output and worked example must match the
  `../../../` depth rule (plan.md line 17) and the journal-app worked example (plan.md line 18) as
  fixed by 01 (`plan-template.md`), 02 (`task-decomposition.md`), and 03 (`certificate-template.md`).
  Trace: diff the four fixtures' worked-example and depth assertions against those three sources →
  expect identical, so a builder/validator/certificate-author exercising a fixture is judged
  against the same layout the planner authored : ☐ (PRESERVED / REGRESSION)
- `scripts/check.sh` / Python suite: the `evals/` files sit outside the synced `skills/` tree and
  outside Python. Trace: run `scripts/sync-skills.sh --check` → expect no drift (these edits do
  not change the synced tree); run `scripts/check.sh` → expect green and the Python suite
  unchanged : ☐ (PRESERVED / REGRESSION)

## Residue

Notes for the validator: this task depends on 01–06 (each fixture asserts its skill's final
shape), but the conformance of those skills' docs is each skill task's own obligation, validated
by its own certificate — this certificate covers only the four `evals.json` golden outputs and
their consistency with the layout contract. The eval runner is not invoked here (no model run is
in scope); the obligations verify the fixtures' static shape and JSON validity, not a live eval
pass/fail. None other noted at authoring.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐ <one sentence deriving the verdict from the statuses>
