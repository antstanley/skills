# Done Certificate — Task 17: Python package skeleton (no BenchFlow)

**Task:** [17-package_skeleton.md](../17-package_skeleton.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-05-27 — unverified

> This certificate is a verification protocol for Task 17. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 17) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** A uv-managed Python package — the `benchmark/` tree with `pytest` + `ruff` wired and deps locked — that imports and tests clean without BenchFlow.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** The only pre-existing files are `pyproject.toml`, `.python-version`, and `main.py`; the skeleton must not break `uv run python main.py`.

## Obligations

- **O1 — `uv run pytest` passes and the package imports.**
  - *Claim:* the smoke test passes and `import benchmark.harness` (and sub-packages) resolves.
  - *Evidence to collect:* run `uv run pytest` — expect the smoke test passes; run `uv run python -c "import benchmark.harness, benchmark.harness.driver, benchmark.harness.backends"` — expect no error.
  - *Status:* ☐ unverified

- **O2 — No BenchFlow dependency is present.**
  - *Claim:* the skeleton is the Docker-free root; BenchFlow is split out to task 01.
  - *Evidence to collect:* grep `pyproject.toml` and `uv.lock` for `benchflow`/`bench` — expect absent; confirm `import benchflow` fails.
  - *Status:* ☐ unverified

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean; confirm `uv.lock` present.
  - *Status:* ☐ unverified

- **O4 — Reviewable: clean checkout `uv sync` + `uv run pytest` pass with no BenchFlow.**
  - *Claim:* on a fresh checkout a reviewer runs `uv sync` and `uv run pytest` and both pass with BenchFlow uninstalled.
  - *Evidence to collect:* on a clean clone run `uv sync` then `uv run pytest` — expect pass; confirm BenchFlow is not installed.
  - *Status:* ☐ unverified

## Regression check

- The pre-existing placeholder must still run. Trace `uv run python main.py` after the skeleton lands → expect it still prints its line : ☐ (PRESERVED / REGRESSION)

## Residue

- None noted at authoring.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐
