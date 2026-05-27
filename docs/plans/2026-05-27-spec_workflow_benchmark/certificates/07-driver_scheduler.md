# Done Certificate — Task 07: Driver scheduler

**Task:** [07-driver_scheduler.md](../07-driver_scheduler.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-05-27 — unverified

> This certificate is a verification protocol for Task 07. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 07) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** A backend-neutral driver: a campaign runs end to end through the `RunBackend` / `ScoringBackend` interface — expanding the matrix, driving each trial through its lifecycle, and emitting one `ScoreReport` per trial.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Calls run then score through the Task 19 interface; must not bind to a concrete backend. Its first real exercise is the local pipeline demo (Task 23); the container backends (04/05) plug in at M1.

## Obligations

- **O1 — A campaign over a suite yields one `ScoreReport` per trial via the backend interface.**
  - *Claim:* the driver expands (arm × instance × seed), runs each trial through `queued → provisioning → running → captured → scored → aggregated`, calling the campaign's `RunBackend` then its `ScoringBackend`, and produces a `ScoreReport` per trial, from which raw %Resolved is computable.
  - *Evidence to collect:* run a small campaign through a backend test-double (or the local backend); count `ScoreReport`s = number of trials; compute raw %Resolved as the mean of `resolved`.
  - *Checks:* resolve the per-trial calls — confirm `run` and `score` resolve to the campaign's backend through the Task 19 interface, not a hardcoded backend, and run in that order.
  - *Status:* ☐ unverified

- **O2 — Infra failures are recorded as `failed` and excluded from scored results.**
  - *Claim:* a forced infra fault lands a trial in `failed`, not `scored`, and is excluded from metrics.
  - *Evidence to collect:* run the test that injects a provisioning fault → expect the trial `status == failed` and absent from the scored set; confirm `failed != resolved: false`.
  - *Status:* ☐ unverified

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline; the concurrency pool size is a named constant).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean; grep the scheduler for a named pool-size constant.
  - *Status:* ☐ unverified

- **O4 — Reviewable: launch a small campaign through a backend test-double (or the local backend); read the score reports and raw %Resolved.**
  - *Claim:* a reviewer launches a small campaign through a backend test-double or the local backend and reads the per-trial score reports and the raw %Resolved.
  - *Evidence to collect:* launch the campaign; print each `ScoreReport` and the aggregate raw %Resolved.
  - *Status:* ☐ unverified

## Regression check

- The Task 19 backend interface is the contract the driver calls. Trace one trial: driver → backend `run` → backend `score` (via a test-double or the local backend) → expect the same `ScoreReport` as invoking that backend by hand : ☐ (PRESERVED / REGRESSION)

## Residue

- Stats (CIs, McNemar, Pass@k) are Task 09; this task computes only raw %Resolved as a mean.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐
