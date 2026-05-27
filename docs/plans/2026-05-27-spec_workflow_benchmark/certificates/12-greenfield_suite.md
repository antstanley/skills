# Done Certificate — Task 12: Greenfield suite

**Task:** [12-greenfield_suite.md](../12-greenfield_suite.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-05-27 — unverified

> This certificate is a verification protocol for Task 12. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 12) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** Greenfield instances that run through an arm and are scored by their hidden suites, with hidden tests baked only into the scoring image.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Uses Task 02 `TaskInstance` and extends Task 04's oracle with the `greenfield-hidden-tests` convention; the integrity rule (hidden tests off the run side) must hold.

## Obligations

- **O1 — A greenfield instance is scored by its hidden suite; hidden tests absent from run image, present in scoring image.**
  - *Claim:* an arm's output on a greenfield instance is scored against the withheld suite, and a test asserts the run image has no hidden tests while the scoring image does.
  - *Evidence to collect:* run an arm on a greenfield instance and score it → expect a `ScoreReport`; run the two-image test → expect run image clean, scoring image carries the hidden suite.
  - *Checks:* resolve the scoring path to the `greenfield-hidden-tests` oracle convention (Task 04), not the `swe-bench-pro` one; confirm the run image build excludes the test layer.
  - *Status:* ☐ unverified

- **O2 — Seed instances are multi-component and carry `testTags`.**
  - *Claim:* each seed instance's spec names several components with dependencies, and `testTags` maps hidden tests to spec sections/components.
  - *Evidence to collect:* read a seed instance's spec seed → expect ≥2 dependent components; read its `testTags` → expect a test→section mapping covering the hidden suite.
  - *Status:* ☐ unverified

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline); instances validate against the schema.
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean; confirm greenfield instances validate as `TaskInstance` records.
  - *Status:* ☐ unverified

- **O4 — Reviewable: run one arm on a greenfield instance; see it scored by the withheld suite; confirm run image has no hidden tests. (M3 capstone.)**
  - *Claim:* a reviewer runs one arm on a greenfield instance, sees it scored by the withheld suite, and confirms the run image carries no hidden tests.
  - *Evidence to collect:* run an arm once; print the `ScoreReport`; inspect the run image for absence of hidden tests.
  - *Status:* ☐ unverified

## Regression check

- Task 04's `swe-bench-pro` oracle convention must still work after the greenfield convention is added. Trace a SWE-bench Pro gold-patch scoring → expect it still resolves : ☐ (PRESERVED / REGRESSION)

## Residue

- Seed count vs usable interval width is a task Open question (shared with plan.md suite sizing); not an obligation here.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐
