# Done Certificate — Task 01: BenchFlow scaffold

**Task:** [01-benchflow_scaffold.md](../01-benchflow_scaffold.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-05-27 — unverified

> This certificate is a verification protocol for Task 01. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 01) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** The harness project stands up on the BenchFlow `bench` SDK: a trivial task passes `bench tasks check`, dependencies are uv-locked, and `pytest` + `ruff` run clean.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Builds on the Task 17 package skeleton (the `benchmark/` tree, `pyproject.toml`, pytest + ruff); layering BenchFlow on must not break the skeleton's existing imports or `uv run` resolution.

## Obligations

- **O1 — `bench tasks check` passes and the project imports cleanly.**
  - *Claim:* the BenchFlow SDK is installed and locked, the `benchmark/` package tree imports, and `bench tasks check` succeeds on the trivial task.
  - *Evidence to collect:* run `uv run bench tasks check` against the throwaway task — expect success; run `uv run python -c "import benchmark.harness"` — expect no import error; confirm the SDK appears in `uv.lock`.
  - *Checks:* resolve the `bench` entry point to the BenchFlow SDK dependency, not a same-named local script.
  - *Status:* ☐ unverified

- **O2 — BenchFlow can host the custom schema + per-arm provisioning + separate scoring, or the gap is recorded.**
  - *Claim:* a custom task schema and a two-step (run, then score) eval are expressible in BenchFlow, or any blocking limitation is written into `plan.md`'s Open questions.
  - *Evidence to collect:* read the scaffold's spike/notes demonstrating a custom schema and a run-then-score eval; if unsupported, read the new entry in `plan.md` §Open questions naming the limitation.
  - *Status:* ☐ unverified

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format are clean, dependencies are locked, limits are named constants (per the plan.md baseline — no `development-guidelines.md` exists).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean; confirm `uv.lock` is present and current.
  - *Status:* ☐ unverified

- **O4 — Reviewable: `uv run bench tasks check` and the test suite pass on a clean checkout.**
  - *Claim:* a reviewer on a fresh checkout can run the check and the tests and see both pass.
  - *Evidence to collect:* on a clean clone, run `uv sync`, `uv run bench tasks check`, and `uv run pytest` — expect all pass.
  - *Status:* ☐ unverified

## Regression check

- Task 17's skeleton is the base. Trace `import benchmark.harness` and `uv run pytest` after BenchFlow is layered on → expect the skeleton's imports and smoke test still pass : ☐ (PRESERVED / REGRESSION)

## Residue

- The depth of the BenchFlow feasibility spike (O2) is the validator's judgement; a shallow spike that misses the two-container constraint should lower CONFIDENCE, not pass silently.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐
