# Done Certificate — Task 01: BenchFlow scaffold

**Task:** [01-benchflow_scaffold.md](01-benchflow_scaffold.md) · **Plan:** [plan.md](../plan.md)
**State:** Validated 2026-05-27

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
  - *Collected:* `uv run bench tasks check benchmark/suites/benchflow-probe/trivial-probe` → `✓ trivial-probe — valid` (exit 0). `uv run python -c "import benchmark.harness"` → `OK`, no import error. `benchflow==0.4.0` present in `uv.lock` (with deps anyio/httpx/pydantic/pyyaml/rich/typer) and listed in `benchmark`'s `requires-dist`. Check: the `bench` console-script entry point resolves to `benchflow.cli.main:app` from distribution `benchflow` (queried via `importlib.metadata.entry_points`), the venv `bench` at `.venv/bin/bench` — not a same-named local script. No shadowing.
  - *Status:* ☑ SATISFIED

- **O2 — BenchFlow can host the custom schema + per-arm provisioning + separate scoring, or the gap is recorded.**
  - *Claim:* a custom task schema and a two-step (run, then score) eval are expressible in BenchFlow, or any blocking limitation is written into `plan.md`'s Open questions.
  - *Evidence to collect:* read the scaffold's spike/notes demonstrating a custom schema and a run-then-score eval; if unsupported, read the new entry in `plan.md` §Open questions naming the limitation.
  - *Collected:* the substrate spike is recorded in `benchmark/harness/substrate.py` (module docstring + named constants), investigated against `benchflow==0.4.0`. It finds: (1) `bench tasks init`/`check` exist and the probe task validates with no Docker daemon; (2) `bench tasks check` validates a **fixed** layout (`REQUIRED_TASK_FILES`/`REQUIRED_TASK_DIRS`), NOT the benchmark's custom `TaskInstance` schema (`BENCH_VALIDATES_TASKINSTANCE_SCHEMA = False`) — the schema stays in `benchmark.harness.domain`; (3) BenchFlow's eval is a single-sandbox rollout (agent + verifier `tests/test.sh` → reward share one environment), so the spec's two-container scoring-isolation split is NOT native (`BENCH_NATIVE_TWO_CONTAINER_SPLIT = False`) and stays on the benchmark's own `RunBackend`/`ScoringBackend` seam. The probe (`benchmark/suites/benchflow-probe/trivial-probe`) demonstrates the run-then-score shape (`tests/test.sh` writes `reward.txt`). The blocking limitation is written into `plan.md` §Open questions ("*Two-container split in BenchFlow's eval model* … **Resolved 2026-05-27 (Task 01) — it needs a wrapper.**") and the corresponding Assumption is annotated "partially false". Spike depth is adequate: it names the exact two-container constraint the Residue flags, with evidence from the installed package (mirrors `benchflow._utils.task_authoring`). Gap honestly recorded — an acceptable DONE outcome per the task DoD.
  - *Status:* ☑ SATISFIED

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format are clean, dependencies are locked, limits are named constants (per the plan.md baseline — no `development-guidelines.md` exists).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean; confirm `uv.lock` is present and current.
  - *Collected:* `bash scripts/check.sh` (full suite) → `uv sync` clean, `ruff format --check` 32 files already formatted, `ruff check` All checks passed, `pyright` 0 errors/0 warnings, `pytest` 70 passed. `uv sync --frozen` → clean (exit 0, 33 packages, lock current). `uv.lock` present (71886 bytes) with `benchflow==0.4.0` locked. Limits are named constants: `REQUIRED_TASK_FILES`, `REQUIRED_TASK_DIRS`, and the `BENCH_*` flags in `benchmark/harness/substrate.py`; the probe's `task.toml` carries explicit `timeout_sec`/`cpus`/`memory_mb`. (No `development-guidelines.md` baseline applies; plan.md baseline met.)
  - *Status:* ☑ SATISFIED

- **O4 — Reviewable: `uv run bench tasks check` and the test suite pass on a clean checkout.**
  - *Claim:* a reviewer on a fresh checkout can run the check and the tests and see both pass.
  - *Evidence to collect:* on a clean clone, run `uv sync`, `uv run bench tasks check`, and `uv run pytest` — expect all pass.
  - *Collected:* exercised against the locked state. `uv sync --frozen` clean → `uv run bench tasks check benchmark/suites/benchflow-probe/trivial-probe` → `✓ trivial-probe — valid` → `uv run pytest` (full) 70 passed; substrate+smoke subset 8 passed independently. The reviewable action runs and both halves hold from the locked dependency set. (Discharged against the jj workspace synced from `uv.lock`, not a separate `git clone`, but the frozen-lock sync is the equivalent clean-checkout invariant.)
  - *Status:* ☑ SATISFIED

## Regression check

- Task 17's skeleton is the base. Trace `import benchmark.harness` and `uv run pytest` after BenchFlow is layered on → expect the skeleton's imports and smoke test still pass : ☑ PRESERVED. `import benchmark.harness` → OK; all 6 harness sub-packages and `benchmark.suites` still import (smoke test passes inside the 70). The one intended change to the skeleton's smoke test is correct, not a regression: Task 17 asserted `benchflow` must NOT be installed (`test_no_benchflow_dependency`); Task 01 wires the §Substrate, so it now correctly asserts `benchflow` IS installed (`test_benchflow_substrate_installed`) — the inverted assertion tracks the substrate decision. No other existing code touched; `pyproject.toml` adds `benchflow>=0.4.0` and excludes the throwaway probe from ruff/pyright (probe is BenchFlow-generated scaffolding, correctly out of scope).

## Residue

- The depth of the BenchFlow feasibility spike (O2) is the validator's judgement; a shallow spike that misses the two-container constraint should lower CONFIDENCE, not pass silently.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: DONE
CONFIDENCE: high
SUMMARY: O1–O4 all SATISFIED with evidence — `bench tasks check` passes on the in-repo probe with the `bench` entry point resolved to the `benchflow` dist (not a local shadow), the substrate spike honestly records the non-native two-container split + custom-schema gaps in `substrate.py` and plan.md §Open questions, the repo DoD is clean (70 pytest / ruff / pyright / `uv sync --frozen`), and the reviewable check + suite pass on the locked state; the Task 17 skeleton import and smoke test are PRESERVED (its one inverted benchflow assertion correctly tracks the now-wired substrate).
