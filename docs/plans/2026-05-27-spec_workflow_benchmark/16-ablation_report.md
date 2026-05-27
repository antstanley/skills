# Task 16 — Ablation report

**Plan:** [plan.md](plan.md) · **Status:** Todo · **Certificate:** [certificates/16-ablation_report.md](certificates/16-ablation_report.md)

**Implements:** [06-scoring-and-statistics.md](../../benchmark/specs/06-scoring-and-statistics.md) §Reporting; [02-arms.md](../../benchmark/specs/02-arms.md) §The pairwise deltas
**Depends on:** 09, 13, 14, 15
**Produces:** the full ablation table — every metric column for all five arms and the four pairwise-delta rows (A1−A0, A1−A2, A2−A3, A1−A4) with their McNemar results
**Pointers:** `benchmark/harness/stats/` (report render)

## Steps

- [ ] Assemble every metric (outcome, cost-matched, conformance, gate efficacy, robustness) into one table, one row per arm, each cell a value with its 95% interval.
- [ ] Compute and call out the four pairwise-delta rows with their McNemar results.
- [ ] Apply (or justify omitting) a multiple-comparison correction across the four deltas (resolve the Open question).
- [ ] Render the table to a shareable artifact for a campaign.
- [ ] Add a test that the report includes all five arms, all metric columns, and the four delta rows, and that absent metrics (e.g. conformance for A0 on SWE-bench Pro) are shown as not-applicable rather than zero.

## Definition of done

- [ ] The report renders the full ablation table with all metric columns, all five arms, and the four pairwise-delta rows with McNemar results.
- [ ] Multiple-comparison handling is applied or its omission is justified; not-applicable cells are distinguished from zero.
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer reads the complete ablation table for a campaign and can trace each delta to its arms. **(M4 capstone.)**

## Open questions

- Whether to apply a multiple-comparison correction across the four deltas, and which.
