# Done Certificate — Task 19: Backend interfaces

**Task:** [19-backend_interfaces.md](../19-backend_interfaces.md) · **Plan:** [plan.md](../plan.md)
**State:** Validated 2026-05-27

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
  - *Evidence collected:* `interfaces.py:73-75` defines `RunBackend.run(self, instance: TaskInstance, arm_or_solver: ArmOrSolver) -> tuple[ArtifactBundle, CandidatePatch]`; `interfaces.py:104-106` defines `ScoringBackend.score(self, instance: TaskInstance, candidate_patch: CandidatePatch) -> ScoreReport` — both the spec'd signatures. `test_backends.py:113-116` (`test_double_satisfies_both_protocols`) passes: `isinstance(backend, RunBackend)` and `isinstance(backend, ScoringBackend)` both `True` (driven live). Round-trip `test_round_trip_run_then_score_resolves` passes: `run("fixture") -> (ArtifactBundle, _GOLD_PATCH)`, `score -> ScoreReport(resolved=True, regressed=False)`.
  - *Checks result:* `ArtifactBundle`, `ScoreReport`, `TaskInstance` resolve (step 4, imported) to `benchmark.harness.domain` — `domain.py:373/421/297` — the real Task 02 entities, not local stand-ins. No shadowing.
  - *Status:* ☑ SATISFIED

- **O2 — The integrity-rule contract is stated and a run-output test enforces it.**
  - *Claim:* the interface docs state run env and scoring env are distinct with hidden tests on the scoring side only, and a test asserts a backend's run output carries no hidden tests.
  - *Evidence to collect:* read the contract docstring on the interfaces; run the test asserting the test-double's run output excludes hidden tests.
  - *Evidence collected:* module docstring `interfaces.py:10-25` and the per-protocol "INTEGRITY RULE" docstrings (`RunBackend` `interfaces.py:65-70`: "the RUN side NEVER sees the hidden tests … run environment is a DISTINCT filesystem/process"; `ScoringBackend` `interfaces.py:95-96`: "hidden … suite is injected ONLY here, on the scoring side") state run env and scoring env are distinct with hidden tests scoring-side only. The shared resolution rule is stated at `interfaces.py:98-102`. `test_run_output_carries_no_hidden_tests` (`test_backends.py:149-167`) passes; driven live: `HIDDEN_TEST_FIELDS = ('failToPass','passToPass')`, hidden-selector/field leak in `repr(bundle.to_dict())+repr(patch)` = NONE, and oracle selectors absent from `run_inputs_seen` (`['localfix__demo__0001','Make f() return 1.','fixture']`). The bundle has no failToPass/passToPass field (`domain.py:373-385`), so the run side cannot structurally carry the suite.
  - *Status:* ☑ SATISFIED

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Evidence collected:* `uv sync` → "Resolved 13 packages / Checked 12 packages" (deps locked). `uv run pytest -q` → `39 passed in 0.12s`. `uv run ruff check` → "All checks passed!". `uv run ruff format --check` → "16 files already formatted". Named-constant limits: `HIDDEN_TEST_FIELDS`, `CandidatePatch`, `ArmOrSolver` are module-level named constants (`interfaces.py:40-51`); telemetry magic numbers in the test fixture are test data, not limits. jj working copy.
  - *Status:* ☑ SATISFIED

- **O4 — Reviewable: read the two protocols and run the test-double through them.**
  - *Claim:* a reviewer reads the `RunBackend`/`ScoringBackend` protocols and runs the conformance test-double through them.
  - *Evidence to collect:* open the protocols; run the conformance test and observe it pass.
  - *Evidence collected:* read both protocols at `interfaces.py:54-113` — two `@runtime_checkable` `Protocol` classes with the spec'd single methods and full contract docstrings. Ran the conformance double through the protocol surface live (run -> bundle+patch -> score -> ScoreReport): `isinstance` True for both, round-trip resolved=True/regressed=False, no-op patch resolved=False, no hidden-test leak. All 4 tests in `test_backends.py` pass.
  - *Status:* ☑ SATISFIED

## Regression check

No existing callers yet — the interfaces are consumed by the driver (07) and backends (04/05/20/22) downstream. Confirm Task 02 types import unchanged into the backends module : ☑ PRESERVED — the diff touches only the 3 new files (`backends/__init__.py`, `backends/interfaces.py`, `tests/test_backends.py`); `domain.py` is unmodified. The backends module imports `ArtifactBundle, ScoreReport, TaskInstance` from `benchmark.harness.domain` and the full suite runs `39 passed` (35 prior domain/harness tests + 4 new), so the Task 02 types import unchanged.

## Residue

- None noted at authoring.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: DONE
CONFIDENCE: high
SUMMARY: O1–O4 all SATISFIED with evidence (both protocols carry the spec'd signatures over the real Task-02 domain types, the integrity and shared resolution rules are documented on the interfaces and asserted by tests, deps locked + 39 pytest passed + ruff check/format clean, and the runtime-checkable double was driven through run->score and the no-hidden-tests assertion live), and the Task-02 type import is PRESERVED.
