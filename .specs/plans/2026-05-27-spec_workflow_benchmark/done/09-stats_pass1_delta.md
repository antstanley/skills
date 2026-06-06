# Task 09 — Stats: Pass@1 and the A1−A0 delta

**Plan:** [plan.md](../plan.md) · **Certificate:** [09-stats_pass1_delta-certificate.md](09-stats_pass1_delta-certificate.md)

**Implements:** [06-scoring-and-statistics.md](../../../benchmark/specs/06-scoring-and-statistics.md) §Repetition and Pass@k, §Confidence intervals and pairwise tests, §Reporting; [04-metrics.md](../../../benchmark/specs/04-metrics.md) §Bucket 1 — Outcome
**Depends on:** 07, 08
**Produces:** the A0-vs-A1 ablation table — per-arm %Resolved with binomial CIs and Pass@k, and the A1−A0 paired McNemar delta
**Pointers:** `benchmark/harness/stats/`

## Steps

- [x] Compute per-arm %Resolved (Pass@1) and Pass@k over `trialsPerInstance` from the score reports, with 95% binomial confidence intervals. *(`stats/outcome.py`: Pass@1 mean-over-trials, Pass@k any-over-instance, Wilson 95% CI; `failed` trials excluded via `CampaignRun.scored_results`.)*
- [x] Compute the A1−A0 delta on paired instances using McNemar's test on the discordant pairs. *(`mcnemar_delta`: continuity-corrected χ² + exact two-sided binomial p when b+c ≤ 25; per-instance pairing = resolved-by-any-trial.)*
- [x] Compute the regression rate per arm. *(`regression_rate`, with a Wilson CI.)*
- [x] Render a two-arm ablation table (A0, A1) with the metric columns and the A1−A0 delta row. *(`ablation_table` → `AblationTable`; `render_ablation_table` → Markdown; delta row labels exact-binomial vs chi-square_1.)*
- [x] Add tests on synthetic score reports with known outcomes that the CI, Pass@k, and McNemar computations return the expected values. *(`test_stats.py`: Wilson 0/10·5/10·10/10, Pass@1≠Pass@k, McNemar b=8/c=2 → χ²=2.5, exact p=0.109375, b+c=0 edge, failed-excluded.)*

## Definition of done

- [ ] The ablation table reports A0 and A1 %Resolved with binomial CIs, Pass@k, regression rate, and the McNemar A1−A0 delta, on the seed instances.
- [ ] The statistics are verified against synthetic inputs with known answers.
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer reads the A0-vs-A1 table and confirms the delta and intervals against a re-run within their stated bounds. **(M2 capstone.)**
