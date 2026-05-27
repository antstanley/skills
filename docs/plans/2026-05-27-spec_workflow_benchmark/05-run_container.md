# Task 05 — Run container

**Plan:** [plan.md](plan.md) · **Status:** Todo · **Certificate:** [certificates/05-run_container.md](certificates/05-run_container.md)

**Implements:** [05-harness-architecture.md](../../benchmark/specs/05-harness-architecture.md) §Run container, [02-arms.md](../../benchmark/specs/02-arms.md) §A0 — Baseline (provisioning)
**Depends on:** 01, 02, 12, 19
**Produces:** the `container` `RunBackend` (implementing the task 19 interface) — A0 runs in a provisioned container against a greenfield `TaskInstance` and yields a `candidatePatch` plus a transcript captured into an `ArtifactBundle`
**Pointers:** `benchmark/harness/arms/` (A0 recipe), `benchmark/harness/driver/` (container provisioning); provision from the greenfield run image (hidden tests excluded, task 12)

## Steps

- [ ] Provision a run container from the instance's greenfield run image (`dockerImage`, hidden tests excluded) with `jj` and `git` available.
- [ ] Implement the A0 provisioning recipe: a plain agent on the fixed model, no `spec-*` plugins, given the instance `problemStatement`.
- [ ] Run A0 to completion non-interactively and extract the `candidatePatch` as the diff of the working state against `baseCommit`.
- [ ] Capture the transcript into the `ArtifactBundle`; discard the container afterward.
- [ ] Add a test that an A0 run on one seed instance produces a non-empty, apply-able patch against `baseCommit`.

## Definition of done

- [ ] An A0 run on a seed instance yields a `candidatePatch` that applies cleanly against `baseCommit` and an `ArtifactBundle` with the transcript.
- [ ] The run container carries no hidden test content (the integrity rule holds on the run side).
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer runs A0 on one seed instance and inspects the emitted patch and transcript.
