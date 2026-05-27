# Done Certificate — Task 20: Local ScoringBackend

**Task:** [20-local_scoring_backend.md](../20-local_scoring_backend.md) · **Plan:** [plan.md](../plan.md)
**State:** Validated 2026-05-27

> This certificate is a verification protocol for Task 20. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 20) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** A `ScoringBackend` that scores a candidate patch via a temp checkout and a local `pytest` run — no Docker.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Implements the Task 19 `ScoringBackend` interface; uses Task 18's `local` oracle convention; must honour the integrity rule.

## Obligations

- **O1 — Gold resolves, no-op does not, on an inline test instance.**
  - *Claim:* `score()` makes a fresh temp checkout at `baseCommit`, applies the patch, injects hidden tests, runs `pytest`, and derives `resolved`/`regressed` correctly — gold patch resolves, no-op does not.
  - *Evidence to collect:* run the backend's tests over an inline throwaway repo+tests — expect gold → `resolved: true`, no-op → `resolved: false`; confirm `regressed` is set when a `passToPass` breaks.
  - *Checks:* resolve the resolution rule to the shared definition (all `failToPass` pass AND `passToPass` hold), not a local re-derivation; resolve the `pytest` invocation to a subprocess against the temp checkout.
  - *Evidence collected:* `test_gold_patch_resolves`, `test_noop_patch_does_not_resolve`, `test_regression_patch_sets_regressed` all PASS (4 passed in 2.08s). Independent inline snippet over a throwaway repo: GOLD → `resolved=True regressed=False`; NOOP → `resolved=False regressed=False`; regression patch → `regressed=True` (test asserts `passToPassResults[...] is False`).
  - *Checks resolved:* `derive_resolved`/`derive_regressed` in `score()` (local.py:138-139) resolve (step 4, imported) to `benchmark.harness.scoring.resolution` — the single shared source, not a local re-derivation; `derive_resolved` = `all(failToPass) and all(passToPass)`, matching the spec convention (`06-scoring-and-statistics.md` §The test oracle, and `interfaces.py` RESOLUTION RULE). `pytest` resolves (local.py:199-205) to `subprocess.run([sys.executable, "-m", "pytest", ..., selector], cwd=checkout)` — a subprocess against the temp checkout. No shadowing.
  - *Status:* ☑ SATISFIED

- **O2 — Scoring dir is separate from the run dir; hidden tests injected only here.**
  - *Claim:* the scoring temp directory is distinct from any run directory and the hidden tests are introduced only on the scoring side.
  - *Evidence to collect:* read the temp-dir handling; run the test asserting the scoring dir differs from the run dir and hidden tests appear only in scoring.
  - *Evidence collected:* `score()` (local.py:120-122) creates the checkout via `tempfile.mkdtemp(prefix=SCORING_DIR_PREFIX, dir=SCORING_TEMP_BASE)` — a fresh unique dir per call under a named base `<tmp>/benchmark-scoring`; a `RunBackend` never uses this base, so the scoring dir is distinct from any run dir. `_prepare_checkout` copies `base/` into the checkout, then injects `hidden/` into `checkout/hidden/` ONLY (local.py:160-170) — the source `base/` tree is never mutated. Test `test_scoring_dir_is_distinct_and_hidden_tests_only_on_scoring_side` PASSES. Independent snippet: run-visible `base/` blob contains no `test_f_returns_one`/`test_smoke` (RUN-SIDE has hidden? False); `SCORING_TEMP_BASE` distinct from and not a parent of a run dir.
  - *Status:* ☑ SATISFIED

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Evidence collected:* `uv sync` → `Resolved 13 packages` / `Checked 12 packages` (deps locked). `uv run pytest -q` → `49 passed in 2.30s`. `uv run ruff check` → `All checks passed!`. `uv run ruff format --check` → `20 files already formatted`. Limits named as module constants in local.py: `SCORING_TEMP_BASE`, `SCORING_DIR_PREFIX`, `REPO_BASE_SUBDIR`, `REPO_HIDDEN_SUBDIR`, `INJECTED_HIDDEN_DIR`, `PYTEST_TIMEOUT_SECONDS = 120`, `_PYTEST_EXIT_OK`.
  - *Status:* ☑ SATISFIED

- **O4 — Reviewable: score a gold and a no-op patch locally; inspect run side has no hidden tests.**
  - *Claim:* a reviewer scores a gold patch (resolved) and a no-op (not resolved) locally and inspects that the run side carries no hidden tests.
  - *Evidence to collect:* run the two scorings on the inline instance; print the `ScoreReport`s; inspect the directories.
  - *Evidence collected:* exercised via an independent inline snippet (not by assumption). Printed reports: `GOLD resolved=True regressed=False f2p={'hidden/test_feature.py::test_f_returns_one': True} p2p={'hidden/test_smoke.py::test_smoke': True}`; `NOOP resolved=False regressed=False f2p={...: False} p2p={...: True}`. Inspected the run-visible `base/` tree directly — carries no hidden test content (`RUN-SIDE has hidden? False`). `ALL ASSERTIONS PASSED`.
  - *Status:* ☑ SATISFIED

## Regression check

- Task 19's `ScoringBackend` interface is the contract. Trace the local backend through the interface's conformance test → expect it satisfies the protocol unchanged : ☑ PRESERVED — `LocalScoringBackend.score(instance, candidate_patch) -> ScoreReport` matches the `@runtime_checkable` `ScoringBackend` Protocol signature in `backends/interfaces.py`; 45 prior tests pass unchanged (`uv run pytest --ignore=tests/test_local_scoring.py` → `45 passed`), and the full suite is `49 passed` with the 4 new tests. No existing module was modified except `scoring/__init__.py` (additive re-exports).

## Residue

- Local–container verdict parity is a change-spec Open question; the validator notes it but it is not an obligation of this task.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: DONE
CONFIDENCE: high
SUMMARY: O1–O4 all SATISFIED with collected evidence (4 local-scoring tests pass; an independent snippet confirms gold→resolved, no-op→not-resolved, regression→regressed, and the run-visible base/ tree carries no hidden tests); the resolution rule is single-sourced in resolution.py and pytest runs as a subprocess in the temp checkout; uv/pytest/ruff all clean (49 passed); the ScoringBackend protocol is PRESERVED with 45 prior tests still passing.
