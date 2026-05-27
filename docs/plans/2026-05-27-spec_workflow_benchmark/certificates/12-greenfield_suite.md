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

- **P1 — Goal.** The greenfield instances and the two-image build (run image with hidden tests excluded, scoring image with them included), plus a private reference solution for a self-test instance — the data and images the container backends (Tasks 04, 05) provision against. Greenfield is the sole ablation suite.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Uses Task 02 `TaskInstance`; the container scorer (Task 04) and runner (Task 05) depend on this task, not the reverse; the integrity rule (hidden tests off the run side) must hold by construction in the two-image split.

## Obligations

- **O1 — Greenfield instances validate; hidden tests absent from run image, present in scoring image.**
  - *Claim:* the greenfield instances load as validated `TaskInstance` records (`goldPatch: null`, `contaminationTier: authored-private`), and a test asserts the run image has no hidden tests while the scoring image does.
  - *Evidence to collect:* load the suite → expect validated `TaskInstance` records; run the two-image test → expect run image clean, scoring image carries the hidden suite.
  - *Checks:* confirm the run image build excludes the test layer; confirm each row validates against the Task 02 canonical schema.
  - *Status:* ☐ unverified

- **O2 — Seed instances are multi-component, carry `testTags`, and one ships a private reference solution.**
  - *Claim:* each seed instance's spec names several dependent components and `testTags` maps hidden tests to spec sections; at least one self-test instance ships a private reference solution in the suite directory, not in the arms-visible `goldPatch` field.
  - *Evidence to collect:* read a seed instance's spec seed → expect ≥2 dependent components; read its `testTags` → expect a test→section mapping; locate the self-test instance's reference solution and confirm it is outside the `goldPatch` field (which stays `null`).
  - *Status:* ☐ unverified

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline); instances validate against the schema.
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean; confirm greenfield instances validate as `TaskInstance` records.
  - *Status:* ☐ unverified

- **O4 — Reviewable: load the suite; confirm run image hidden-test-free and scoring image with them; locate the self-test reference solution.**
  - *Claim:* a reviewer loads the suite, lists the seed instances, confirms the run image carries no hidden tests while the scoring image does, and locates the self-test instance's private reference solution.
  - *Evidence to collect:* list the instances; inspect the run and scoring images for the hidden suite; open the self-test instance's reference solution.
  - *Status:* ☐ unverified

## Regression check

- No existing callers — the suite's data and images are consumed by the container backends (Tasks 04, 05), built later. Confirm the new greenfield instances validate against the Task 02 schema without changing it : ☐ (PRESERVED / REGRESSION)

## Residue

- Seed count vs usable interval width is a task Open question (shared with plan.md suite sizing); not an obligation here.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐
