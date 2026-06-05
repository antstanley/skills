# Task 23 — Local pipeline demonstration

**Plan:** [plan.md](plan.md) · **Status:** Done · **Certificate:** [certificates/23-local_pipeline_demo.md](certificates/23-local_pipeline_demo.md)

**Implements:** [05-harness-architecture.md](../../benchmark/specs/05-harness-architecture.md) §Component shape (backend-neutral driver); [06-scoring-and-statistics.md](../../benchmark/specs/06-scoring-and-statistics.md) §Repetition and Pass@k (over the fixture); [changes/merged/2026-05-27-local_backends.md](../../benchmark/specs/changes/merged/2026-05-27-local_backends.md) (end to end)
**Depends on:** 07, 20, 21, 22
**Produces:** the driver runs a local `Campaign` (`backend: local`, `solver: fixture`) over the `local-fixture` suite end to end and yields a deterministic resolved verdict plus a minimal %Resolved — the whole run → score → aggregate pipeline, no Docker
**Pointers:** `benchmark/harness/driver/` (task 07), the local backends (tasks 20, 22), the fixture suite (task 21)

## Steps

- [x] Assemble a local `Campaign`: `backend: local`, `solver: fixture`, the `local-fixture` suite, a small `trialsPerInstance`.
- [x] Run it through the driver (task 07) using the local `RunBackend` (22) and local `ScoringBackend` (20).
- [x] Assert the fixture trial resolves deterministically across repeated runs (same verdict every time).
- [x] Compute and print %Resolved over the fixture trials; confirm `1.0` with the fixture solver and `0.0` with a no-op solver variant.

## Definition of done

- [ ] The driver runs the local campaign end to end and the fixture trial is deterministically `resolved` across repeated runs.
- [ ] %Resolved over the fixture is computed and correct — `1.0` with the fixture solver, `0.0` with a no-op variant.
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer runs the local campaign and reads the deterministic resolved verdict and %Resolved — run → score → aggregate, with no Docker, BenchFlow, or API. **(M0 capstone.)**
