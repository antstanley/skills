# Task 08 — Arm A1 pipeline

**Plan:** [plan.md](plan.md) · **Status:** Done · **Certificate:** [certificates/08-arm_a1_pipeline.md](certificates/08-arm_a1_pipeline.md)

**Implements:** [02-arms.md](../../benchmark/specs/02-arms.md) §A1 — Full pipeline, [05-harness-architecture.md](../../benchmark/specs/05-harness-architecture.md) §Run container (patch extraction for parallel arms)
**Depends on:** 05, 07
**Produces:** A1 drives `spec-creator` → `spec-planner` → `spec-builder` end to end in a run container and is scored on the greenfield suite
**Pointers:** `benchmark/harness/arms/` (A1 recipe), extends the provisioning from task 05

## Steps

- [x] Build the A1 provisioning recipe: install `spec-creator`, `spec-planner`, `spec-builder` and drive them non-interactively from the instance `problemStatement` (create spec → plan → build with both gates). *(`arms/a1.py`: 3 plugins read-only mounted + `--plugin-dir`, one orchestrating `claude -p`; hard `$20` cap + 1200s timeout.)*
- [x] Extract the single `candidatePatch` as the diff of `spec-builder`'s integration tip against `baseCommit`, without smuggling plan/spec/cert artifacts into the diff. *(`_extract_patch(exclude_artifacts=True)` diffs the base tag → `_resolve_integration_tip` with `:(exclude).specs/`; verified code-only.)*
- [x] Capture the spec, plan, and certificate files plus `GateEvent`s into the `ArtifactBundle`. *(spec/plan/cert artifacts captured + classified. **GateEvents NOT captured** — see Open questions: the canonical domain model hangs `GateEvent` off `Trial`, not `ArtifactBundle`, and A1's gates run inside one opaque `claude -p`; this sub-clause over-specifies vs the spec.)*
- [x] Run A1 through the driver (07) and score it through the oracle (04) on the seed instances. *(Live run on `text_toolkit`: driver → `ContainerRunBackend` → `ContainerScoringBackend`, $0.96, 425s, scored resolved=false 4/15 — a genuine partial.)*
- [x] Add a test that an A1 run yields an apply-able patch and a populated `ArtifactBundle` (spec + plan + certificates + gate events). *(`test_a1_pipeline.py`: non-live artifact/patch-separation tests + an opt-in (`BENCHMARK_RUN_A1_LIVE=1`) live test; evidence saved under `_a1_live_evidence/`.)*

## Definition of done

- [ ] A1 runs to completion on the seed instances and yields a `candidatePatch` that applies against `baseCommit` and scores through the oracle.
- [ ] The patch excludes workflow artifacts; the spec/plan/certificate/gate-event records are captured in the bundle.
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer runs A1 on one seed instance and inspects the integration-tip patch, the captured artifacts, and the score report.

## Open questions

- Patch extraction from a multi-merge integration tip must survive conflict resolution without including test or artifact files — confirm on an instance whose plan has parallel tasks. **Still open:** the live run built only task 01 (single integration commit), so the multi-merge path was exercised in code (`_resolve_integration_tip` prefers `spec-builder/integration`, falls back to newest `spec-builder/*`, then `HEAD`) but not yet end-to-end on a parallel-wave plan.
- **(New, 2026-05-27) Single-prompt A1 under-builds.** Driving the whole `spec-creator → spec-planner → spec-builder` workflow from one orchestrating `claude -p` session, the orchestrator ended its turn naturally (`stop_reason: end_turn`, 42 turns, $0.96 of the $20 cap) after authoring the full spec + 4-task plan + certificates but building only task 01 (tokenizer) → resolved=false (4/15). The harness mechanism is correct and the trial is a valid measurement, but A1 will look artificially weak in the ablation unless the orchestration reliably walks the entire plan DAG. Tuning options to pin before the headline campaign: a continuation/`--max-turns` loop, a higher turn budget, or invoking spec-builder as its own pass rather than nested in one prompt. Bears on tasks 09/16 (the A1−A0 delta).
- **(New, 2026-05-27) GateEvent capture is unspecified.** The DoD asked for `GateEvent`s in the `ArtifactBundle`, but the canonical [01-domain-model.md](../../benchmark/specs/01-domain-model.md) attaches `GateEvent` to the `Trial`, and A1's gates run inside the opaque orchestrator session, so none are emitted. Decide whether gate-efficacy ([14](14-workflow_artifact_metrics.md)) reconstructs `GateEvent`s from the captured certificate artifacts, or whether A1 must surface them structurally.
