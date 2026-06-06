# Task 19 — Backend interfaces

**Plan:** [plan.md](../plan.md) · **Certificate:** [19-backend_interfaces-certificate.md](19-backend_interfaces-certificate.md)

**Implements:** [changes/merged/2026-05-27-local_backends.md](../../../benchmark/specs/changes/merged/2026-05-27-local_backends.md) §Proposed changes (`05-harness-architecture.md` → Backends, §Run container, §Scoring isolation)
**Depends on:** 02
**Produces:** the `RunBackend` and `ScoringBackend` interfaces the driver and the concrete backends code against
**Pointers:** `benchmark/harness/backends/`

## Steps

- [x] Define `RunBackend` — `run(instance, arm_or_solver) -> (ArtifactBundle, candidatePatch)` — as a Python protocol/ABC, documenting that the run side never sees the hidden tests.
- [x] Define `ScoringBackend` — `score(instance, candidatePatch) -> ScoreReport` — documenting that hidden tests are injected only here and the resolution rule is shared (all `failToPass` pass and `passToPass` hold).
- [x] State the integrity-rule contract in the interface docs: run environment and scoring environment are distinct, hidden tests on the scoring side only.
- [x] Provide an in-memory conformance test-double implementing both, and a test that drives it through the protocols.

## Definition of done

- [ ] Both protocols are defined with their documented contracts, and the test-double satisfies them and round-trips through the driver-facing calls.
- [ ] The integrity-rule contract is stated on the interfaces and a test asserts a backend's run output carries no hidden tests.
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer reads the two protocols and runs the conformance test-double through them.
