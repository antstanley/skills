# Done Certificate — Task 19: Backend interfaces

**Task:** [19-backend_interfaces.md](../19-backend_interfaces.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-05-27 — unverified

> This certificate is a verification protocol for Task 19. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 19) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** The `RunBackend` and `ScoringBackend` interfaces the driver and the concrete backends code against.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Uses Task 02 types (`ArtifactBundle`, `ScoreReport`, `candidatePatch`); defines contracts only — no concrete backend behavior.

## Obligations

- **O1 — Both protocols are defined and a test-double satisfies them.**
  - *Claim:* `RunBackend.run(instance, arm_or_solver) -> (ArtifactBundle, candidatePatch)` and `ScoringBackend.score(instance, candidatePatch) -> ScoreReport` are defined, and an in-memory test-double implements both and round-trips through the driver-facing calls.
  - *Evidence to collect:* read the protocol definitions in `benchmark/harness/backends/`; run the test-double conformance test — expect it satisfies both protocols.
  - *Checks:* resolve the type references in the signatures to the Task 02 entities (`ArtifactBundle`, `ScoreReport`), not local stand-ins.
  - *Status:* ☐ unverified

- **O2 — The integrity-rule contract is stated and a run-output test enforces it.**
  - *Claim:* the interface docs state run env and scoring env are distinct with hidden tests on the scoring side only, and a test asserts a backend's run output carries no hidden tests.
  - *Evidence to collect:* read the contract docstring on the interfaces; run the test asserting the test-double's run output excludes hidden tests.
  - *Status:* ☐ unverified

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* ☐ unverified

- **O4 — Reviewable: read the two protocols and run the test-double through them.**
  - *Claim:* a reviewer reads the `RunBackend`/`ScoringBackend` protocols and runs the conformance test-double through them.
  - *Evidence to collect:* open the protocols; run the conformance test and observe it pass.
  - *Status:* ☐ unverified

## Regression check

No existing callers yet — the interfaces are consumed by the driver (07) and backends (04/05/20/22) downstream. Confirm Task 02 types import unchanged into the backends module : ☐ (PRESERVED / REGRESSION)

## Residue

- None noted at authoring.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐
