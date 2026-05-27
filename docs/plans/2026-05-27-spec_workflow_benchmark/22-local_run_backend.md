# Task 22 — Local RunBackend and fixture solver

**Plan:** [plan.md](plan.md) · **Status:** Done · **Certificate:** [certificates/22-local_run_backend.md](certificates/22-local_run_backend.md)

**Implements:** [changes/2026-05-27-local_backends.md](../../benchmark/specs/changes/2026-05-27-local_backends.md) §Proposed changes (`05-harness-architecture.md` → Run container: `local`, Backends — the `fixture` solver)
**Depends on:** 18, 19, 21
**Produces:** a `RunBackend` that runs in a temp working directory with no Docker, supporting a `fixture` scripted solver that emits the instance `goldPatch`
**Pointers:** `benchmark/harness/arms/` or `benchmark/harness/backends/` (local run backend), the `RunBackend` interface from task 19

## Steps

- [x] Implement `run()`: make a temp working directory checked out at `baseCommit`, distinct from any scoring directory.
- [x] Implement the `fixture` solver mode: emit the instance `goldPatch` as the `candidatePatch` (deterministic, no LLM/API).
- [x] Produce an `ArtifactBundle` with a minimal `Telemetry` record (at least `wallClockSeconds`; token/cost zero for the fixture solver).
- [x] Add a test that the local backend with `solver=fixture` on the fixture instance emits the gold patch and a populated bundle, and that the run dir carries no hidden tests.

## Definition of done

- [ ] On the fixture instance, the local `RunBackend` with `solver=fixture` emits the `goldPatch` as `candidatePatch` plus an `ArtifactBundle` with a `Telemetry` record.
- [ ] The run directory is distinct from the scoring directory and carries no hidden tests (integrity rule on the run side).
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer runs the fixture solver on the fixture instance and inspects the emitted gold patch and the artifact bundle.
