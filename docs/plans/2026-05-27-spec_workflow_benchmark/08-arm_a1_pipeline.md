# Task 08 — Arm A1 pipeline

**Plan:** [plan.md](plan.md) · **Status:** Todo · **Certificate:** [certificates/08-arm_a1_pipeline.md](certificates/08-arm_a1_pipeline.md)

**Implements:** [02-arms.md](../../benchmark/specs/02-arms.md) §A1 — Full pipeline, [05-harness-architecture.md](../../benchmark/specs/05-harness-architecture.md) §Run container (patch extraction for parallel arms)
**Depends on:** 05, 07
**Produces:** A1 drives `spec-creator` → `spec-planner` → `spec-builder` end to end in a run container and is scored on SWE-bench Pro
**Pointers:** `benchmark/harness/arms/` (A1 recipe), extends the provisioning from task 05

## Steps

- [ ] Build the A1 provisioning recipe: install `spec-creator`, `spec-planner`, `spec-builder` and drive them non-interactively from the instance `problemStatement` (create spec → plan → build with both gates).
- [ ] Extract the single `candidatePatch` as the diff of `spec-builder`'s integration tip against `baseCommit`, without smuggling plan/spec/cert artifacts into the diff.
- [ ] Capture the spec, plan, and certificate files plus `GateEvent`s into the `ArtifactBundle`.
- [ ] Run A1 through the driver (07) and score it through the oracle (04) on the seed instances.
- [ ] Add a test that an A1 run yields an apply-able patch and a populated `ArtifactBundle` (spec + plan + certificates + gate events).

## Definition of done

- [ ] A1 runs to completion on the seed instances and yields a `candidatePatch` that applies against `baseCommit` and scores through the oracle.
- [ ] The patch excludes workflow artifacts; the spec/plan/certificate/gate-event records are captured in the bundle.
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer runs A1 on one seed instance and inspects the integration-tip patch, the captured artifacts, and the score report.

## Open questions

- Patch extraction from a multi-merge integration tip must survive conflict resolution without including test or artifact files — confirm on an instance whose plan has parallel tasks.
