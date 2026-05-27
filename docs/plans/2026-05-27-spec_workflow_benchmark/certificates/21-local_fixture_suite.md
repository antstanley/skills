# Done Certificate — Task 21: Local-fixture suite

**Task:** [21-local_fixture_suite.md](../21-local_fixture_suite.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-05-27 — unverified

> This certificate is a verification protocol for Task 21. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 21) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** The bundled `local-fixture` instance — a small repo, a hidden `pytest` suite, and a gold patch — as a validated `TaskInstance` scorable by the local `ScoringBackend`.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Uses Task 18's `local-fixture` kind / `local` convention and Task 20's local `ScoringBackend`.

## Obligations

- **O1 — The fixture validates and the local backend scores gold resolved, no-op not.**
  - *Claim:* the fixture `TaskInstance` validates, and the local `ScoringBackend` scores its `goldPatch` resolved and a no-op not.
  - *Evidence to collect:* load the fixture and validate it; score `goldPatch` via the local backend → `resolved: true`; score a no-op → `resolved: false`.
  - *Checks:* resolve the instance fields — `kind: local-fixture`, `oracleConvention: local`, `dockerImage: null`, `contaminationTier: authored-private`.
  - *Status:* ☐ unverified

- **O2 — The suite needs no Docker and no network.**
  - *Claim:* loading and scoring the fixture uses neither Docker nor network.
  - *Evidence to collect:* run the fixture's test with no Docker daemon and no network — expect it passes; confirm no `dockerImage` is referenced.
  - *Status:* ☐ unverified

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* ☐ unverified

- **O4 — Reviewable: load the fixture, score its gold patch via the local backend, see resolved.**
  - *Claim:* a reviewer loads the fixture and scores its gold patch through the local backend and sees `resolved: true`.
  - *Evidence to collect:* load the fixture; score the gold patch; print the `ScoreReport`.
  - *Status:* ☐ unverified

## Regression check

- Task 20's local `ScoringBackend` scores this fixture. Trace the gold patch through the backend → expect the same `resolved: true` the backend's own tests showed : ☐ (PRESERVED / REGRESSION)

## Residue

- Fixture breadth (one instance vs several to exercise the scorer's branches) is an Open question shared with the change spec; not an obligation here.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐
