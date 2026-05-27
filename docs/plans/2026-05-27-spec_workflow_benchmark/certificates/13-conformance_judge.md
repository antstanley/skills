# Done Certificate — Task 13: Conformance judge

**Task:** [13-conformance_judge.md](../13-conformance_judge.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-05-27 — unverified

> This certificate is a verification protocol for Task 13. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 13) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** A rubric-driven conformance score on `ScoreReport.conformanceScore`, with a stated human-label agreement figure.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Consumes Task 07 score reports, Task 08 spec artifacts, and Task 12 greenfield specs; writing `conformanceScore` must not alter `resolved`/`regressed`.

## Obligations

- **O1 — Conformance is scored for the right arm/suite combinations and null where no spec exists.**
  - *Claim:* every arm on greenfield (scored against the instance spec seed) and spec-bearing arms (A1, A2, A3) on SWE-bench Pro get a `conformanceScore` in `[0,1]`; A0/A4 on SWE-bench Pro get null.
  - *Evidence to collect:* run the judge over a mixed campaign; read `conformanceScore` per (arm, suite) → expect populated where a spec exists, null otherwise. Run the applicability test.
  - *Checks:* resolve the judging procedure to `spec-reviewer` R2/R3 where the spec-creator plugin is available, else the rubric directly; confirm greenfield scoring uses the instance's input spec seed.
  - *Status:* ☐ unverified

- **O2 — A human-label agreement figure is reported and meets the agreed threshold.**
  - *Claim:* the judge is calibrated against a human-labelled sample and the reported agreement meets the threshold set for reportability.
  - *Evidence to collect:* read the calibration output — the agreement figure and sample size; confirm it meets the agreed threshold (resolving the calibration Open question).
  - *Status:* ☐ unverified

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* ☐ unverified

- **O4 — Reviewable: read conformance across arms on a greenfield instance and the agreement figure.**
  - *Claim:* a reviewer reads conformance scores for a greenfield instance across arms and the agreement figure against human labels.
  - *Evidence to collect:* render conformance per arm for one greenfield instance; show the calibration agreement figure.
  - *Status:* ☐ unverified

## Regression check

- Task 07 score reports must keep their existing fields. Trace a score report after conformance is written → expect `resolved`/`regressed` unchanged, `conformanceScore` added : ☐ (PRESERVED / REGRESSION)

## Residue

- The calibration threshold is a task Open question; if unset at validation, O2 is UNVERIFIED.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐
