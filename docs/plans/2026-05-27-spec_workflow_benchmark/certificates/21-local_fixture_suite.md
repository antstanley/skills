# Done Certificate — Task 21: Local-fixture suite

**Task:** [21-local_fixture_suite.md](../21-local_fixture_suite.md) · **Plan:** [plan.md](../plan.md)
**State:** Validated 2026-05-27

> This certificate is a verification protocol for Task 21. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 21) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** The bundled `local-fixture` instance — a small repo, a hidden `pytest` suite, and a gold patch — as a validated `TaskInstance` scorable by the local `ScoringBackend`.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Uses Task 18's `local-fixture` kind / `local` convention and Task 20's local `ScoringBackend`.

## Obligations

- **O1 — The fixture validates and the local backend scores gold resolved, no-op not.**
  - *Claim:* the fixture `TaskInstance` validates, and the local `ScoringBackend` scores its `goldPatch` resolved and a no-op not.
  - *Evidence to collect:* load the fixture and validate it; score `goldPatch` via the local backend → `resolved: true`; score a no-op → `resolved: false`.
  - *Checks:* resolve the instance fields — `kind: local-fixture`, `oracleConvention: local`, `dockerImage: null`, `contaminationTier: authored-private`.
  - *Evidence collected:* `load_instance()` returns a validated `TaskInstance` (slug `localfix__calculator__0001`, suite `local-fixture`, `contaminationTier=authored-private`, `dockerImage=None`, `baseCommit=0000000`); schema round-trip `TaskInstance.from_dict(inst.to_dict()) == inst` holds (test_fixture_loads_and_validates passes). Scoring via task-20 `LocalScoringBackend`: GOLD → `resolved: True, regressed: False` (failToPass {sums:True, zero:True}, passToPass {identity:True}); NO-OP(None) → `resolved: False, regressed: False` (failToPass {sums:False, zero:True}). Note: `kind`/`oracleConvention` correctly live on `Suite`, not `TaskInstance` — the loader does not set them, schema validation accepts the instance.
  - *Status:* ☑ SATISFIED

- **O2 — The suite needs no Docker and no network.**
  - *Claim:* loading and scoring the fixture uses neither Docker nor network.
  - *Evidence to collect:* run the fixture's test with no Docker daemon and no network — expect it passes; confirm no `dockerImage` is referenced.
  - *Evidence collected:* `docker` binary ABSENT in environment, yet `uv run pytest -q` (54 passed) and the Reviewable scoring snippet both succeed. `grep -rni docker|http|socket|requests|urllib benchmark/suites/` returns only docstring mentions and `dockerImage=None` — no docker-daemon or network calls. The task-20 backend scores by local `pytest` subprocess in a temp checkout. `instance.dockerImage is None`.
  - *Status:* ☑ SATISFIED

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Evidence collected:* `uv sync` → "Resolved 13 packages / Checked 12 packages" (deps locked). `uv run pytest -q` → `54 passed in 3.75s`. `uv run ruff check` → "All checks passed!". `uv run ruff format --check` → "26 files already formatted". Loader uses named constants (SUITES_DIR, FIXTURE_DIR, REPO_SOURCE_DIR, BASE_COMMIT, FAIL_TO_PASS, PASS_TO_PASS, etc.); no magic literals.
  - *Status:* ☑ SATISFIED

- **O4 — Reviewable: load the fixture, score its gold patch via the local backend, see resolved.**
  - *Claim:* a reviewer loads the fixture and scores its gold patch through the local backend and sees `resolved: true`.
  - *Evidence to collect:* load the fixture; score the gold patch; print the `ScoreReport`.
  - *Evidence collected:* Reviewable snippet run directly: `LocalScoringBackend().score(load_instance(), inst.goldPatch)` → `resolved: True, regressed: False`, failToPass {sums:True, zero:True}, passToPass {identity:True}. Reviewer sees `resolved: true`.
  - *Status:* ☑ SATISFIED

## Regression check

- Task 20's local `ScoringBackend` scores this fixture. Trace the gold patch through the backend → expect the same `resolved: true` the backend's own tests showed : ☑ PRESERVED. The change is purely additive (loader + fixture trees + new test); no existing file modified. The fixture conforms to the backend's documented `LocalRepoSource` layout (`repo/base/`, `repo/hidden/`), selectors `hidden/...` resolve verbatim to the injected tree, gold patch context (`@@ -11,7 +11,7 @@`) matches `base/calculator.py`. All 49 prior tests still pass (54 total, 5 new).

## Residue

- Fixture breadth (one instance vs several to exercise the scorer's branches) is an Open question shared with the change spec; not an obligation here.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: DONE
CONFIDENCE: high
SUMMARY: All four obligations SATISFIED with evidence and the regression check is PRESERVED — the fixture validates against the canonical schema (Suite-only fields correctly omitted), the task-20 LocalScoringBackend scores gold resolved:true and no-op resolved:false, the suite needs no Docker (binary absent) and no network, and pytest/ruff/format are clean with all 49 prior tests still passing.
