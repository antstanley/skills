# Done Certificate — Task 04: Scoring oracle

**Task:** [04-scoring_oracle.md](../04-scoring_oracle.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-05-27 — unverified

> This certificate is a verification protocol for Task 04. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 04) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** A clean-container scorer that applies a candidate patch, injects hidden tests, and returns a `ScoreReport` (`resolved`, `regressed`), proven on the gold patch and proven to keep hidden tests off the run side.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Must consume Task 02 types and Task 03 instances; the integrity rule (hidden tests only in scoring) is the spec's central invariant and must hold.

## Obligations

- **O1 — Gold patch resolves; no-op patch does not.**
  - *Claim:* feeding an instance's `goldPatch` yields `resolved: true`; an empty patch yields `resolved: false` without crashing.
  - *Evidence to collect:* run the oracle on a seed instance with `goldPatch` → expect `resolved: true`; run with a no-op patch → expect `resolved: false`. Read the resolution rule: all `failToPass` pass AND all `passToPass` hold.
  - *Checks:* resolve the test-run invocation to the reused SWE-bench Pro evaluation harness for the `swe-bench-pro` oracle convention, not a local re-implementation.
  - *Status:* ☐ unverified

- **O2 — Scoring runs in a separate container and hidden tests are absent from the run side.**
  - *Claim:* the scoring container is distinct from any run container, and run-side inputs carry no hidden test selectors/bodies.
  - *Evidence to collect:* read the scorer's container provisioning — confirm a fresh container per scoring; run the test asserting run-side inputs contain no `failToPass`/`passToPass` content.
  - *Status:* ☐ unverified

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* ☐ unverified

- **O4 — Reviewable: score a gold patch (resolved) and a no-op (not resolved); inspect run-side has no hidden tests.**
  - *Claim:* a reviewer scores both patches on one seed instance and inspects that run-side inputs carry no hidden tests.
  - *Evidence to collect:* run the two scorings on one instance and print the `ScoreReport`s; inspect the run-side input bundle for absence of hidden tests.
  - *Status:* ☐ unverified

## Regression check

No existing callers yet — the scorer is consumed by the driver in Task 07. Confirm Task 03's seed instances load unchanged into the scorer : ☐ (PRESERVED / REGRESSION)

## Residue

- Greenfield (`greenfield-hidden-tests`) oracle convention is added in Task 12; this task covers the `swe-bench-pro` convention only.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐
