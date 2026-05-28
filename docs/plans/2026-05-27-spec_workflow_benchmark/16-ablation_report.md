# Task 16 — Ablation report

**Plan:** [plan.md](plan.md) · **Status:** Done · **Certificate:** [certificates/16-ablation_report.md](certificates/16-ablation_report.md)

**Implements:** [06-scoring-and-statistics.md](../../benchmark/specs/06-scoring-and-statistics.md) §Reporting; [02-arms.md](../../benchmark/specs/02-arms.md) §The pairwise deltas
**Depends on:** 09, 13, 14, 15
**Produces:** the full ablation table — every metric column for all five arms and the four pairwise-delta rows (A1−A0, A1−A2, A2−A3, A1−A4) with their McNemar results
**Pointers:** `benchmark/harness/stats/` (report render)

## Steps

- [x] Assemble every metric (outcome, cost-matched, conformance, gate efficacy, robustness) into one table, one row per arm, each cell a value with its 95% interval. *(`stats/ablation_report.py`: `build_ablation_report(...)` → `AblationReport` with 5 `ArmRow`s × 16 metric columns; Wilson intervals from the upstream tasks.)*
- [x] Compute and call out the four pairwise-delta rows with their McNemar results. *(`PAIRWISE_DELTAS = (A1−A0, A1−A2, A2−A3, A1−A4)`; each `DeltaRow` carries its `McNemarResult`.)*
- [x] Apply (or justify omitting) a multiple-comparison correction across the four deltas (resolve the Open question). *(Resolved: Holm-Bonferroni at α=0.05 — uniformly more powerful than plain Bonferroni at the same FWER; textbook-verified. See Open questions.)*
- [x] Render the table to a shareable artifact for a campaign. *(`render_ablation_report` → Markdown: cost-basis + correction headers, arm rows, then the four pairwise-delta bullets with adjusted p + significance.)*
- [x] Add a test that the report includes all five arms, all metric columns, and the four delta rows, and that absent metrics (e.g. the gate metrics for A0/A4, which run no gates, and plan coverage/DAG validity for A0/A4, which produce no plan) are shown as not-applicable rather than zero. *(`test_ablation_report.py`: 25 deterministic tests, incl. the `0.0% ≠ N/A` distinction; 262 total pass.)*

## Definition of done

- [ ] The report renders the full ablation table with all metric columns, all five arms, and the four pairwise-delta rows with McNemar results.
- [ ] Multiple-comparison handling is applied or its omission is justified; not-applicable cells are distinguished from zero.
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer reads the complete ablation table for a campaign and can trace each delta to its arms. **(M4 capstone.)**

## Open questions

- Whether to apply a multiple-comparison correction across the four deltas, and which.

  **Resolution (M4):** apply **Holm-Bonferroni** at α = 0.05 across the four pairwise deltas (A1−A0, A1−A2, A2−A3, A1−A4). With four planned comparisons the uncorrected family-wise error rate is roughly `1 - 0.95^4 ≈ 0.185`, so omitting a correction is not honest with this many tests. Holm-Bonferroni is the textbook step-down procedure (Holm 1979, *Scandinavian Journal of Statistics*): uniformly more powerful than plain Bonferroni at the same family-wise error rate, parameter-free, and valid under arbitrary dependence between the comparisons (which is what we have — the four deltas share arms). Each delta row carries the raw McNemar p-value, a Holm-Bonferroni-adjusted p-value, and a binary `significant_at_alpha` flag against α = 0.05. The named constant `HOLM_BONFERRONI_ALPHA` (in `benchmark/harness/stats/ablation_report.py`) is the configuration knob if a future campaign wants a different family-wise rate. See the module docstring for the full procedure + the textbook small-example test cases.
