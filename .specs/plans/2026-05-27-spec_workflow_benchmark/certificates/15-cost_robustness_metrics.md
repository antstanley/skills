# Done Certificate — Task 15: Cost and robustness metrics

**Task:** [15-cost_robustness_metrics.md](../15-cost_robustness_metrics.md) · **Plan:** [plan.md](../plan.md)
**State:** Validated 2026-05-28

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
  - *Status:* SATISFIED — `cost_robustness_metric_results` (`benchmark/harness/stats/cost_robustness.py:514`) emits the six `MetricResult` rows per arm; live demo over a 2×2 synthetic CampaignRun produced 12 rows tagged with `suite='demo'`, each carrying `ciLow`/`ciHigh`. Cost basis pinned `dollars` (`DEFAULT_COST_BASIS`, line 171), with `CostBasis` enum `dollars|tokens|wall_clock` (lines 157–167) documented in the module docstring (§"Cost-matching basis (PINNED)"). Cost resolution traces to `ArtifactBundle.telemetry` via `_trial_cost` (lines 177–197) reading `costUsd` / `inputTokens+outputTokens` / `wallClockSeconds` — all three fields present in `benchmark/harness/domain.py:361-367`. Manual-pause traces to `GateEvent.verdict == GATE_VERDICT_UNVERIFIED` (`manual_pause_rate`, line 394; `GATE_VERDICT_UNVERIFIED = "UNVERIFIED"`, line 143; `GateEvent.verdict` at `domain.py:405`). Retry depth traces to `GateEvent.retryIndex` (`gate_retry_depth_for_arm`, line 439; `GateEvent.retryIndex` at `domain.py:406`).

- **O2 — The computations are verified against synthetic inputs with known answers.**
  - *Claim:* cost-matching and the robustness rates compute as expected on synthetic telemetry/gate inputs.
  - *Evidence to collect:* run the synthetic-input tests → expect each metric matches its hand-computed value.
  - *Status:* SATISFIED — `uv run pytest benchmark/tests/test_cost_robustness.py -v` → **24 passed in 0.16s**. Each test hand-computes its expected value: equal-budget min-of-max (`test_equal_budget_picks_min_of_max_per_arm`), cost-matched %Resolved on all three bases (dollars/tokens/wall_clock; `test_cost_matched_resolved_*_known_answer`/`*_basis`/`*_at_arms_own_max_equals_raw`), parallel-speedup ratio with edges (`test_parallel_speedup_known_ratio` 600/300=2.0, single-trial/no-trials/zero-walls = 1.0), merge-conflict fraction (`test_merge_conflict_rate_known_fraction` 1/4=0.25 with Wilson 95%), manual-pause `UNVERIFIED` fraction (`test_manual_pause_rate_unverified_fraction` 1/4), gate-retry mean + Bessel-corrected normal-approximation CI on [0,1,2,3] mean 1.5 with half-width `z·sqrt(5/3)/sqrt(4)`, regression rate, and end-to-end emission cross-checking all six metrics at once (`test_cost_robustness_metric_results_known_values`).

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* SATISFIED — `bash scripts/check.sh` → `uv sync` (33 packages, 0.49ms, NO new deps; `pyproject.toml`/`uv.lock` unchanged in diff), `ruff format --check` (85 files already formatted), `ruff check` (All checks passed!), `pyright` (0 errors, 0 warnings, 0 informations), `pytest` **237 passed, 5 skipped in 162.99s** (5 skips are pre-existing live opt-in tests gated on `BENCHMARK_RUN_*_LIVE=1`). Named limits in `cost_robustness.py`: `_Z_95` (line 120, re-bound from `WILSON_Z_95`), `_DEFAULT_SPEEDUP_NO_OBSERVATION` (line 149), `_SINGLE_TRIAL_SPEEDUP` (line 154), `GATE_VERDICT_UNVERIFIED` (line 143), `DEFAULT_COST_BASIS` (line 171), and the metric-name constants on lines 124–139 — no bare magic values at call sites.

