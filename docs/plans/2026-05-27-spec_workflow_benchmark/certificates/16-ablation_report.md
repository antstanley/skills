# Done Certificate — Task 16: Ablation report

**Task:** [16-ablation_report.md](../16-ablation_report.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-05-27 — unverified

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
  - *Status:* ☐ unverified

- **O2 — Multiple-comparison handling is applied or justified; not-applicable cells are distinguished from zero.**
  - *Claim:* a multiple-comparison correction across the four deltas is applied or its omission justified, and cells like the gate metrics for A0/A4 (which run no gates) render as not-applicable, not zero.
  - *Evidence to collect:* read the report's multiple-comparison note; run the test asserting an N/A cell is rendered distinctly from a `0.0` value.
  - *Status:* ☐ unverified

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* ☐ unverified

- **O4 — Reviewable: read the complete ablation table; trace each delta to its arms. (M4 capstone.)**
  - *Claim:* a reviewer reads the complete ablation table for a campaign and can trace each delta to its arms.
  - *Evidence to collect:* render the table; for each delta row, confirm the two arms it derives from are identifiable and present.
  - *Status:* ☐ unverified

## Regression check

- Tasks 09/13/14/15 produce the metric values. Trace one metric (e.g. A1 %Resolved) from its `MetricResult` into the report cell → expect the report shows the same value and interval, unmodified : ☐ (PRESERVED / REGRESSION)

## Residue

- Multiple-comparison correction choice is a task Open question; the validator notes which was applied.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐
