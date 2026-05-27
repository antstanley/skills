# Done Certificate — Task 20: Local ScoringBackend

**Task:** [20-local_scoring_backend.md](../20-local_scoring_backend.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-05-27 — unverified

> This certificate is a verification protocol for Task 20. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 20) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** A `ScoringBackend` that scores a candidate patch via a temp checkout and a local `pytest` run — no Docker.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Implements the Task 19 `ScoringBackend` interface; uses Task 18's `local` oracle convention; must honour the integrity rule.

## Obligations

- **O1 — Gold resolves, no-op does not, on an inline test instance.**
  - *Claim:* `score()` makes a fresh temp checkout at `baseCommit`, applies the patch, injects hidden tests, runs `pytest`, and derives `resolved`/`regressed` correctly — gold patch resolves, no-op does not.
  - *Evidence to collect:* run the backend's tests over an inline throwaway repo+tests — expect gold → `resolved: true`, no-op → `resolved: false`; confirm `regressed` is set when a `passToPass` breaks.
  - *Checks:* resolve the resolution rule to the shared definition (all `failToPass` pass AND `passToPass` hold), not a local re-derivation; resolve the `pytest` invocation to a subprocess against the temp checkout.
  - *Status:* ☐ unverified

- **O2 — Scoring dir is separate from the run dir; hidden tests injected only here.**
  - *Claim:* the scoring temp directory is distinct from any run directory and the hidden tests are introduced only on the scoring side.
  - *Evidence to collect:* read the temp-dir handling; run the test asserting the scoring dir differs from the run dir and hidden tests appear only in scoring.
  - *Status:* ☐ unverified

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* ☐ unverified

- **O4 — Reviewable: score a gold and a no-op patch locally; inspect run side has no hidden tests.**
  - *Claim:* a reviewer scores a gold patch (resolved) and a no-op (not resolved) locally and inspects that the run side carries no hidden tests.
  - *Evidence to collect:* run the two scorings on the inline instance; print the `ScoreReport`s; inspect the directories.
  - *Status:* ☐ unverified

## Regression check

- Task 19's `ScoringBackend` interface is the contract. Trace the local backend through the interface's conformance test → expect it satisfies the protocol unchanged : ☐ (PRESERVED / REGRESSION)

## Residue

- Local–container verdict parity is a change-spec Open question; the validator notes it but it is not an obligation of this task.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐
