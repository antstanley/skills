# Task 03 — Emit a `MetricResult` for every ablation column

**Plan:** [plan.md](../plan.md)

**Implements:** [04-metrics.md](../../../benchmark/specs/04-metrics.md) §Implementation layout — "Each metric is a named `MetricResult` keyed by (campaign, arm, suite, metricName), carrying value and a 95% interval."
**Depends on:** 01 (data — the `gate_escape_rate` column reads `ScoreReport.gateEscape` once populated), 02 (review — the `parallel_speedup` column is honestly emittable only once intra-trial timing is captured)
**Produces:** a single emitter `ablation_metric_results(run, *, suite, …)` in `benchmark/harness/stats/ablation_report.py` returns the full sixteen `MetricResult` records per arm — every column the ablation table renders — alongside the existing six emitted from `cost_robustness_metric_results`; a test asserts every `METRIC_COLUMNS` entry appears as a schema-valid `MetricResult` whose `value`/`ciLow`/`ciHigh` agree with the matching `ArmRow` cell.
**Pointers:** `benchmark/harness/stats/ablation_report.py:185` (`METRIC_COLUMNS`); `benchmark/harness/stats/ablation_report.py:219` (`APPLICABILITY`); `benchmark/harness/stats/cost_robustness.py:132` (`COST_ROBUSTNESS_METRIC_NAMES`); `benchmark/harness/stats/cost_robustness.py:514` (`cost_robustness_metric_results`, the partial emitter to extend or wrap); `benchmark/harness/domain.py:442` (`MetricResult`).

## Steps

- [x] Audit `METRIC_COLUMNS` (16 entries) against `COST_ROBUSTNESS_METRIC_NAMES` (6 entries) and the per-arm `ArmRow` dataclass. Confirm the ten missing names: `pass_at_1`, `pass_at_k`, `mean_tokens`, `mean_cost_usd`, `mean_wall_clock_seconds`, `conformance`, `plan_coverage`, `dag_validity`, `gate_catch_rate`, `gate_escape_rate`. Documented as `OUTCOME_AND_ARTIFACT_METRIC_NAMES`.
- [x] Add per-metric emitters for the ten that lack one, modelled on the existing `cost_robustness.py` helpers. Each emitter takes `(run, arm, suite)` and returns one `MetricResult` with `value`/`ciLow`/`ciHigh`. ArmRow is the source of truth — no re-derivation.
- [x] Respect `APPLICABILITY`: non-applicable (arm, metric) pairs emit nothing — encoded via the `_emit_ci`/`_emit_scalar` helpers returning `None` when the ArmRow field is `None`.
- [x] Add a single top-level emitter `ablation_metric_results(run, *, suite, …)` that calls `cost_robustness_metric_results` plus the new ten emitters; exported from `benchmark/harness/stats/__init__.py`. Shared `budget` is threaded so the two paths cannot diverge on cost-matched %Resolved.
- [x] Tests (`benchmark/tests/test_ablation_metric_results.py`): 9 tests — universe completeness, the 6+10=16 decomposition, schema validity, exact value/CI agreement with `ArmRow` (math.isclose abs_tol=1e-9), absent-vs-zero distinction, zero-trial absence, empty-run absence, and the extends-cost-robustness composition.
- [x] Negative-space: zero-trial arms yield no rows. `test_arm_with_zero_scored_trials_emits_no_rows` and `test_empty_run_emits_no_rows`.

## Definition of done

- [x] `ablation_metric_results` returns the full set of `MetricResult`s for an (Arm, Suite) — every applicable column in `METRIC_COLUMNS` is present; non-applicable columns are absent.
- [x] Each emitted record is schema-valid against `canonical-types.schema.json` `MetricResult` `$def`; the fields `value`/`ciLow`/`ciHigh` match the `ArmRow` cell the renderer would print (exact for finite n).
- [x] Negative-space: zero-trial arms emit no rows; non-applicable metrics emit no rows; both invariants are tested.
- [x] The existing `cost_robustness_metric_results` entry point is unchanged in behaviour — `ablation_metric_results` calls it and extends the result.
- [x] Meets the repo definition of done — `bash scripts/check.sh` GREEN at 314 passed / 6 skipped.
- [x] Reviewable: `test_metric_result_values_agree_with_arm_row` proves the two views agree column-for-column on a synthetic five-arm campaign.

## Gate verdicts

- **Gate 1 — semi-formal review:** `VERDICT: CORRECT` / `CONFIDENCE: high`. Emitters read straight off `ArmRow` (no re-derivation); shared budget threaded so the table and stream cannot diverge on cost-matched %Resolved; APPLICABILITY encoded as ArmRow-field-is-None → emitter returns None → row absent.
- **Gate 2 — validate done:** `VERDICT: DONE` / `CONFIDENCE: high`. All 6 obligations SATISFIED; no UNVERIFIED items (fully discharge-able in-workspace).

## Open questions

- *Naming for the new top-level emitter.* `ablation_metric_results` reads as "everything the ablation table holds, in `MetricResult` form". An alternative `all_metric_results` is shorter but loses the cross-link to the ablation surface. Pick during implementation; document the chosen name in `__all__`.
