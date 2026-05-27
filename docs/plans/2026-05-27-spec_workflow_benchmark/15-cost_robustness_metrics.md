# Task 15 — Cost and robustness metrics

**Plan:** [plan.md](plan.md) · **Status:** Todo · **Certificate:** [certificates/15-cost_robustness_metrics.md](certificates/15-cost_robustness_metrics.md)

**Implements:** [04-metrics.md](../../benchmark/specs/04-metrics.md) §Bucket 2 (cost-matched %Resolved, parallel speedup), §Bucket 4 — Robustness
**Depends on:** 06, 09, 10, 11
**Produces:** cost-matched %Resolved and parallel speedup, plus regression rate, merge-conflict rate, manual-pause rate, and gate-retry depth
**Pointers:** `benchmark/harness/stats/`; reads `ArtifactBundle.telemetry` and `GateEvent`s

## Steps

- [ ] Compute cost-matched %Resolved by equalising the token/dollar/wall-clock budget across arms (fix the cost-matching basis first — resolve the Open question).
- [ ] Compute parallel speedup (A1 wall-clock vs sequential) and correlate it with task-graph width.
- [ ] Compute the robustness columns: merge-conflict rate, manual-pause (`UNVERIFIED`) rate, and mean gate-retry depth from `GateEvent`s.
- [ ] Surface these as `MetricResult`s per (arm, suite) with intervals.
- [ ] Add tests on synthetic telemetry/gate inputs that cost-matching and the robustness rates compute as expected.

## Definition of done

- [ ] Cost-matched %Resolved, parallel speedup, and the four robustness metrics are produced per (arm, suite) with intervals, on a documented cost-matching basis.
- [ ] The computations are verified against synthetic inputs with known answers.
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer reads the cost-matched table and the robustness columns and confirms the cost basis is stated.

## Open questions

- Cost-matching basis (tokens, dollars, or wall-clock) must be fixed before the cost-matched delta is reported.
