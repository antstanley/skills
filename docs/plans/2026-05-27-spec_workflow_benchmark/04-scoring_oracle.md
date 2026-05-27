# Task 04 — Scoring oracle

**Plan:** [plan.md](plan.md) · **Status:** Todo · **Certificate:** [certificates/04-scoring_oracle.md](certificates/04-scoring_oracle.md)

**Implements:** [06-scoring-and-statistics.md](../../benchmark/specs/06-scoring-and-statistics.md) §The test oracle, [05-harness-architecture.md](../../benchmark/specs/05-harness-architecture.md) §Scoring isolation — the integrity rule
**Depends on:** 02, 03, 19
**Produces:** the `container` `ScoringBackend` (implementing the task 19 interface) — a clean-container scorer that applies a candidate patch, injects the hidden tests, and returns a `ScoreReport` (`resolved`, `regressed`); proven to resolve the gold patch and to keep hidden tests off the run side
**Pointers:** `benchmark/harness/scoring/oracle/`; reuse the SWE-bench Pro evaluation flow for the `swe-bench-pro` oracle convention

## Steps

- [ ] Build the scoring step: from the instance base image in a *fresh* container, apply a candidate patch, inject `failToPass`/`passToPass`, run them, and derive `resolved` (all fail-to-pass pass and all pass-to-pass hold) and `regressed`.
- [ ] Implement the `swe-bench-pro` oracle convention by reusing SWE-bench Pro's evaluation harness for the public suite.
- [ ] Enforce the integrity rule: the scoring container is separate from any run container and the hidden tests are introduced only here.
- [ ] Add the gold-patch sanity check: feeding an instance's `goldPatch` as the candidate yields `resolved: true`.
- [ ] Add a negative case: an empty/no-op patch yields `resolved: false` and does not crash.

## Definition of done

- [ ] The gold patch resolves and a no-op patch does not, on the seed instances.
- [ ] Scoring runs in a container distinct from the run side, and a test asserts the hidden test selectors are not present in the run-side inputs.
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer scores a gold patch (resolved) and a no-op patch (not resolved) on one seed instance and inspects that the run-side inputs carry no hidden tests.
