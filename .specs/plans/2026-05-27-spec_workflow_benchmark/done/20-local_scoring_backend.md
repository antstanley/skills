# Task 20 — Local ScoringBackend

**Plan:** [plan.md](../plan.md) · **Certificate:** [20-local_scoring_backend-certificate.md](20-local_scoring_backend-certificate.md)

**Implements:** [changes/merged/2026-05-27-local_backends.md](../../../benchmark/specs/changes/merged/2026-05-27-local_backends.md) §Proposed changes (`06-scoring-and-statistics.md` → The test oracle: `local`; `05-harness-architecture.md` → Scoring isolation: `local`)
**Depends on:** 18, 19
**Produces:** a `ScoringBackend` that scores a candidate patch via a temp checkout and a local `pytest` run — no Docker
**Pointers:** `benchmark/harness/scoring/` (local backend), the `ScoringBackend` interface from task 19

## Steps

- [x] Implement `score()`: make a fresh temp checkout at `baseCommit` in a directory distinct from any run directory, apply the `candidatePatch`, inject the hidden `failToPass`/`passToPass`, run `pytest` as a subprocess.
- [x] Derive `resolved` (all `failToPass` pass and `passToPass` hold) and `regressed` using the shared resolution rule; return a `ScoreReport`.
- [x] Exercise it in tests with an inline throwaway repo+tests (not the shipped fixture): a gold patch resolves, a no-op does not.
- [x] Assert the scoring temp dir is separate from the run dir and the hidden tests are introduced only on the scoring side.

## Definition of done

- [ ] On the inline test instance, a gold patch yields `resolved: true` and a no-op yields `resolved: false`, with `regressed` set correctly.
- [ ] The scoring directory is distinct from any run directory and a test asserts hidden tests are injected only on the scoring side (integrity rule).
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer scores a gold patch (resolved) and a no-op (not resolved) locally and inspects that the run side carries no hidden tests.
