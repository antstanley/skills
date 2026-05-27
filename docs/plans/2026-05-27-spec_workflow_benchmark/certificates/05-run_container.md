# Done Certificate — Task 05: Run container

**Task:** [05-run_container.md](../05-run_container.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-05-27 — unverified

> This certificate is a verification protocol for Task 05. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 05) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** A0 runs in a provisioned container against a `TaskInstance` and yields a `candidatePatch` plus a transcript captured into an `ArtifactBundle`.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Must consume Task 02 types and Task 03 instances; the run container must not introduce hidden tests (integrity rule on the run side).

## Obligations

- **O1 — An A0 run yields an apply-able patch and a bundle with the transcript.**
  - *Claim:* an A0 run on a seed instance produces a `candidatePatch` that applies cleanly against `baseCommit` and an `ArtifactBundle` carrying the transcript.
  - *Evidence to collect:* run A0 on a seed instance; apply the emitted patch to a fresh checkout at `baseCommit` → expect clean apply; confirm the `ArtifactBundle` has a non-empty transcript.
  - *Checks:* resolve the patch extraction to the diff of working state against `baseCommit`, not against the container's dirty HEAD; confirm `jj`/`git` are present in the container.
  - *Status:* ☐ unverified

- **O2 — The run container carries no hidden test content.**
  - *Claim:* the provisioned run image contains no `failToPass`/`passToPass` test material.
  - *Evidence to collect:* run the test that inspects the run container for hidden test files → expect none present.
  - *Status:* ☐ unverified

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* ☐ unverified

- **O4 — Reviewable: run A0 on one seed instance; inspect the patch and transcript.**
  - *Claim:* a reviewer runs A0 on one seed instance and inspects the emitted patch and transcript.
  - *Evidence to collect:* run A0 once; print the candidate patch and the transcript head.
  - *Status:* ☐ unverified

## Regression check

- Task 04's scorer consumes a `candidatePatch`. Trace one A0 patch through the scorer → expect it applies and scores without scorer changes : ☐ (PRESERVED / REGRESSION)

## Residue

- A1 and the other arms extend this provisioning in Tasks 08/10/11; this task is the A0 recipe only.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐
