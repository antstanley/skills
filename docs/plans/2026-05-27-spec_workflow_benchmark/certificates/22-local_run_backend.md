# Done Certificate — Task 22: Local RunBackend and fixture solver

**Task:** [22-local_run_backend.md](../22-local_run_backend.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-05-27 — unverified

> This certificate is a verification protocol for Task 22. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 22) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** A `RunBackend` that runs in a temp working directory with no Docker, supporting a `fixture` scripted solver that emits the instance `goldPatch`.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Implements the Task 19 `RunBackend` interface; runs against the Task 21 fixture; uses Task 18's `solver` field; honours the integrity rule on the run side.

## Obligations

- **O1 — Fixture solver emits the gold patch + a bundle with telemetry.**
  - *Claim:* the local `RunBackend` with `solver=fixture` on the fixture instance emits the `goldPatch` as `candidatePatch` and an `ArtifactBundle` with a `Telemetry` record.
  - *Evidence to collect:* run the backend with `solver=fixture` on the fixture instance; confirm `candidatePatch` equals the fixture `goldPatch`; read the `ArtifactBundle.telemetry` (at least `wallClockSeconds` present).
  - *Checks:* resolve `solver` to the Task 18 `Campaign.solver` field; resolve the run dir to a temp directory distinct from the scoring dir.
  - *Status:* ☐ unverified

- **O2 — The run directory carries no hidden tests.**
  - *Claim:* the run working directory contains no hidden test content (integrity rule on the run side).
  - *Evidence to collect:* run the test inspecting the run dir for hidden test files → expect none.
  - *Status:* ☐ unverified

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* ☐ unverified

- **O4 — Reviewable: run the fixture solver on the fixture instance; inspect the gold patch + bundle.**
  - *Claim:* a reviewer runs the fixture solver on the fixture instance and inspects the emitted gold patch and the artifact bundle.
  - *Evidence to collect:* run the backend with `solver=fixture`; print the `candidatePatch` and the `ArtifactBundle`.
  - *Status:* ☐ unverified

## Regression check

- Task 19's `RunBackend` interface is the contract. Trace the local backend through the interface conformance test → expect it satisfies the protocol unchanged : ☐ (PRESERVED / REGRESSION)

## Residue

- The `agent` solver mode for the local backend is out of scope here (real arms use the container backend); a local agent solver is a later concern, not an obligation.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐
