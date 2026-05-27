# Done Certificate — Task 15: Cost and robustness metrics

**Task:** [15-cost_robustness_metrics.md](../15-cost_robustness_metrics.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-05-27 — unverified

> This certificate is a verification protocol for Task 15. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 15) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** Cost-matched %Resolved and parallel speedup, plus regression rate, merge-conflict rate, manual-pause rate, and gate-retry depth.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Consumes Task 06 telemetry, Task 09 stats base, and Task 10/11 arms; must not modify the underlying score reports or telemetry.

## Obligations

- **O1 — Cost-matched %Resolved, parallel speedup, and the four robustness metrics are produced with intervals on a documented basis.**
  - *Claim:* cost-matched %Resolved (on a fixed budget basis), parallel speedup, and merge-conflict / manual-pause / gate-retry-depth / regression rates are produced per (arm, suite) with intervals.
  - *Evidence to collect:* run the metrics over a campaign; read each `MetricResult` → expect all present with intervals; read the documented cost-matching basis (tokens, dollars, or wall-clock).
  - *Checks:* resolve cost-matching inputs to `ArtifactBundle.telemetry`; resolve manual-pause rate to `GateEvent.verdict == UNVERIFIED` and retry depth to `GateEvent.retryIndex`.
  - *Status:* ☐ unverified

- **O2 — The computations are verified against synthetic inputs with known answers.**
  - *Claim:* cost-matching and the robustness rates compute as expected on synthetic telemetry/gate inputs.
  - *Evidence to collect:* run the synthetic-input tests → expect each metric matches its hand-computed value.
  - *Status:* ☐ unverified

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* ☐ unverified

- **O4 — Reviewable: read the cost-matched table and robustness columns; confirm the cost basis is stated.**
  - *Claim:* a reviewer reads the cost-matched table and the robustness columns and confirms the cost basis is stated.
  - *Evidence to collect:* render the cost-matched + robustness columns; show the documented cost-matching basis.
  - *Status:* ☐ unverified

## Regression check

- Task 09's outcome stats must be unchanged. Trace the A1−A0 %Resolved delta after cost metrics are added → expect the raw (un-matched) numbers are identical to Task 09's : ☐ (PRESERVED / REGRESSION)

## Residue

- Cost-matching basis is a task Open question; if unset at validation, O1 is at best UNVERIFIED.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐
