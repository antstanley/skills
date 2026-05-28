# Task 15 — Cost and robustness metrics

**Plan:** [plan.md](plan.md) · **Status:** Done · **Certificate:** [certificates/15-cost_robustness_metrics.md](certificates/15-cost_robustness_metrics.md)

**Implements:** [04-metrics.md](../../benchmark/specs/04-metrics.md) §Bucket 2 (cost-matched %Resolved, parallel speedup), §Bucket 4 — Robustness
**Depends on:** 06, 09, 10, 11
**Produces:** cost-matched %Resolved and parallel speedup, plus regression rate, merge-conflict rate, manual-pause rate, and gate-retry depth
**Pointers:** `benchmark/harness/stats/`; reads `ArtifactBundle.telemetry` and `GateEvent`s

## Steps

- [x] Compute cost-matched %Resolved by equalising the token/dollar/wall-clock budget across arms (fix the cost-matching basis first — resolve the Open question). *(Resolved: basis = dollars by default via `CostBasis` enum; equal-budget rule = `min over arms of max(per-trial cost)`; overshoots count against the arm. See Open questions.)*
- [x] Compute parallel speedup (A1 wall-clock vs sequential) and correlate it with task-graph width. *(`parallel_speedup_for_arm`: speedup = sum/max wall-clock intra-campaign; `graph_width` from `dag_validity` carried alongside.)*
- [x] Compute the robustness columns: merge-conflict rate, manual-pause (`UNVERIFIED`) rate, and mean gate-retry depth from `GateEvent`s. *(All with intervals: Wilson for fractions, Bessel-corrected normal-approx for the retry-depth mean.)*
- [x] Surface these as `MetricResult`s per (arm, suite) with intervals. *(`cost_robustness_metric_results(run, ...) → list[MetricResult]` — 6 metrics per arm, schema-valid.)*
- [x] Add tests on synthetic telemetry/gate inputs that cost-matching and the robustness rates compute as expected. *(`test_cost_robustness.py`: 24 hand-computed known-answer tests, all green; 237 total pass.)*

## Definition of done

- [ ] Cost-matched %Resolved, parallel speedup, and the four robustness metrics are produced per (arm, suite) with intervals, on a documented cost-matching basis.
- [ ] The computations are verified against synthetic inputs with known answers.
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer reads the cost-matched table and the robustness columns and confirms the cost basis is stated.

## Open questions

- Cost-matching basis (tokens, dollars, or wall-clock) must be fixed before the cost-matched delta is reported.
  - **Resolved (2026-05-28):** Pinned headline basis is **dollars** (`Telemetry.costUsd`) — the spec text in `04-metrics.md` §Bucket 2 says "token (or dollar) budget" and `costUsd` is the most directly comparable unit across arms ("the same spend"). Tokens (`inputTokens + outputTokens`) and wall-clock (`wallClockSeconds`) are selectable via the `CostBasis` enum for ablation reports that want to factor out per-model pricing or compare at fixed time. The equal-budget rule used: `B = min over arms of max(per-trial cost)`, then `cost_matched_pass_at_1(arm, B) = |{ trial : cost ≤ B AND resolved }| / n_scored` with a Wilson 95% interval — "of the trials I ran, how many resolved within budget B". Documented in `benchmark/harness/stats/cost_robustness.py`'s module docstring.
