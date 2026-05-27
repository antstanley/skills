# Task 04 — Scoring oracle

**Plan:** [plan.md](plan.md) · **Status:** Todo · **Certificate:** [certificates/04-scoring_oracle.md](certificates/04-scoring_oracle.md)

**Implements:** [06-scoring-and-statistics.md](../../benchmark/specs/06-scoring-and-statistics.md) §The test oracle, [05-harness-architecture.md](../../benchmark/specs/05-harness-architecture.md) §Scoring isolation — the integrity rule
**Depends on:** 02, 12, 19
**Produces:** the `container` `ScoringBackend` (implementing the task 19 interface) — a clean-container scorer that applies a candidate patch, injects the hidden tests, and returns a `ScoreReport` (`resolved`, `regressed`); proven to resolve a greenfield reference solution and to keep hidden tests off the run side
**Pointers:** `benchmark/harness/scoring/oracle/`; the `greenfield-hidden-tests` oracle convention against the greenfield scoring image (hidden tests included), reusing the shared resolution rule in `benchmark/harness/scoring/resolution.py` (built in M0)

## Steps

- [ ] Build the scoring step: from the instance's scoring image in a *fresh* container, apply a candidate patch, inject `failToPass`/`passToPass`, run them, and derive `resolved` (all fail-to-pass pass and all pass-to-pass hold) and `regressed` via the shared `resolution.py` rule.
- [ ] Implement the `greenfield-hidden-tests` oracle convention: run the instance's withheld suite in the scoring image built with the hidden tests included (task 12).
- [ ] Enforce the integrity rule: the scoring container is separate from any run container and the hidden tests are introduced only here.
- [ ] Add the reference-solution sanity check: feeding a greenfield self-test instance's private reference solution (shipped in the suite dir by task 12, never in the arms-visible `goldPatch` field) as the candidate yields `resolved: true`.
- [ ] Add a negative case: an empty/no-op patch yields `resolved: false` and does not crash.

## Definition of done

- [ ] The reference solution resolves and a no-op patch does not, on the greenfield self-test instance.
- [ ] Scoring runs in a container distinct from the run side, and a test asserts the hidden test selectors are not present in the run-side inputs.
- [ ] The container scorer derives its verdict from the same `resolution.py` rule the `local` backend uses, so the resolved/regressed definition is single-sourced across backends.
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer scores the reference solution (resolved) and a no-op patch (not resolved) on the greenfield self-test instance and inspects that the run-side inputs carry no hidden tests.

## Open questions

- Whether the container scorer's verdict should be cross-checked for parity against the already-built `local` `ScoringBackend` on a shared instance (the local–container verdict-parity question carried over from the local_backends change spec), or accepted as backend-specific.
