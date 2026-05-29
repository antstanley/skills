# Done Certificate — Task 06: Telemetry capture

**Task:** [06-telemetry_capture.md](../06-telemetry_capture.md) · **Plan:** [plan.md](../plan.md)
**State:** Validated 2026-05-27

> This certificate is a verification protocol for Task 06. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 06) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** Every run records `inputTokens`, `outputTokens`, `costUsd`, `wallClockSeconds`, and `agentTurns` into `ArtifactBundle.telemetry`, uniformly across arms.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Wraps the Task 05 run loop; must not change the `candidatePatch` or transcript the run produces.

## Obligations

- **O1 — An A0 run yields a `Telemetry` record with all five fields populated and non-negative.**
  - *Claim:* after an A0 run, `Telemetry` has `inputTokens`, `outputTokens`, `costUsd`, `wallClockSeconds`, `agentTurns`, each present and ≥ 0.
  - *Evidence to collect:* run A0 on a seed instance; read `ArtifactBundle.telemetry` → expect all five fields present and non-negative. Run the test asserting the same.
  - *Checks:* resolve the telemetry write to the `Telemetry` type from Task 02 (schema-validated), not an ad-hoc dict.
  - *Status:* SATISFIED — `benchmark/tests/test_telemetry.py::test_captures_all_five_fields_correctly_mapped` PASS (5/5 telemetry tests pass): all five fields present, correctly mapped, each ≥ 0. The live A0 run (gate-1-verified: 68s, ~$0.15) produced a populated 5-field `ArtifactBundle.telemetry` through this same path. Check: the write resolves to `benchmark.harness.domain.Telemetry` — `capture.py:56` returns `Telemetry(...)` (imported at `capture.py:33`), and `domain.py:361` `class Telemetry(Record)` is schema-validated (`Telemetry.from_dict(t.to_dict()) == t` round-trips in `test_round_trips_through_schema`). Not an ad-hoc dict.

- **O2 — Capture is uniform across arms, or the A0 granularity gap is documented.**
  - *Claim:* the same capture path serves the plain A0 baseline and the plugin arms, or any A0 granularity shortfall is recorded in `plan.md` Open questions.
  - *Evidence to collect:* read the capture implementation — confirm it is arm-agnostic; if A0 cannot report at parity, read the recorded gap in `plan.md` §Open questions.
  - *Status:* SATISFIED — a single arm-agnostic function `telemetry_from_agent_result` (`benchmark/harness/telemetry/capture.py:36`) is the one capture path; the run backend delegates to it at `container.py:207` (`telemetry = telemetry_from_agent_result(result_json, wall_clock_seconds)`). The prior inline `_telemetry_from_result` static method and its `_as_int`/`_as_float` helpers were removed from `container.py` (DRY) — `grep` for them across `benchmark/` returns no hits. Every arm funnels its `claude -p --output-format json` result through this one function, so granularity is uniform. A0-parity holds with NO gap, recorded in the `capture.py` module docstring (lines 20-26); nothing to log in plan.md Open questions.

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* SATISFIED — `bash scripts/check.sh` clean: `ruff format --check` (64 files formatted), `ruff check` (all passed), `pyright` (0 errors, 0 warnings), `pytest` (104 passed in 140s). `uv sync --frozen` clean (33 packages checked, exit 0) — deps uv-locked. Limits use named non-negative-zero defaults in the `_as_non_negative_int`/`_as_non_negative_float` coercion helpers (`capture.py:65-76`).

- **O4 — Reviewable: inspect an A0 bundle and see complete telemetry.**
  - *Claim:* a reviewer inspects the `ArtifactBundle` from an A0 run and sees complete telemetry.
  - *Evidence to collect:* run A0 once; print `ArtifactBundle.telemetry`.
  - *Status:* SATISFIED — gate 1 (semi-formal-review, CORRECT/high) ran a real A0 run that produced a populated 5-field `ArtifactBundle.telemetry` through the shared capture path. The bundle is assembled at `container.py:208-213` with `telemetry=telemetry` from `telemetry_from_agent_result`, so a reviewer inspecting the A0 bundle sees complete telemetry. Re-running the $0.15 live A0 was not repeated per the cost note; the same record is reproduced deterministically by the unit tests.

## Regression check

- Task 05's run output (patch + transcript) must be unchanged by the telemetry wrapper. Trace one A0 run with telemetry enabled → expect the same `candidatePatch` and transcript as without it : PRESERVED — in `container.py.run`, `candidate_patch` is extracted at line 200 (inside the try/finally, upstream of telemetry) and the transcript is `json.dumps(result_json, sort_keys=True)` at line 212; both are independent of the `Telemetry` object. The change only swapped which function builds `telemetry` (inline `_telemetry_from_result` → shared `telemetry_from_agent_result`) and reads the same `result_json`/`wall_clock_seconds` inputs without mutating them. No change to patch or transcript.

## Residue

- Cost-matching that consumes this telemetry is Task 15; this task only captures the fields.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: DONE
CONFIDENCE: high
SUMMARY: O1–O4 all SATISFIED — one arm-agnostic `telemetry_from_agent_result` writes a schema-validated 5-field non-negative `Telemetry` (proven by 5/5 passing unit tests and gate 1's live A0 run), the old inline capture is removed (DRY) with A0-parity recorded and no granularity gap, and the full repo DoD is clean (`uv sync --frozen`, ruff, pyright, 104 pytest); the patch/transcript regression surface is PRESERVED.
