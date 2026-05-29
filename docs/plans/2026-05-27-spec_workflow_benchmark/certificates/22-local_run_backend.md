# Done Certificate — Task 22: Local RunBackend and fixture solver

**Task:** [22-local_run_backend.md](../22-local_run_backend.md) · **Plan:** [plan.md](../plan.md)
**State:** Validated 2026-05-27

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
  - *Status:* ☑ SATISFIED — Fixture snippet on `load_instance()` with `FIXTURE_SOLVER`: `candidatePatch == goldPatch` True; `bundle` is `ArtifactBundle`, `telemetry` is `Telemetry` with `wallClockSeconds=0.00033` (real, ≥0) and `inputTokens/outputTokens/costUsd/agentTurns = 0/0/0.0/0`; bundle round-trips through schema (`from_dict(to_dict()) == bundle` True). `FIXTURE_SOLVER == "fixture"` mirrors `Campaign.solver`; run dir resolves under `RUN_TEMP_BASE=/tmp/benchmark-run`, distinct from `SCORING_TEMP_BASE=/tmp/benchmark-scoring`. Test `test_fixture_solver_emits_gold_patch_and_bundle` + `test_fixture_solver_is_deterministic` pass.

- **O2 — The run directory carries no hidden tests.**
  - *Claim:* the run working directory contains no hidden test content (integrity rule on the run side).
  - *Evidence to collect:* run the test inspecting the run dir for hidden test files → expect none.
  - *Status:* ☑ SATISFIED — `_checkout_base` (local.py:154-169) copies `source/base` ONLY via `shutil.copytree`; `hidden/` is never constructed or referenced on the run path. `test_run_dir_checks_out_base_only_never_hidden` builds a repo with `hidden/test_secret.py` and asserts it never lands in the workdir (passes). Run output is also hidden-free: snippet `no-hidden-tests-on-run-side: True` (no `failToPass`/`passToPass` selectors nor `test_add`/`test_identity` in `repr(bundle)+repr(patch)`); `test_run_output_carries_no_hidden_tests` passes. `RUN_TEMP_BASE != SCORING_TEMP_BASE` and neither is the other's parent (`test_run_dir_is_distinct_from_scoring_dir` passes).

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* ☑ SATISFIED — `uv sync` → "Resolved 13 packages / Checked 12 packages" (deps locked). `uv run pytest -q` → `62 passed in 3.86s`. `uv run ruff check` → "All checks passed!". `uv run ruff format --check` → "28 files already formatted". Limits/values are named constants (`RUN_TEMP_BASE`, `RUN_DIR_PREFIX`, `FIXTURE_SOLVER`, `_FIXTURE_INPUT_TOKENS`/`_OUTPUT_TOKENS`/`_COST_USD`/`_AGENT_TURNS`).

- **O4 — Reviewable: run the fixture solver on the fixture instance; inspect the gold patch + bundle.**
  - *Claim:* a reviewer runs the fixture solver on the fixture instance and inspects the emitted gold patch and the artifact bundle.
  - *Evidence to collect:* run the backend with `solver=fixture`; print the `candidatePatch` and the `ArtifactBundle`.
  - *Status:* ☑ SATISFIED — Reviewer ran the fixture solver on `load_instance()` via the snippet above: `candidatePatch == goldPatch` True (the real instance `goldPatch` emitted verbatim, no API), `ArtifactBundle` populated with a `Telemetry` record (real `wallClockSeconds`, zero tokens/cost/turns), schema round-trip True, determinism confirmed across two runs.

## Regression check

- Task 19's `RunBackend` interface is the contract. Trace the local backend through the interface conformance test → expect it satisfies the protocol unchanged : ☑ PRESERVED — `LocalRunBackend.run(self, instance, arm_or_solver) -> tuple[ArtifactBundle, CandidatePatch]` matches the `@runtime_checkable RunBackend` Protocol (interfaces.py:54-82); `isinstance(LocalRunBackend(), RunBackend)` is True (snippet + `test_backend_satisfies_run_protocol`). `interfaces.py` and `scoring/local.py` are unchanged; `backends/__init__.py` only adds exports (existing names retained, `__all__` re-sorted). Prior suite unchanged: `54 passed` when the new test file is ignored; full suite `62 passed` (54 prior + 8 new).

## Residue

- The `agent` solver mode for the local backend is out of scope here (real arms use the container backend); a local agent solver is a later concern, not an obligation.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: DONE
CONFIDENCE: high
SUMMARY: All four obligations are SATISFIED with collected evidence and the regression check is PRESERVED — the local `RunBackend` conforms to the Task 19 protocol, emits the real `goldPatch` as `candidatePatch` deterministically with no API, returns a schema-valid `ArtifactBundle`/`Telemetry` (real `wallClockSeconds`, zero tokens/cost/turns), keeps the run temp base distinct from the scoring base and copies `base/` only (never `hidden/`), and the repo DoD is met (`62 passed`, ruff check + format clean, deps locked, named constants).
