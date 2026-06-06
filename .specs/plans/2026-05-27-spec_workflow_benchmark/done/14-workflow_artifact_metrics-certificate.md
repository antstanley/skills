# Done Certificate — Task 14: Workflow-artifact metrics

**Task:** [14-workflow_artifact_metrics.md](14-workflow_artifact_metrics.md) · **Plan:** [plan.md](../plan.md)
**State:** Validated 2026-05-27

> This certificate is a verification protocol for Task 14. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 14) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** Plan coverage and DAG validity from plan artifacts, gate catch rate from injected defects, and false-`Done` escape rate.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Consumes Task 08/10 plan artifacts and gates and Task 12 `testTags`; injecting defects must not corrupt organic trial results.

## Obligations

- **O1 — Catch and escape rates for gated arms; coverage and DAG validity for plan-producing arms.**
  - *Claim:* gate catch rate (from `InjectedDefect`) and false-`Done` escape rate are produced for A1/A2; plan coverage and DAG validity are produced for A1/A2/A3.
  - *Evidence to collect:* run the metrics over a campaign with gated arms; read catch rate, escape rate, coverage, DAG validity — expect each populated for its applicable arms.
  - *Checks:* resolve the escape source to `ScoreReport.gateEscape`; resolve coverage to the `Implements`→spec-section mapping and DAG validity to an acyclicity check over the plan's dependency table.
  - *Status:* SATISFIED — Catch rate: `catch_rate` (`probes/defects.py:186`) over `InjectedDefect.caughtBy`; `test_catch_rate_counts_caught_and_escaped` → 3/5 with per-kind breakdown (PASS). Escape rate: `escape_rate` (`probes/escape.py:157`) resolves to `ScoreReport.gateEscape` semantics via `derive_gate_escape` = `not report.resolved` (`escape.py:86–96`); `gateEscape` field confirmed at `domain.py:438`. `GATED_ARMS = ("A1","A2")` (`escape.py:39`). Coverage: `plan_coverage` (`artifact_metrics.py:205`) maps `Implements:` lines (`_IMPLEMENTS_RE`) to `## Component N:` headings; `test_plan_coverage_on_captured_a1_evidence_is_full` → fraction 1.0 over the four text_toolkit sections (PASS). DAG validity: `dag_validity` (`artifact_metrics.py:323`) does `_find_cycle` (iterative DFS) + dangling-edge resolution; `test_dag_validity_on_captured_a1_evidence_is_valid` → valid with edges["04"]=("01","02","03") (PASS). Applicability to A1/A2/A3 documented in `artifact_metrics.py` module docstring + `GATED_ARMS` constant. All 27 task-14 tests PASS (1 live skip).

- **O2 — Per-task escape attribution works where `testTags` exist and falls back otherwise.**
  - *Claim:* with `testTags` (greenfield) escape is attributed per task via the `Implements` pointer; without them escape is computed at instance granularity.
  - *Evidence to collect:* run on a greenfield instance with `testTags` → expect per-task attribution; run on an instance without `testTags` → expect instance-granularity escape. Run the known-bad-patch tests (one caught, one escaped) and confirm the counts.
  - *Status:* SATISFIED — `per_task_escapes` (`escape.py:110`) attributes failing selectors to components via `instance.testTags` and returns `()` when absent; `escape_rate` falls back to instance granularity (`escape.py:184–193`). Tests: `test_per_task_escapes_attributes_failures_via_testtags` → components {tokenizer, normalizer} (PASS); `test_escape_rate_per_task_granularity` → granularity "task", 2/3 (PASS); `test_escape_rate_instance_granularity_fallback` → granularity "instance", 1/2 (PASS); `test_escape_rate_on_captured_a1_evidence` over a real organic A1 `ScoreReport` → granularity "task", 3/4 = 0.75 (PASS). Known-bad-patch counts: `test_catch_rate_counts_caught_and_escaped` confirms caught(3)/escaped(2); `test_run_gate_probe_sets_caughtby_with_injected_reviewer` confirms one caught (BUGGY→caughtBy set) and one escaped (CORRECT→None) (PASS).

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline; defect counts/classes are named constants).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* SATISFIED — `bash scripts/check.sh`: `uv sync` checked 33 packages; `ruff format --check` 83 files formatted; `ruff check` all passed; pyright 0 errors/0 warnings; pytest 213 passed, 5 skipped (opt-in live tests) in 143.93s. `uv sync --frozen` clean (no lockfile drift). Named-constant limits present: `DEFECT_KINDS`, `DEFECT_MUTATIONS` (`defects.py`), `GATED_ARMS`, `GRANULARITY_TASK/INSTANCE` (`escape.py`), `PROBE_MAX_BUDGET_USD`, `PROBE_TIMEOUT_SECONDS`, `LIVE_PROBE_ENV` (`live.py`), `RUN_BACKEND_GATE_EVENTS_ATTR` (`scheduler.py`) — no magic numbers.

- **O4 — Reviewable: inject a known defect, see it counted caught/escaped; read coverage and DAG validity.**
  - *Claim:* a reviewer injects a known defect, sees it counted as caught or escaped, and reads the coverage and DAG-validity figures for a workflow trial.
  - *Evidence to collect:* inject one defect through a gated build; show whether it was caught; print coverage and DAG validity for the trial's plan.
  - *Status:* SATISFIED — The live gate probe already ran once: a real off-by-one defect in `frequency` (`return ranked[:limit]` → `return ranked[: limit + 1]`) was injected into the reference solution and run through the live semi-formal-review gate, which CAUGHT it. Evidence: `benchmark/tests/_gate_probe_live_evidence/defect.json` records `{"defectKind":"off-by-one","caughtBy":"semi-formal-review","component":"frequency"}` — caughtBy set = counted as caught. Coverage and DAG-validity figures for the captured A1 workflow trial are read by `test_plan_coverage_on_captured_a1_evidence_is_full` (coverage 1.0, uncovered ()) and `test_dag_validity_on_captured_a1_evidence_is_valid` (valid, 4 nodes, edges resolve) — both PASS. The reviewable loop (inject → caught → read coverage/DAG) is exercised end to end.

## Regression check

- Injected-defect probe trials must be segregated from organic trials. Trace an organic A1 trial run alongside probes → expect its `ScoreReport` is unaffected by the injected defects : PRESERVED. The probe modules are pure/read-only over organic data: `make_injected_defect`/`catch_rate` mint and read separate `InjectedDefect` records; `escape_rate`/`per_task_escapes`/`derive_gate_escape` only READ frozen `ScoreReport` dataclasses (no mutation). The live probe injects into the reference solution diff and runs an isolated `claude -p` — it NEVER touches the hidden suite (`live.py` docstring; `test_defect_mutations_apply_to_the_reference_solution` asserts targets exist only in the reference). `test_escape_rate_on_captured_a1_evidence` consumes a genuine organic A1 `ScoreReport` and yields the uncorrupted 0.75 figure. The scheduler GateEvent threading re-keys events onto Trials by `replace` (new frozen records) — no existing path mutated; `test_backend_without_gate_events_threads_none` confirms backends without events (A0/local) get `()`. Full suite (213 passed) confirms no regression in any prior task's tests.

## Residue

- Defect-injection realism (hand-injected vs mined from real failed trials) is a spec Open question; the validator should note which was used and let it inform CONFIDENCE.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: DONE
CONFIDENCE: high
SUMMARY: O1–O4 all SATISFIED with collected evidence — catch/escape rates and coverage/DAG validity produced for their applicable arms (`probes/`, `stats/artifact_metrics.py`), per-task `testTags` attribution with instance fallback proven (0.75 on real A1 evidence), repo DoD clean (213 passed/5 opt-in skips, ruff+pyright clean, `uv sync --frozen` clean, named-constant limits), and the reviewable inject→caught path exercised live (`_gate_probe_live_evidence/defect.json` caught an off-by-one) with coverage 1.0 + valid DAG read for the A1 trial; the organic A1 `ScoreReport` is PRESERVED (probes are read-only/isolated, no regression).

RESIDUE NOTE: Defect-injection realism — the one live data point used a HAND-INJECTED classified mutation (an off-by-one in `frequency`), not a defect mined from a real failed trial, consistent with the spec Open question; this is appropriate for greenfield and does not lower confidence in the mechanism, which is what this task delivers.
