# Done Certificate — Task 23: Local pipeline demonstration

**Task:** [23-local_pipeline_demo.md](../23-local_pipeline_demo.md) · **Plan:** [plan.md](../plan.md)
**State:** Validated 2026-05-27

> This certificate is a verification protocol for Task 23. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 23) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** The driver runs a local `Campaign` (`backend: local`, `solver: fixture`) over the `local-fixture` suite end to end and yields a deterministic resolved verdict plus a minimal %Resolved — run→score→aggregate, no Docker.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Wires the Task 07 driver, the Task 20 local `ScoringBackend`, the Task 22 local `RunBackend`, and the Task 21 fixture; must not modify their behavior, only compose them.

## Obligations

- **O1 — The driver runs the local campaign end to end with a deterministic resolved fixture trial.**
  - *Claim:* a local `Campaign` (`backend: local`, `solver: fixture`, fixture suite) runs through the driver and the fixture trial is `resolved` deterministically across repeated runs.
  - *Evidence to collect:* run the local campaign twice; confirm the fixture trial is `resolved: true` both times with an identical `ScoreReport`.
  - *Checks:* resolve the run/score calls to the local backends (Tasks 22/20) selected by `Campaign.backend == local`, not the container backends.
  - *Status:* ☑ SATISFIED — `run_local_demo()` assembles `demo_campaign()` (`backend=local`, `solver=fixture`, suite `local-fixture`, `trialsPerInstance=3`) and drives it through the REAL task-07 `run_campaign` (`driver/scheduler.py:252`) with the REAL `LocalRunBackend` (`backends/local.py:84`, task 22) and `LocalScoringBackend` (`scoring/local.py:96`, task 20) injected — no container backend constructed anywhere (`run_local_demo.py:162-171`). The driver's `_arm_or_solver` routes `solver=="fixture"` to the scripted goldPatch path; the scorer runs hidden pytest in a temp checkout. Two CLI repeats and `test_fixture_verdict_is_deterministic_across_repeated_runs` (1 passed) yield identical `(seed, resolved=True, regressed=False)` for all 3 trials, every trial `status=aggregated`, `failed=0`.

- **O2 — %Resolved over the fixture is computed and correct.**
  - *Claim:* %Resolved is `1.0` with the fixture solver and `0.0` with a no-op solver variant.
  - *Evidence to collect:* run with `solver=fixture` → expect %Resolved `1.0`; run with a no-op solver variant → expect `0.0`.
  - *Status:* ☑ SATISFIED — demo output: `fixture %Resolved=1.0 (expected 1.0); no-op %Resolved=0.0 (expected 0.0)`. The no-op variant (`NoOpRunBackend` returns the `None` no-op patch per `interfaces.py:40`) is an HONEST `resolved:false`: all 3 no-op trials reach `status=aggregated` with `failed=0` and `resolved=False` — they enter the metric (scored), they are NOT excluded infra faults. Confirmed by `test_fixture_resolved_rate_is_one` and `test_noop_variant_resolved_rate_is_zero` (both passed).

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* ☑ SATISFIED — `uv sync` clean (12 packages checked); `uv run pytest -q` → `66 passed in 8.63s`; `uv run ruff check` → `All checks passed!`; `uv run ruff format --check` → `30 files already formatted`. Limits/config named as constants (`DEMO_TRIALS_PER_INSTANCE`, `DEMO_BACKEND`, `DEMO_SOLVER`, `EXPECTED_FIXTURE_RESOLVED_RATE`, `EXPECTED_NOOP_RESOLVED_RATE`, etc. in `run_local_demo.py:46-77`). Diff adds only 2 files (compose-only), no edits to tasks 07/20/21/22.

- **O4 — Reviewable: run the local campaign; read the deterministic verdict + %Resolved (no Docker). (M0 capstone.)**
  - *Claim:* a reviewer runs the local campaign and reads the deterministic resolved verdict and %Resolved — run→score→aggregate with no Docker, BenchFlow, or API.
  - *Evidence to collect:* run the campaign; print the per-trial `ScoreReport` and the aggregate %Resolved; confirm no Docker/network/API was used.
  - *Status:* ☑ SATISFIED — ran `uv run python -m benchmark.harness.run_local_demo`: it printed each Trial's verdict (`resolved=True/False regressed=False`, `status=aggregated`) and the aggregate `%Resolved=1.0` (fixture) / `0.0` (no-op). No Docker (absent on host), no network, no API: the fixture solver emits the bundled goldPatch and the scorer runs local pytest in a temp checkout. The Reviewable surface is the printed CLI verdict — verified headlessly by running it.

## Regression check

- The driver (Task 07) is exercised here for the first time. Trace one trial: driver → local `RunBackend` (22) → local `ScoringBackend` (20) → expect the `ScoreReport` matches scoring the fixture gold patch directly (Task 21) : ☑ PRESERVED — fixture trial (seed 0): `run_campaign` → `LocalRunBackend.run` emits `instance.goldPatch` → `LocalScoringBackend.score` applies it + injects hidden tests → all `failToPass`+`passToPass` pass → `resolved=True, regressed=False`, matching scoring the gold patch directly. The 62 pre-existing tests (all suites except the 4 new `test_run_local_demo.py`) still pass (`62 passed`); the 4 new tests pass. Compose-only diff modifies no upstream behavior.

## Residue

- This is pipeline verification on a fixture; full statistics (CIs, McNemar, Pass@k) arrive with Task 09 on the container path. The minimal %Resolved here is superseded, not the final reporting.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: DONE
CONFIDENCE: high
SUMMARY: All four obligations SATISFIED and the regression PRESERVED with evidence in hand — the demo drives the local `backend=local`/`solver=fixture` campaign over `local-fixture` through the REAL task-07 driver with the REAL task-20/22 local backends injected (no bypass), yielding a deterministic `resolved=True` verdict (identical across repeats), `%Resolved=1.0` for the fixture solver and an honest scored `%Resolved=0.0` for the no-op variant (`failed=0`), with no Docker/network/API; `pytest` (66 passed, 62 prior preserved), `ruff check`, and `ruff format --check` all clean.
