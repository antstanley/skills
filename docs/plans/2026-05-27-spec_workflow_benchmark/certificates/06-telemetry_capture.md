# Done Certificate — Task 06: Telemetry capture

**Task:** [06-telemetry_capture.md](../06-telemetry_capture.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-05-27 — unverified

> This certificate is a verification protocol for Task 06. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 06) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** Every run records `inputTokens`, `outputTokens`, `costUsd`, `wallClockSeconds`, and `agentTurns` into `ArtifactBundle.telemetry`, uniformly across arms.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Wraps the Task 05 run loop; must not change the `candidatePatch` or transcript the run produces.

## Obligations

- **O1 — An A0 run yields a `Telemetry` record with all five fields populated and non-negative.**
  - *Claim:* after an A0 run, `Telemetry` has `inputTokens`, `outputTokens`, `costUsd`, `wallClockSeconds`, `agentTurns`, each present and ≥ 0.
  - *Evidence to collect:* run A0 on a seed instance; read `ArtifactBundle.telemetry` → expect all five fields present and non-negative. Run the test asserting the same.
  - *Checks:* resolve the telemetry write to the `Telemetry` type from Task 02 (schema-validated), not an ad-hoc dict.
  - *Status:* ☐ unverified

- **O2 — Capture is uniform across arms, or the A0 granularity gap is documented.**
  - *Claim:* the same capture path serves the plain A0 baseline and the plugin arms, or any A0 granularity shortfall is recorded in `plan.md` Open questions.
  - *Evidence to collect:* read the capture implementation — confirm it is arm-agnostic; if A0 cannot report at parity, read the recorded gap in `plan.md` §Open questions.
  - *Status:* ☐ unverified

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* ☐ unverified

- **O4 — Reviewable: inspect an A0 bundle and see complete telemetry.**
  - *Claim:* a reviewer inspects the `ArtifactBundle` from an A0 run and sees complete telemetry.
  - *Evidence to collect:* run A0 once; print `ArtifactBundle.telemetry`.
  - *Status:* ☐ unverified

## Regression check

- Task 05's run output (patch + transcript) must be unchanged by the telemetry wrapper. Trace one A0 run with telemetry enabled → expect the same `candidatePatch` and transcript as without it : ☐ (PRESERVED / REGRESSION)

## Residue

- Cost-matching that consumes this telemetry is Task 15; this task only captures the fields.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐
