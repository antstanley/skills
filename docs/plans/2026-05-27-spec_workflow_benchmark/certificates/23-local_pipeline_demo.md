# Done Certificate — Task 23: Local pipeline demonstration

**Task:** [23-local_pipeline_demo.md](../23-local_pipeline_demo.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-05-27 — unverified

> This certificate is a verification protocol for Task 23. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 23) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** The driver runs a local `Campaign` (`backend: local`, `solver: fixture`) over the `local-fixture` suite end to end and yields a deterministic resolved verdict plus a minimal %Resolved — run→score→aggregate, no Docker.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Wires the Task 07 driver, the Task 20 local `ScoringBackend`, the Task 22 local `RunBackend`, and the Task 21 fixture; must not modify their behavior, only compose them.

## Obligations

- **O1 — The driver runs the local campaign end to end with a deterministic resolved fixture trial.**
  - *Claim:* a local `Campaign` (`backend: local`, `solver: fixture`, fixture suite) runs through the driver and the fixture trial is `resolved` deterministically across repeated runs.
  - *Evidence to collect:* run the local campaign twice; confirm the fixture trial is `resolved: true` both times with an identical `ScoreReport`.
  - *Checks:* resolve the run/score calls to the local backends (Tasks 22/20) selected by `Campaign.backend == local`, not the container backends.
  - *Status:* ☐ unverified

- **O2 — %Resolved over the fixture is computed and correct.**
  - *Claim:* %Resolved is `1.0` with the fixture solver and `0.0` with a no-op solver variant.
  - *Evidence to collect:* run with `solver=fixture` → expect %Resolved `1.0`; run with a no-op solver variant → expect `0.0`.
  - *Status:* ☐ unverified

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* ☐ unverified

- **O4 — Reviewable: run the local campaign; read the deterministic verdict + %Resolved (no Docker). (M0 capstone.)**
  - *Claim:* a reviewer runs the local campaign and reads the deterministic resolved verdict and %Resolved — run→score→aggregate with no Docker, BenchFlow, or API.
  - *Evidence to collect:* run the campaign; print the per-trial `ScoreReport` and the aggregate %Resolved; confirm no Docker/network/API was used.
  - *Status:* ☐ unverified

## Regression check

- The driver (Task 07) is exercised here for the first time. Trace one trial: driver → local `RunBackend` (22) → local `ScoringBackend` (20) → expect the `ScoreReport` matches scoring the fixture gold patch directly (Task 21) : ☐ (PRESERVED / REGRESSION)

## Residue

- This is pipeline verification on a fixture; full statistics (CIs, McNemar, Pass@k) arrive with Task 09 on the container path. The minimal %Resolved here is superseded, not the final reporting.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐
