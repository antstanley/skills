# Done Certificate — Task 16: Ablation report

**Task:** [16-ablation_report.md](../16-ablation_report.md) · **Plan:** [plan.md](../plan.md)
**State:** Validated 2026-05-28

> This certificate is a verification protocol for Task 16. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 16) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** The full ablation table — every metric column for all five arms and the four pairwise-delta rows (A1−A0, A1−A2, A2−A3, A1−A4) with their McNemar results.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Assembles Task 09/13/14/15 outputs; must not recompute or alter the underlying metric values, only present them.

## Obligations

- **O1 — The report renders the full table: all metric columns, all five arms, four delta rows with McNemar.**
  - *Claim:* one table, one row per arm (A0–A4), every metric column (outcome, cost-matched, conformance, gate efficacy, robustness), each cell a value with its 95% interval, plus the four pairwise-delta rows with McNemar results.
  - *Evidence to collect:* render the report for a campaign; confirm five arm rows, all metric columns, and the four delta rows are present with intervals and McNemar results.
  - *Checks:* resolve each column's source to the owning task's `MetricResult`s (09 outcome, 13 conformance, 14 gate/coverage, 15 cost/robustness); confirm no recomputation, only assembly.
  - *Evidence collected:* `ABLATION_ARMS` is the closed five-arm tuple (`ablation_report.py:106`); `build_ablation_report` emits one `ArmRow` per arm in that order (`ablation_report.py:678–692`); `METRIC_COLUMNS` enumerates the 16 metric columns spanning outcome / cost-matched / efficiency / conformance / plan / gate / robustness (`ablation_report.py:185–202`); `PAIRWISE_DELTAS` carries the four planned comparisons A1−A0, A1−A2, A2−A3, A1−A4 (`ablation_report.py:111–136`) and `build_ablation_report` produces a `DeltaRow` per entry, each carrying a `McNemarResult` (`ablation_report.py:694–701`). Renderer emits header + arm rows + four `Delta {label}` lines (`ablation_report.py:826–889`). `test_report_includes_all_five_arms`, `test_report_metric_columns_complete`, `test_report_has_four_delta_rows_with_correct_arm_pairs`, `test_delta_rows_carry_mcnemar_and_adjusted_p`, `test_render_includes_every_arm_row`, `test_render_includes_every_delta_label` all pass.
  - *Resolution check:* every metric is sourced from upstream task functions — `arm_outcome` / `mcnemar_delta` (Task 09 outcome at `outcome.py`), `_conformance_ci_for_arm` reads `ScoreReport.conformanceScore` produced by Task 13, `plan_coverage` / `dag_validity` (Task 14 `artifact_metrics.py`), `cost_matched_resolved_for_arm` / `parallel_speedup_for_arm` / `merge_conflict_rate` / `manual_pause_rate` / `gate_retry_depth_for_arm` (Task 15 `cost_robustness.py`). The module imports each function (`ablation_report.py:59–92`); the only fresh arithmetic in `build_arm_row` is summing telemetry into `_telemetry_means` (a presentation aggregate, not a metric redefinition) and the Holm-Bonferroni adjustment over already-computed McNemar p-values. No metric value is recomputed.
  - *Status:* SATISFIED

- **O2 — Multiple-comparison handling is applied or justified; not-applicable cells are distinguished from zero.**
  - *Claim:* a multiple-comparison correction across the four deltas is applied or its omission justified, and cells like the gate metrics for A0/A4 (which run no gates) render as not-applicable, not zero.
  - *Evidence to collect:* read the report's multiple-comparison note; run the test asserting an N/A cell is rendered distinctly from a `0.0` value.
  - *Evidence collected:* (a) Holm-Bonferroni step-down at α = 0.05 is PINNED with the rationale that FWER over four tests at α=0.05 is ≈0.185 (`ablation_report.py:21–46`); `HOLM_BONFERRONI_ALPHA = 0.05` is a named constant (`ablation_report.py:151`); `holm_bonferroni_adjusted_pvalues` implements the textbook procedure (`ablation_report.py:328–371`); `apply_holm_bonferroni` wraps the McNemar results into `DeltaRow`s with `adjusted_p` and `significant_at_alpha` (`ablation_report.py:374–401`); the renderer emits a `_Multiple-comparison correction: Holm-Bonferroni at α = 0.05_` preamble line and a per-row `Holm-Bonferroni adjusted p = ...` annotation (`ablation_report.py:866–878`, `826–838`). The textbook tests `test_holm_bonferroni_textbook_known_answer`, `test_holm_bonferroni_all_significant_textbook`, `test_holm_bonferroni_first_failure_stops_rejection`, `test_holm_bonferroni_clamps_at_one`, `test_holm_bonferroni_empty_and_single`, `test_holm_bonferroni_preserves_input_order_on_ties`, `test_apply_holm_bonferroni_attaches_significance_flag` all pass. (b) `APPLICABILITY` is the named (metric, arms) table (`ablation_report.py:219–236`); non-applicable cells are stored as `None` on `ArmRow` and rendered as `NA_RENDER_TOKEN = "N/A"` (`ablation_report.py:154–156`, `_cell_value` at `ablation_report.py:782–822`); `test_gate_metrics_zero_value_distinct_from_na` proves an A1 cell with (0, 5) catches renders `0.0%` while A0/A4 render `N/A` for the same column — the two are distinguished. Tests `test_gate_metrics_na_on_a0_and_a4`, `test_plan_metrics_na_on_a0_and_a4`, `test_cell_value_renders_na_token_for_non_applicable`, `test_render_includes_na_token` pass.
  - *Status:* SATISFIED

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Evidence collected:* `bash scripts/check.sh` in `/home/ec2-user/code/skills-task-16` reports: `uv sync` clean (33 packages, no changes), `ruff format --check` 87 files already formatted, `ruff check` all checks passed, `pyright` 0 errors / 0 warnings / 0 informations, `pytest` 262 passed and 5 skipped (the 5 skips are pre-existing opt-in live tests gated on `BENCHMARK_RUN_*_LIVE=1`, unrelated to this task). `jj diff --stat` confirms NO new deps — only `benchmark/harness/stats/__init__.py`, `benchmark/harness/stats/ablation_report.py`, `benchmark/tests/test_ablation_report.py`, and the task file changed; `pyproject.toml` and `uv.lock` untouched. Named-constant limits are exhaustive: `ABLATION_ARMS`, `PAIRWISE_DELTAS`, `PLAN_PRODUCING_ARMS`, `GATED_ARMS`, `HOLM_BONFERRONI_ALPHA`, `NA_RENDER_TOKEN`, `METRIC_COLUMNS`, `APPLICABILITY`, plus reused `CONFIDENCE_LEVEL` / `WILSON_Z_95` from `outcome.py` (`ablation_report.py:101–236`).
  - *Status:* SATISFIED

- **O4 — Reviewable: read the complete ablation table; trace each delta to its arms. (M4 capstone.)**
  - *Claim:* a reviewer reads the complete ablation table for a campaign and can trace each delta to its arms.
  - *Evidence to collect:* render the table; for each delta row, confirm the two arms it derives from are identifiable and present.
  - *Evidence collected:* the structured API `DeltaRow` carries explicit `treatment`, `baseline`, `label` fields (`ablation_report.py:286–303`), so a programmatic consumer reaches the two arms by attribute. The renderer emits the label in the form `A1−A0` / `A1−A2` / `A2−A3` / `A1−A4` (`PAIRWISE_DELTAS` at `ablation_report.py:111–136`), and the test `test_render_includes_every_delta_label` confirms each appears in the rendered Markdown. The five arm rows precede the delta block in the same table (`render_ablation_report` at `ablation_report.py:841–889`), so both arms named in any delta label are present as rows above it. `test_delta_a1_minus_a0_uses_correct_arms` and `test_delta_a2_minus_a3_uses_correct_arms` exercise the routing end-to-end against the real driver types: the synthetic A0/A2 outcomes drive McNemar (b, c, n_pairs) to the expected discordant counts (A1−A0: b=0, c=1; A2−A3: b=1, c=1), proving the delta is computed from exactly the arms its label names — fully traceable.
  - *Status:* SATISFIED

## Regression check

- Tasks 09/13/14/15 produce the metric values. Trace one metric (e.g. A1 %Resolved) from its `MetricResult` into the report cell → expect the report shows the same value and interval, unmodified : PRESERVED. `build_arm_row` calls `arm_outcome(run, arm)` (Task 09 in `outcome.py`) once and reads `outcome.pass_at_1`, `outcome.pass_at_k`, `outcome.regression_rate`, `outcome.n_instances` straight through into the `ArmRow` (`ablation_report.py:544`, `598–604`). The renderer's `_cell_value` for `METRIC_PASS_AT_1` just formats `row.pass_at_1` (`ablation_report.py:790–791`); no arithmetic touches the value. Same pattern for the Task 13 conformance scores (read off `ScoreReport.conformanceScore`), Task 14 plan-coverage/DAG-validity (delegated to the imported functions), and Task 15 cost/robustness (delegated). The McNemar deltas reuse `mcnemar_delta` from `outcome.py` (`ablation_report.py:698`); Holm-Bonferroni only adjusts the p-value family, leaving the raw `McNemarResult` (b, c, n_pairs, delta, statistic, p_value) preserved on every `DeltaRow.mcnemar`. The 262-test suite passes — no upstream computation was modified.

## Residue

- Multiple-comparison correction choice is a task Open question; the validator notes which was applied.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: DONE
CONFIDENCE: high
SUMMARY: All four obligations are SATISFIED with named evidence and the regression trace is PRESERVED — the five-arm × 16-metric ablation table plus the four pairwise-delta rows (A1−A0, A1−A2, A2−A3, A1−A4) are assembled from upstream Task 09/13/14/15 functions without recomputation, Holm-Bonferroni at α = 0.05 is applied and tested against textbook expected values, N/A vs 0.0 is distinguished structurally (`None` on the dataclass, `N/A` token in the renderer, asserted by `test_gate_metrics_zero_value_distinct_from_na`), and `bash scripts/check.sh` is clean (262 passed; 5 skips are pre-existing opt-in live tests, no new deps).
