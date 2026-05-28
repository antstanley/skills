# Task 02 — Gate-emission and live `claude -p` probe checks

**Plan:** [plan.md](plan.md) · **Status:** Done

> **Built 2026-05-28.** Gate 1 (semi-formal-review): LIKELY_CORRECT — gate-emission asserted at both the backend (`last_gate_events`) and driver-threaded (`TrialResult.gate_events`) layers (serial, pool_size=1, to avoid racing the last-run property), live probe mirrors the proven diff-build pattern; live Docker path judged by reading. Gate 2 (validate-done-certificate): DONE — skip path verified (exit 0), ruff/pyright/pytest green (329 passed).

**Implements:** [changes/2026-05-28-add_live_container_verification.md](../../benchmark/specs/changes/2026-05-28-add_live_container_verification.md) → §Proposed changes → `05-harness-architecture.md` §Runtime verification (the *gate emission* and *live `claude -p` gate probe* bullets) and `06-scoring-and-statistics.md` §Gate-efficacy probes; Implementation notes steps 4–5.
**Depends on:** 01
**Produces:** the self-test additionally asserts that on the `text_toolkit` instance A2 surfaces ≥ 1 `GateEvent` and A3 surfaces zero (threaded onto `TrialResult.gate_events` by the driver), and that one bounded live `claude -p` review of an injected off-by-one defect returns `caughtBy = "semi-formal-review"`.
**Pointers:** `ContainerRunBackend.last_gate_events` (`benchmark/harness/backends/container.py:775`); driver threading `TrialResult.gate_events` / `RUN_BACKEND_GATE_EVENTS_ATTR` (`benchmark/harness/driver/scheduler.py:66`, `:309`); `run_gate_probe` + `cli_review_gate` + `PROBE_MAX_BUDGET_USD` / `PROBE_TIMEOUT_SECONDS` (`benchmark/harness/scoring/probes/live.py`); `DEFECT_MUTATIONS` off-by-one entry (`benchmark/harness/scoring/probes/defects.py:99`); arms A2/A3 (`benchmark/harness/arms/a2_a3.py`).

## Steps

- [x] Extend `run_container_check.py` with a gate-emission check: run A2 and A3 on the `text_toolkit` instance (bounded `--max-budget-usd`), then assert `ContainerRunBackend.last_gate_events` is non-empty for A2 and empty for A3.
- [x] Assert the events reach the Trial: drive the two arms through the driver (`run_campaign`) and assert the A2 `TrialResult.gate_events` is non-empty and A3's is empty — proving the re-keying, not just the backend attribute.
- [x] Add the live `claude -p` gate-probe check: call `run_gate_probe(task_instance, diff_text, mutation, reviewer=cli_review_gate)` on the off-by-one `DEFECT_MUTATIONS` entry (the `text_toolkit` frequency mutation) and assert the returned `InjectedDefect.caughtBy == "semi-formal-review"` — a correctness gate should catch a real fault.
- [x] Keep the probe bounded by the existing `PROBE_MAX_BUDGET_USD` / `PROBE_TIMEOUT_SECONDS`; do not introduce a second budget path.
- [x] Fold both checks under the same `BENCHMARK_RUN_CONTAINER_LIVE` opt-in guard from task 01 (gated, skipped by default); any new limit is a named constant.

## Definition of done

- [x] With the env var unset, the new checks skip cleanly alongside task 01's — still exit 0, no traceback, no `claude -p` call, no container started.
- [x] When run live (operator, reviewed by reading here): A2 surfaces ≥ 1 `GateEvent` and A3 zero, both observed on `TrialResult.gate_events`; the live probe on the off-by-one defect returns `caughtBy = "semi-formal-review"`.
- [x] Negative space: A3 (gates off) asserting **exactly zero** gate events is the paired negative case to A2's ≥ 1 — the gate-difference witness.
- [x] Meets the repo definition of done (ruff, pyright, `uv run pytest benchmark/tests` green; bounded budget/timeout as named constants — see plan.md baseline).
- [x] Reviewable: a reviewer runs the module with the env unset (clean skip) and reads the A2/A3 gate-emission and live-probe assertions to confirm they match the shipped backend + probe contracts.
