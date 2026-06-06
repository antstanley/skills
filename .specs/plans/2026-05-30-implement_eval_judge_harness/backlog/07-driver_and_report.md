# Task 07 — Driver and report

**Plan:** [plan.md](../plan.md)

**Implements:** [04-report-and-cli.md](../../../evaljudge/specs/04-report-and-cli.md) §The driver, §The EvalReport artifact
**Depends on:** 02, 03, 05, 06
**Produces:** the sweep driver (discover → run → judge → derive verdict, pooled and capped, with one bad case degrading to `NOT_RUN`/surfaced error rather than aborting the sweep) and the `EvalReport` (JSON artifact + rendered summary, overall and per-skill pass rate) — the whole pipeline runs hermetically with a fake `RunBackend` and an injected `JudgeCallable`
**Pointers:** new `benchmark/evaljudge/driver.py`, `benchmark/evaljudge/report.py`; pool + scheduler shape from `benchmark/harness/driver/scheduler.py`; consumes discovery (02), run backend (03), judge (05), calibration threshold (06); builds `EvalResult`/`EvalReport`/`SkillPassRate` (01)

## Steps

- [ ] Implement the driver: select cases (via 02's `select`), and for each run the run stage then — only for a `completed` `EvalRun` — the judge stage, deriving the `EvalResult` (`PASS`/`FAIL`/`NOT_RUN`, `band`).
- [ ] A non-`completed` run yields a `NOT_RUN` `EvalResult` with no judgment; a run-stage or judge-stage exception degrades that one case (recorded with context) and the sweep continues.
- [ ] Define `DEFAULT_POOL_SIZE` and `MAX_EVALS_PER_SWEEP` named constants; run independent cases concurrently up to the pool; when discovery exceeds the sweep cap, report what was dropped (no silent truncation).
- [ ] Implement `EvalReport` assembly: `pass_rate` over all results (a `NOT_RUN` counts against it; an excluded malformed fixture is reported separately and not in the denominator), `by_skill` breakdown, and the `created` timestamp passed in (never read from a wall clock inside the pure assembly).
- [ ] Implement report rendering: JSON serialization (validates against the schema) and a compact summary table grouped by skill with failures/`NOT_RUN`s sorted first; save the JSON under a known evidence path.
- [ ] Add `benchmark/tests/test_evaljudge_driver.py` and `test_evaljudge_report.py` (hermetic): a full discover→run→judge→report pipeline with a fake `RunBackend` + injected `JudgeCallable` produces an `EvalReport`; a fake backend returning a non-`completed` run yields `NOT_RUN`; a judge that raises degrades one case without aborting; `pass_rate`/`by_skill` compute correctly including the `NOT_RUN`-counts-against rule; the sweep cap reports drops.

## Definition of done

- [ ] The driver runs the full discover→run→judge→derive pipeline and aggregates `EvalResult`s into an `EvalReport`, entirely hermetically (both seams faked, no model call).
- [ ] A `NOT_RUN` (non-completed run) and a degraded case (stage exception) are both handled without aborting the sweep, and `NOT_RUN` counts against `pass_rate` while an excluded malformed fixture does not.
- [ ] `by_skill` pass rates compute correctly; the report serializes to schema-valid JSON and renders a failures-first summary; `created` is injected, not wall-clock-read.
- [ ] `DEFAULT_POOL_SIZE` and `MAX_EVALS_PER_SWEEP` are named constants; exceeding the cap reports the drop.
- [ ] Negative space: non-completed run → `NOT_RUN`; stage exception → degraded case, sweep continues; over-cap → reported drop.
- [ ] Meets the repo definition of done (tests, ruff, pyright, determinism via injected clock/ids — see plan.md baseline).
- [ ] Reviewable: `uv run pytest benchmark/tests/test_evaljudge_driver.py benchmark/tests/test_evaljudge_report.py` is green; a reviewer reads an `EvalReport` produced by the fully-faked pipeline and sees per-skill pass rates.
