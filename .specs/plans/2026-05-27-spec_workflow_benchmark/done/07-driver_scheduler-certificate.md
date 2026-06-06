# Done Certificate — Task 07: Driver scheduler

**Task:** [07-driver_scheduler.md](07-driver_scheduler.md) · **Plan:** [plan.md](../plan.md)
**State:** Validated 2026-05-27

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
  - *Evidence collected:* live campaign (1 arm × 2 instances × 2 reps = 4 trials) through a backend double → 2 healthy trials each `aggregated` with a `ScoreReport`; `score_reports` count = 2 = scored-trial count; raw %Resolved = mean(`resolved`) = 100.0%, computable from `CampaignRun.raw_resolved_rate`. Function resolution: `run_backend.run` (scheduler.py:206) and `scoring_backend.score` (scheduler.py:224) resolve to the INJECTED `RunBackend`/`ScoringBackend` parameters of `_drive_trial`, passed down from `run_campaign` — no concrete backend is imported or constructed in the module (imports are only the Task-19 Protocols + domain records). They run in order: provisioning→running calls `run`, then captured→scored calls `score`. Lifecycle `queued→provisioning→running→captured→scored→aggregated` matches 01-domain-model.md:180-191 exactly. `test_small_campaign_yields_one_score_report_per_trial` and `test_expand_matrix_is_arm_x_instance_x_seed` PASS.
  - *Status:* ☑ SATISFIED

- **O2 — Infra failures are recorded as `failed` and excluded from scored results.**
  - *Claim:* a forced infra fault lands a trial in `failed`, not `scored`, and is excluded from metrics.
  - *Evidence to collect:* run the test that injects a provisioning fault → expect the trial `status == failed` and absent from the scored set; confirm `failed != resolved: false`.
  - *Evidence collected:* live campaign forced an `InfraFault` on the "faulty" instance → both faulty trials landed `status=failed`, `report=None`, `fault="provision crash faulty"`, and were excluded from `score_reports` (2) and `raw_resolved_rate` (100% over the 2 scored only, not 50% over 4). `test_infra_fault_lands_in_failed_not_scored` PASS (2 failed / 2 scored). DISTINCT from `resolved: false`: `test_noop_patch_is_resolved_false_not_failed` PASS — a no-op patch yields `aggregated` + `report.resolved=False` (a legitimate scored outcome), NOT `failed`. `InfraFault` is a dedicated exception class kept separate from the scoring verdict.
  - *Status:* ☑ SATISFIED

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline; the concurrency pool size is a named constant).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean; grep the scheduler for a named pool-size constant.
  - *Evidence collected:* `uv sync` → "Checked 12 packages" (deps locked). `uv run pytest -q` → 45 passed (39 prior + 6 driver). `uv run ruff check` → "All checks passed!". `uv run ruff format --check` → "18 files already formatted". Named pool-size constant: `DEFAULT_POOL_SIZE = 4` (scheduler.py:54), overridable per `run_campaign(..., pool_size=)`, with `pool_size < 1` raising `ValueError`; `SEED_BASE` and the `STATUS_*` lifecycle states are also named constants.
  - *Status:* ☑ SATISFIED

- **O4 — Reviewable: launch a small campaign through a backend test-double (or the local backend); read the score reports and raw %Resolved.**
  - *Claim:* a reviewer launches a small campaign through a backend test-double or the local backend and reads the per-trial score reports and the raw %Resolved.
  - *Evidence to collect:* launch the campaign; print each `ScoreReport` and the aggregate raw %Resolved.
  - *Evidence collected:* launched a small campaign through the `DoubleBackend` and printed per-trial outcomes:
    ```
    A0/faulty/seed0:  status=failed     resolved=None  fault=provision crash faulty
    A0/faulty/seed1:  status=failed     resolved=None  fault=provision crash faulty
    A0/healthy/seed0: status=aggregated resolved=True  fault=None
    A0/healthy/seed1: status=aggregated resolved=True  fault=None
    total trials   = 4 | scored reports = 2 | failed (infra) = 2 | raw %Resolved = 100.0% (over scored only)
    ```
    Results are stable, order-independent (sorted by arm, instance, seed); `test_results_are_order_independent_across_pool_sizes` confirms pool_size 1 vs 4 yield identical ordering. Reviewer can read both the per-trial reports and the raw %Resolved.
  - *Status:* ☑ SATISFIED

## Regression check

- The Task 19 backend interface is the contract the driver calls. Trace one trial: driver → backend `run` → backend `score` (via a test-double or the local backend) → expect the same `ScoreReport` as invoking that backend by hand : ☑ PRESERVED. The driver imports only the Task-19 `RunBackend`/`ScoringBackend` Protocols (unchanged) and domain records; no existing unit was modified. One trial: `_drive_trial(healthy)` → `run()` returns `(bundle, GOLD)` → `score(instance, GOLD)` returns the backend's `ScoreReport(resolved=True)`; the driver re-keys it to the trial id via `_rebind_report_trial` (verdict preserved), matching the report the backend yields when called by hand. All 39 prior tests still pass (45 total).

## Residue

- Stats (CIs, McNemar, Pass@k) are Task 09; this task computes only raw %Resolved as a mean.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: DONE
CONFIDENCE: high
SUMMARY: O1–O4 all SATISFIED with evidence — a 4-trial campaign through a backend double yields one ScoreReport per scored trial via the INJECTED Task-19 backends (no concrete backend imported), the full lifecycle is traversed, a forced infra fault lands in `failed` excluded from the raw %Resolved (100% over scored only) and distinct from `resolved: false`, the pool size is a named constant, and tests/lint/format are clean (45 passed); the backend regression trace is PRESERVED.