- **O4 — Reviewable: read the cost-matched table and robustness columns; confirm the cost basis is stated.**
  - *Claim:* a reviewer reads the cost-matched table and the robustness columns and confirms the cost basis is stated.
  - *Evidence to collect:* render the cost-matched + robustness columns; show the documented cost-matching basis.
  - *Status:* SATISFIED — rendered the table over a synthetic 2-arm × 2-trial CampaignRun via `cost_robustness_metric_results(run, suite='demo')`; got 12 rows (6 metrics × 2 arms), each with `value`, `ciLow`, `ciHigh`, `n`. Sample rows: `A0 cost_matched_resolved 0.5000 [0.0945, 0.9055] n=2` (auto-derived `B = min($0.20, $1.20) = $0.20`, A0 within-budget {i1,i2} resolved {i2} ⇒ 1/2; A1 within {} ⇒ 0/2 → `0.0000 [0.0000, 0.6576]`), `A0 parallel_speedup 1.7500` (seq 70 / parallel 40), `A1 manual_pause_rate 0.5000 [0.0945, 0.9055]` (1 UNVERIFIED of 2), `A1 gate_retry_depth 1.0000` (single event, point reported in both bounds — degenerate interval per `GateRetryDepth` docstring). Cost basis stated three places: (a) module docstring §"Cost-matching basis (PINNED)" — "Headline basis: dollars (`costUsd`)"; (b) `DEFAULT_COST_BASIS = CostBasis.DOLLARS` (line 171); (c) the `CostBasis` enum carried through every cost-matched call so the choice is explicit at the call site. Task file Open question is also marked Resolved with the same pinning rationale.

## Regression check

- Task 09's outcome stats must be unchanged. Trace the A1−A0 %Resolved delta after cost metrics are added → expect the raw (un-matched) numbers are identical to Task 09's : PRESERVED. `jj diff --stat` shows only four files touched: `benchmark/harness/stats/__init__.py` (additive re-export), `benchmark/harness/stats/cost_robustness.py` (new module), `benchmark/tests/test_cost_robustness.py` (new tests), and the task md (Open question resolved). `jj diff --stat -- benchmark/harness/driver/ benchmark/harness/stats/outcome.py benchmark/harness/domain.py` → 0 files changed. All 237 non-live tests pass, which includes Task 09's outcome / pass@1 / mcnemar tests — raw %Resolved arithmetic is unmodified.

## Residue

- Cost-matching basis is a task Open question; if unset at validation, O1 is at best UNVERIFIED.
  - **Resolved before validation:** `DEFAULT_COST_BASIS = CostBasis.DOLLARS` pinned in `cost_robustness.py:171`, documented in the module docstring and in the task file's Open questions block; O1 SATISFIED.
- Sample limitations documented in the module docstring §"Real-data zeros": on captured live data, `gate_retry_depth = 0` (only final `retryIndex` is preserved), `manual_pause_rate = 0` (no `UNVERIFIED` in production runs), and merge-conflict rate is 0 except for an A4 side channel the driver does not currently thread to `TrialResult`. These are sample limitations of the upstream telemetry, not metric bugs; the synthetic tests exercise the non-zero paths.
- The parallel-speedup `MetricResult` reports `ciLow = ciHigh = value` because no closed-form interval is defensible for the inter-trial speedup ratio; this is honest by the module docstring rather than fabricating a bound.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: DONE
CONFIDENCE: high
SUMMARY: All four obligations SATISFIED with direct evidence (24/24 cost-robustness known-answer tests pass, full check.sh green at 237/5-skipped, rendered demo shows six MetricResults per arm with intervals on the pinned `dollars` basis, GateEvent/Telemetry resolutions trace cleanly); regression check PRESERVED (driver/outcome/domain unchanged in diff, no new deps); cost-basis Open question resolved in both code and task file.
