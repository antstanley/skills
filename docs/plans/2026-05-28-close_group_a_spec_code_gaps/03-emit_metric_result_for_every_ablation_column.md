# Task 03 — Emit a `MetricResult` for every ablation column

**Plan:** [plan.md](plan.md) · **Status:** Todo

**Implements:** [04-metrics.md](../../benchmark/specs/04-metrics.md) §Implementation layout — "Each metric is a named `MetricResult` keyed by (campaign, arm, suite, metricName), carrying value and a 95% interval."
**Depends on:** 01 (data — the `gate_escape_rate` column reads `ScoreReport.gateEscape` once populated), 02 (review — the `parallel_speedup` column is honestly emittable only once intra-trial timing is captured)
**Produces:** a single emitter `ablation_metric_results(run, *, suite, …)` in `benchmark/harness/stats/ablation_report.py` returns the full sixteen `MetricResult` records per arm — every column the ablation table renders — alongside the existing six emitted from `cost_robustness_metric_results`; a test asserts every `METRIC_COLUMNS` entry appears as a schema-valid `MetricResult` whose `value`/`ciLow`/`ciHigh` agree with the matching `ArmRow` cell.
**Pointers:** `benchmark/harness/stats/ablation_report.py:185` (`METRIC_COLUMNS`); `benchmark/harness/stats/ablation_report.py:219` (`APPLICABILITY`); `benchmark/harness/stats/cost_robustness.py:132` (`COST_ROBUSTNESS_METRIC_NAMES`); `benchmark/harness/stats/cost_robustness.py:514` (`cost_robustness_metric_results`, the partial emitter to extend or wrap); `benchmark/harness/domain.py:442` (`MetricResult`).

## Steps

- [ ] Audit `METRIC_COLUMNS` (16 entries) against `COST_ROBUSTNESS_METRIC_NAMES` (6 entries) and the per-arm `ArmRow` dataclass. Confirm the ten missing names: `pass_at_1`, `pass_at_k`, `mean_tokens`, `mean_cost_usd`, `mean_wall_clock_seconds`, `conformance`, `plan_coverage`, `dag_validity`, `gate_catch_rate`, `gate_escape_rate`. (Document this set as a named constant `OUTCOME_AND_ARTIFACT_METRIC_NAMES` next to `COST_ROBUSTNESS_METRIC_NAMES` so the universe is auditable.)
- [ ] Add per-metric emitters for the ten that lack one, modelled on the existing `cost_robustness.py` helpers. Each emitter takes `(run, arm, suite)` and returns one `MetricResult` with `value`/`ciLow`/`ciHigh`. Reuse the per-column value/interval each `ArmRow` already computes; do not re-derive — the `ArmRow` value is the source of truth, and the new `MetricResult` is its serialised form.
- [ ] Respect `APPLICABILITY` (`benchmark/harness/stats/ablation_report.py:219`): when a metric does not apply to an arm (gate metrics on A0/A4; plan coverage / DAG validity on A0/A4), emit **no** `MetricResult` for that (arm, metric) — do not emit a zero with a wide CI. The `N/A` cells stay `N/A` in the `MetricResult` stream the same way they render in the Markdown table.
- [ ] Add a single top-level emitter `ablation_metric_results(run, *, suite, …)` that calls `cost_robustness_metric_results` plus the new ten emitters and returns the concatenated `list[MetricResult]`. Export it from `benchmark/harness/stats/__init__.py`. Keep `cost_robustness_metric_results` as a stable lower-level entry point — it is already imported by external callers — and document `ablation_metric_results` as the canonical surface for the universal claim.
- [ ] Tests (`benchmark/tests/test_ablation_metric_results.py`): assemble a synthetic five-arm `CampaignRun` and call `ablation_metric_results`; assert (a) every `metricName` in `METRIC_COLUMNS` × applicable arms appears once and only once; (b) each emitted `MetricResult` is schema-valid; (c) `value`/`ciLow`/`ciHigh` agree with the `ArmRow` cell to a tight tolerance (the two paths share the same Wilson/normal-CI math, so the agreement should be exact for finite n); (d) for A0/A4, `gate_catch_rate` / `gate_escape_rate` / `plan_coverage` / `dag_validity` are absent from the stream — not emitted as zero.
- [ ] Negative-space: an arm with zero scored trials yields no rows in the stream for any metric (not zero-valued rows with `nTrials = 0`); the renderer's "no trials" path is the right home for that case, not the metric stream.

## Definition of done

- [ ] `ablation_metric_results` returns the full set of `MetricResult`s for an (Arm, Suite) — every applicable column in `METRIC_COLUMNS` is present; non-applicable columns are absent.
- [ ] Each emitted record is schema-valid against `canonical-types.schema.json` `MetricResult` `$def`; the fields `value`/`ciLow`/`ciHigh` match the `ArmRow` cell the renderer would print.
- [ ] Negative-space: zero-trial arms emit no rows; non-applicable metrics emit no rows; both invariants are tested.
- [ ] The existing `cost_robustness_metric_results` entry point is unchanged in behaviour — `ablation_metric_results` calls it and extends the result.
- [ ] Meets the repo definition of done (uv-locked deps, ruff format + lint clean, pyright clean, pytest clean — see `plan.md` baseline).
- [ ] Reviewable: a reviewer runs the test suite, then renders the ablation report and the new metric stream on a synthetic five-arm campaign and confirms the two views agree column-for-column.

## Open questions

- *Naming for the new top-level emitter.* `ablation_metric_results` reads as "everything the ablation table holds, in `MetricResult` form". An alternative `all_metric_results` is shorter but loses the cross-link to the ablation surface. Pick during implementation; document the chosen name in `__all__`.
