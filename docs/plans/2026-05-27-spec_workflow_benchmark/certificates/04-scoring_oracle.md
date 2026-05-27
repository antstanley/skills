# Done Certificate — Task 04: Scoring oracle

**Task:** [04-scoring_oracle.md](../04-scoring_oracle.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-05-27 — unverified

> This certificate is a verification protocol for Task 04. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 04) ≡ every obligation O1…O5 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** A clean-container `ScoringBackend` that applies a candidate patch, injects hidden tests, and returns a `ScoreReport` (`resolved`, `regressed`) under the `greenfield-hidden-tests` convention, proven on a greenfield reference solution and proven to keep hidden tests off the run side.
- **P2 — Obligations.** Done iff O1…O5 all hold; O5 is the Reviewable item.
- **P3 — Invariants.** Must consume Task 02 types and Task 12 greenfield instances (including the self-test instance's private reference solution); the integrity rule (hidden tests only in scoring) is the spec's central invariant and must hold; the resolved/regressed verdict comes from the shared `resolution.py` rule, not a re-implementation.

## Obligations

- **O1 — Reference solution resolves; no-op patch does not.**
  - *Claim:* feeding the greenfield self-test instance's private reference solution yields `resolved: true`; an empty patch yields `resolved: false` without crashing.
  - *Evidence to collect:* run the oracle on the self-test instance with the reference solution → expect `resolved: true`; run with a no-op patch → expect `resolved: false`. Read the resolution rule: all `failToPass` pass AND all `passToPass` hold.
  - *Checks:* resolve the test-run invocation to the `greenfield-hidden-tests` oracle convention against the scoring image (hidden tests included, from Task 12); the reference solution is read from the suite directory, never from the arms-visible `goldPatch` field.
  - *Status:* ☐ unverified

- **O2 — Scoring runs in a separate container and hidden tests are absent from the run side.**
  - *Claim:* the scoring container is distinct from any run container, and run-side inputs carry no hidden test selectors/bodies.
  - *Evidence to collect:* read the scorer's container provisioning — confirm a fresh container per scoring; run the test asserting run-side inputs contain no `failToPass`/`passToPass` content.
  - *Status:* ☐ unverified

- **O3 — Verdict is single-sourced through `resolution.py`.**
  - *Claim:* the container scorer derives `resolved`/`regressed` from the same `benchmark/harness/scoring/resolution.py` rule the `local` backend uses, so the definition is not duplicated per backend.
  - *Evidence to collect:* resolve the scorer's verdict derivation to a call into `resolution.py` (the M0 module), not an inline re-implementation; confirm by reading the call site.
  - *Status:* ☐ unverified

- **O4 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* ☐ unverified

- **O5 — Reviewable: score the reference solution (resolved) and a no-op (not resolved); inspect run-side has no hidden tests.**
  - *Claim:* a reviewer scores both patches on the greenfield self-test instance and inspects that run-side inputs carry no hidden tests.
  - *Evidence to collect:* run the two scorings on the self-test instance and print the `ScoreReport`s; inspect the run-side input bundle for absence of hidden tests.
  - *Status:* ☐ unverified

## Regression check

No existing callers yet — the scorer is consumed by the driver in Task 07. Confirm Task 12's greenfield instances load unchanged into the scorer, and the shared `resolution.py` rule still passes its M0 tests after this task wires the container scorer to it : ☐ (PRESERVED / REGRESSION)

## Residue

- This task implements the `greenfield-hidden-tests` oracle convention only. The `swe-bench-pro` convention was removed from the canonical spec (2026-05-27) and is out of scope; re-adding it is a separate change spec.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐
