# Done Certificate — Task 08: Arm A1 pipeline

**Task:** [08-arm_a1_pipeline.md](../08-arm_a1_pipeline.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-05-27 — unverified

> This certificate is a verification protocol for Task 08. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 08) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** A1 drives `spec-creator` → `spec-planner` → `spec-builder` end to end in a run container and is scored on SWE-bench Pro.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Extends Task 05 provisioning and runs through Task 07's driver and Task 04's oracle; must not regress the A0 path.

## Obligations

- **O1 — A1 runs to completion and yields an apply-able, scorable patch.**
  - *Claim:* A1 drives create→plan→build with both gates and yields a `candidatePatch` that applies against `baseCommit` and scores through the oracle on the seed instances.
  - *Evidence to collect:* run A1 on a seed instance; apply the patch at `baseCommit` → expect clean apply; score it → expect a `ScoreReport`.
  - *Checks:* resolve the candidate-patch source to the diff of `spec-builder`'s integration tip against `baseCommit`; confirm the three plugins are installed and driven non-interactively.
  - *Status:* ☐ unverified

- **O2 — The patch excludes workflow artifacts; spec/plan/certificate/gate-event records are captured.**
  - *Claim:* the `candidatePatch` contains no plan/spec/cert files, and the `ArtifactBundle` holds `specArtifacts`, `planArtifacts`, `certificateArtifacts`, and `GateEvent`s.
  - *Evidence to collect:* grep the patch for `docs/plans`/`docs/specs`/`certificates` paths → expect none; read the `ArtifactBundle` → expect the artifact lists and gate events populated.
  - *Status:* ☐ unverified

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* ☐ unverified

- **O4 — Reviewable: run A1 on one seed instance; inspect integration-tip patch, artifacts, score.**
  - *Claim:* a reviewer runs A1 on one seed instance and inspects the integration-tip patch, the captured artifacts, and the score report.
  - *Evidence to collect:* run A1 once; print the patch, the artifact bundle contents, and the `ScoreReport`.
  - *Status:* ☐ unverified

## Regression check

- Task 07's driver dispatches arms generically. Trace an A0 trial through the driver after A1 is added → expect A0 still runs and scores unchanged : ☐ (PRESERVED / REGRESSION)

## Residue

- Patch extraction from a multi-merge integration tip is a task Open question; the validator should test it on an instance whose plan has parallel tasks and lower CONFIDENCE if untested.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐
