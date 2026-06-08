# Task 07 — Eval fixtures assert kanban

**Plan:** [plan.md](../plan.md) · **Certificate:** [07-eval_fixtures_kanban-certificate.md](07-eval_fixtures_kanban-certificate.md)

**Implements:** [2026-06-05-kanban_plan_folder_layout.md](../../../changes/2026-06-05-kanban_plan_folder_layout.md) — the `4 × evals.json` row of the Affected-pages table and the "four-folder ripple" / "shared worked example" implementation notes
**Depends on:** 01, 02, 03, 04, 05, 06
**Produces:** all four `evals.json` golden `expected_output`s rewritten to assert the kanban layout — the four-folder board (`backlog/`/`in-progress/`/`blocked/`/`done/`), co-located `NN-task-certificate.md` files (no `certificates/` subfolder), task references by number, folder-move transitions (not `Status:`-field flips), `**Layout:** kanban`, the four-bucket enumeration, and `../../../` spec-link depth — with the shared journal-app worked example updated identically across them
**Pointers:** `plugins/spec-planner/skills/spec-planner/evals/evals.json` (3 cases — L8 "one `NN-…md` file per task" + `(../../)` depth, L15 flat task-file list); `plugins/spec-planner/skills/done-certificates/evals/evals.json` (3 cases — L7 worked example, L8 `certificates/` path + `../NN-…md` depth); `plugins/spec-builder/skills/spec-builder/evals/evals.json` (4 cases — L7 `certificates/` subfolder + worked example, L8/L15/L22 `Status:`-flip transitions); `plugins/spec-builder/skills/validate-done-certificate/evals/evals.json` (2 cases — L7 `certificates/NN-…md` path)

## Steps

- [ ] spec-planner `evals.json`: in the golden outputs, replace "one `NN-snake_case_task.md` file per task" with the four-subfolder board + number-keyed dependency table; change the `(../../)` spec-link depth to `(../../../)`; update the flat task-file list (L15) to the kanban shape.
- [ ] done-certificates `evals.json`: replace the `certificates/` location and `../NN-…md and ../plan.md` depth with co-located `NN-task-certificate.md` authored into `backlog/` and same-directory + `../plan.md` links; update the worked example (L7).
- [ ] spec-builder `evals.json`: replace the `certificates/` subfolder mention and every per-task `Status:`-flip transition (L8/L15/L22 — "Status flip to Done", "stays In progress with a note", "reads each task's Status") with folder-move transitions (`backlog/`→`in-progress/`→`done/`, park → `blocked/`, preconditions = tasks already in `done/`) and the `**Layout:** kanban` header; the parked/unreachable case becomes an `ls blocked/` query.
- [ ] validate-done-certificate `evals.json`: replace the `certificates/01-passphrase_lock.md` path with the co-located certificate in the task's current subfolder (`.../<subfolder>/01-passphrase_lock-certificate.md`).
- [ ] Update the shared journal-app worked example (`01-passphrase_lock …`) **identically** across all four fixtures and consistent with `plan-template.md` (01), `task-decomposition.md` (02), and `certificate-template.md` (03) — no stale copy may reintroduce the flat layout.
- [ ] Validate each file is well-formed JSON (e.g. `python -m json.tool` on each) and that only `expected_output`/description prose changed — the eval `id`/`name`/`prompt`/`files` structure is preserved.
- [ ] Confirm `scripts/check.sh` passes (the `evals/` files are stripped from the synced `skills/` tree, so this edit produces no drift — but the gate must still be green).

## Definition of done

- [ ] All four golden outputs assert the four-folder board, co-located `NN-task-certificate.md` certificates, number-keyed references, folder-move transitions, `**Layout:** kanban`, the four-bucket enumeration (incl. `blocked/`), and `../../../` depth — with no flat-layout / `certificates/`-subfolder / `Status:`-flip assertions remaining.
- [ ] The shared worked example is **identical** across the four fixtures and matches tasks 01/02/03 (the shared-worked-example invariant).
- [ ] Each `evals.json` is valid JSON with its `id`/`name`/`prompt`/`files` structure intact (only golden/description prose changed).
- [ ] `scripts/check.sh` passes (no drift — `evals/` is not synced — and the Python suite is green).
- [ ] Meets the repo definition of done (Conventional Commits, `scripts/check.sh` green — see plan.md baseline; these fixtures are hand-edited, not synced).
- [ ] Reviewable: a reader diffs each golden output and sees it now describes the kanban layout; a JSON-lint of all four passes; `scripts/check.sh` is green.
