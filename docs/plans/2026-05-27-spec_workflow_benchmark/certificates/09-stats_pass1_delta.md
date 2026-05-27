# Done Certificate — Task 09: Stats — Pass@1 and the A1−A0 delta

**Task:** [09-stats_pass1_delta.md](../09-stats_pass1_delta.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-05-27 — unverified

> This certificate is a verification protocol for Task 09. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 09) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** The A0-vs-A1 ablation table — per-arm %Resolved with binomial CIs and Pass@k, and the A1−A0 paired McNemar delta.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Consumes Task 07/08 `ScoreReport`s; must not modify the score reports, only aggregate them.

## Obligations

- **O1 — The table reports A0 and A1 metrics with CIs, Pass@k, regression rate, and the McNemar delta.**
  - *Claim:* per-arm %Resolved (Pass@1) with 95% binomial CIs, Pass@k, regression rate, and the A1−A0 paired McNemar delta are all rendered on the seed instances.
  - *Evidence to collect:* run the stats over the seed campaign; read the table — expect all named columns and the delta row present.
  - *Checks:* resolve the McNemar computation to operate on *paired* instances (discordant pairs), not on independent proportions; confirm the binomial CI uses the trial count `n`.
  - *Status:* ☐ unverified

- **O2 — The statistics are verified against synthetic inputs with known answers.**
  - *Claim:* CI, Pass@k, and McNemar return the expected values on synthetic score reports with hand-computed answers.
  - *Evidence to collect:* run the synthetic-input tests → expect each statistic matches its hand-computed value.
  - *Status:* ☐ unverified

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* ☐ unverified

- **O4 — Reviewable: read the A0-vs-A1 table; confirm delta and intervals against a re-run. (M2 capstone.)**
  - *Claim:* a reviewer reads the A0-vs-A1 table and confirms the delta and intervals against a re-run within their stated bounds.
  - *Evidence to collect:* render the table; re-run the campaign and confirm the second table's values fall within the first's intervals.
  - *Status:* ☐ unverified

## Regression check

No existing callers — stats is a new leaf consuming score reports. Confirm Task 07/08 score reports load into the stats layer unchanged : ☐ (PRESERVED / REGRESSION)

## Residue

- Cost-matched %Resolved, conformance, and gate metrics are added to the report in Tasks 15/13/14 and assembled in Task 16; this task is the outcome columns and the A1−A0 delta only.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐
