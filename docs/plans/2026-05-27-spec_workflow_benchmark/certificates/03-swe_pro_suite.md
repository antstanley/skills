# Done Certificate — Task 03: SWE-bench Pro suite

**Task:** [03-swe_pro_suite.md](../03-swe_pro_suite.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-05-27 — unverified

> This certificate is a verification protocol for Task 03. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 03) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** The SWE-bench Pro public instances are ingested as validated `TaskInstance` records in `suites/swe-bench-pro-public/instances.jsonl`.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Must use the Task 02 `TaskInstance` type and its schema validation; the seed subset is consumed by Tasks 04, 05, 07.

## Obligations

- **O1 — `instances.jsonl` loads as validated records and the seed subset is identifiable.**
  - *Claim:* every row loads as a `TaskInstance`, validates against the schema, and a ≈5-instance seed subset is tagged.
  - *Evidence to collect:* run the suite-load test — expect all rows validate; confirm the seed subset is selectable by its tag and has ≈5 members.
  - *Checks:* resolve the field mapping — confirm `failToPass`/`passToPass` hold selectors (not test bodies), `dockerImage` holds a `jefzda/sweap-images` tag, and `contaminationTier == "public"`.
  - *Status:* ☐ unverified

- **O2 — No hidden test content is materialised into the run-side records.**
  - *Claim:* records carry only test selectors and image tags, never hidden test source.
  - *Evidence to collect:* grep `instances.jsonl` for test-body content; confirm only selector strings and tags are present. Run the test asserting `goldPatch` and selectors are populated but no test source is inlined.
  - *Status:* ☐ unverified

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* ☐ unverified

- **O4 — Reviewable: load the suite, list the seed, confirm image tags and selectors.**
  - *Claim:* a reviewer loads the suite, lists the seed instances, and sees each carries a `dockerImage` tag and `failToPass`/`passToPass` selectors.
  - *Evidence to collect:* load the suite and print the seed instances with their image tags and selector counts.
  - *Status:* ☐ unverified

## Regression check

- Task 02's `TaskInstance` validation is the load path. Trace one `instances.jsonl` row through `TaskInstance` construction → expect it validates with no schema change required : ☐ (PRESERVED / REGRESSION)

## Residue

- Full suite size beyond the seed is an Open question (suite sizing / power analysis); not an obligation here.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐
