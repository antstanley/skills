# Task 04 — Compute the cost-matched paired delta

**Plan:** [plan.md](../plan.md)

**Implements:** [06-scoring-and-statistics.md](../../../benchmark/specs/06-scoring-and-statistics.md) §Confidence intervals and pairwise tests — "Cost-matched delta. The same paired comparison after equalising the budget."
**Depends on:** 03 (build — reuses the per-arm MetricResult helpers and the `cost_matched_resolved_for_arm` machinery)
**Produces:** each of the four pairwise comparisons (A1−A0, A1−A2, A2−A3, A1−A4) produces a cost-matched McNemar delta alongside the raw delta — same arms, but the per-instance bool is `cost ≤ B AND resolved` at the shared equal budget. The cost-matched deltas surface in the rendered ablation report (a new bullet line per pairwise comparison) and as four additional `MetricResult` records emitted by `ablation_metric_results`. Holm-Bonferroni adjustment is applied across the *raw* deltas and the *cost-matched* deltas as two separate families (eight total, two families of four), preserving the spec's α = 0.05 family-wise rate per comparison.
**Pointers:** `benchmark/harness/stats/cost_robustness.py:224` (`equal_budget_for_arms`); `benchmark/harness/stats/cost_robustness.py:246` (`cost_matched_resolved_for_arm`); `benchmark/harness/stats/outcome.py:284` (`mcnemar_delta`); `benchmark/harness/stats/outcome.py:244` (`_instance_resolved_any`, the pairing-reduction rule); `benchmark/harness/stats/ablation_report.py:111` (`PAIRWISE_DELTAS`); `benchmark/harness/stats/ablation_report.py:328` (`holm_bonferroni_adjusted_pvalues`); `benchmark/harness/stats/ablation_report.py:648` (`build_ablation_report`).

## Steps

- [x] Add an `_arm_instance_cost_matched_resolved(run, arm, budget, basis)` helper to `benchmark/harness/stats/ablation_report.py` returning per-instance `cost(trial) ≤ budget AND resolved` via the `any`-over-trials rule.
- [x] In `build_ablation_report`, compute per-pair shared budget `B` via `equal_budget_for_arms` over only the two arms in the comparison (not all five) — the spec's two-arm reading.
- [x] Per comparison, compute a cost-matched `McNemarResult` by passing the cost-matched bool maps through the existing `mcnemar_delta` (delta, b, c, χ², raw p, exact/asymptotic label all flow through unchanged).
- [x] Wrap `apply_holm_bonferroni` with `apply_holm_bonferroni_per_family(raw_p, cm_p, alpha)` that runs `holm_bonferroni_adjusted_pvalues` independently on each family of four — the spec's per-comparison α = 0.05 reading. Documented in the wrapper docstring.
- [x] Extend `render_ablation_report` to add `### Cost-matched pairwise deltas` after `### Pairwise deltas`, naming cost basis in the preamble and printing `B={budget:.4f} {basis}` on each bullet.
- [x] Extend `ablation_metric_results` to emit four `cost_matched_delta__<label>` `MetricResult`s. Each carries the delta value; the Holm-adjusted significance flag is encoded via `ciLow`/`ciHigh`: **significant** at α → `ciLow == ciHigh == value` (degenerate point); **not significant** → `ciLow = min(value, 0)`, `ciHigh = max(value, 0)` (interval straddles zero). Both shapes satisfy the schema invariant `ciLow ≤ value ≤ ciHigh`. Documented in `cost_matched_delta_metric_result`'s docstring. Behaviour note: the MetricResult is omitted if either arm in the pair has no scored trials (matches task 03's universe rule); the in-memory `CostMatchedDeltaRow` is still produced for the rendered report.
- [x] Tests (`benchmark/tests/test_cost_matched_delta.py`): 14 tests covering the sign-flip scenario, per-pair budget uses only the two arms, two-families-of-four Holm separation, the rendered section contains both four-bullet sets with per-bullet `B`, schema validity, significance-flag encoding, negative-space (disjoint instances + un-sampled arm).

## Definition of done

- [x] Four cost-matched McNemar delta rows are computed alongside the existing four raw delta rows; each carries Δ%Resolved, χ², raw p, exact/asymptotic label, b/c, and a Holm-Bonferroni-adjusted p-value at α = 0.05.
- [x] The two delta families (raw and cost-matched) are adjusted **separately**.
- [x] The rendered ablation report carries a `### Cost-matched pairwise deltas` section beneath the existing `### Pairwise deltas`, naming the cost basis and per-comparison equal budget `B`.
- [x] `ablation_metric_results` returns four additional `MetricResult`s named `cost_matched_delta__<label>`; each is schema-valid.
- [x] Negative-space: an arm pair with no shared scored instances yields a cost-matched delta with `b = c = 0` and `delta = 0`, no divide-by-zero (reuses `mcnemar_delta`'s existing guarantee).
- [x] Repo definition of done: `bash scripts/check.sh` GREEN at 328 passed / 6 skipped. No schema delta.
- [x] Reviewable: test-suite half SATISFIED (synthetic five-arm fixture exercises the renderer); **UNVERIFIED** for the "saved live evidence" half because there is no saved five-arm `CampaignRun` on disk (only per-arm bundles under `_a1_live_evidence/` and `_a2_a3_live_evidence/`). User can manually exercise by assembling a five-arm run or by running a full live campaign across all five arms.

## Gate verdicts

- **Gate 1 — semi-formal review:** `VERDICT: LIKELY_CORRECT` / `CONFIDENCE: high`. All four deltas, the per-pair budget, the per-family Holm-Bonferroni, the rendered section, and the four MetricResults are produced correctly. The single flagged blemish — the `ciLow/ciHigh`-as-significance-flag encoding overloads the same shape `_emit_scalar` uses for "no closed-form CI" — is a documentation/readability concern, not a correctness bug.
- **Gate 2 — validate done:** `VERDICT: DONE` / `CONFIDENCE: high`. All 7 obligations SATISFIED; the live-evidence half of Reviewable is genuinely environment-bound (no saved five-arm campaign on disk), surfaced for user confirmation.

## Open questions

- *Significance-flag encoding overload.* The four `cost_matched_delta__*` MetricResults reuse the `ciLow == ciHigh == value` shape `_emit_scalar` uses for "no closed-form CI" to mean "Holm rejected H0 at α". Consumers reading the metric stream by `metricName` namespace can disambiguate; consumers reading `ciHigh - ciLow` as "uncertainty width" without checking `metricName` would be misled. A future schema delta could add an optional `significant` or `adjustedP` field on `MetricResult` to carry the flag explicitly; until then the per-record docstring is the contract. Also: for a delta of exactly 0.0, the two encodings collapse to `ciLow == ciHigh == 0`, indistinguishable; the test `test_cost_matched_delta_significance_flag_encoded_in_ci_bounds` covers non-zero deltas only.

## Open questions

- *Family for Holm-Bonferroni.* This task pins two families of four at α = 0.05 each (raw deltas; cost-matched deltas). The alternative — one family of eight — is statistically more conservative and would weaken every signal by a factor of two. The choice should be documented as a `Decision` on `06-scoring-and-statistics.md` if the user prefers the one-family reading; the code constant `HOLM_BONFERRONI_ALPHA` already lives there and can be left unchanged either way.
