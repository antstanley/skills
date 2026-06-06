# Task 02 — Capture intra-trial workflow timing for honest parallel speedup

**Plan:** [plan.md](../plan.md)

**Implements:** [04-metrics.md](../../../benchmark/specs/04-metrics.md) §Bucket 2 — Cost and efficiency, "Parallel speedup = A1's wall-clock vs the same plan run sequentially, correlated with task-graph width."
**Depends on:** —
**Produces:** `ContainerRunBackend._run_workflow_arm` records per-task wall-clocks alongside the orchestrator's wall-clock; the `ArtifactBundle` carries the per-task series in a typed sidecar; `parallel_speedup_for_arm` is rewritten to read the series and return `sum(per-task wall-clocks) / orchestrator wall-clock` — the quantity the spec defines, not the intra-campaign `sum / max` the docstring is candid about today.
**Pointers:** `benchmark/harness/backends/container.py:677` (`_run_workflow_arm`); `benchmark/harness/arms/a2_a3.py:311` (`extract_gate_events`, the captured-certificate parser the timing capture can reuse if certificates carry an elapsed line); `benchmark/harness/domain.py:361` (`Telemetry`); `benchmark/harness/domain.py:372` (`ArtifactBundle`); `benchmark/harness/stats/cost_robustness.py:309` (`parallel_speedup_for_arm`, the consumer).

## Steps

- [x] Decide where per-task wall-clocks come from. First probe: do the discharged done-certificates `extract_gate_events` already parses carry an `Elapsed:`/`Duration:` line? If so, extend the parser to surface per-task elapsed seconds alongside the verdict. Second probe: if certificates do not carry the line, add an instruction to the A1/A2/A3 orchestrating prompts telling `spec-builder` to write a per-task `elapsed_seconds` line into each certificate (or into a sibling JSONL log). Pick the smaller of the two; document the choice in `_run_workflow_arm`'s docstring. **Chose Option B + parser extension** — current certificates carry no `Elapsed:` line, so a parser-only probe would find nothing. Added `TIMING_DIRECTIVE` to the A1/A2/A3 orchestrating prompts and a `_ELAPSED_LINE_RE`-driven parser that reuses `extract_gate_events`'s shared `_split_capture_entry` and `_certificate_task_id` helpers.
- [x] Carry the per-task series on the `ArtifactBundle` as a typed sidecar. Option A: add an optional `taskWallClocks: dict[str, float] | None` field to `ArtifactBundle` (schema change required — extend `ArtifactBundle` in `canonical-types.schema.json` and `benchmark/harness/domain.py`). Option B: persist the series in a sibling JSON file referenced from the bundle's `transcript` path. Prefer Option A — the bundle is the canonical home for telemetry that drives a metric.
- [x] Rewrite `parallel_speedup_for_arm` to compute `speedup = sum(taskWallClocks.values()) / wallClockSeconds` per trial (the orchestrator's wall-clock is already on `Telemetry`); average across the arm's scored trials. Fall back to the present `sum / max` estimate (with a logged warning) only when `taskWallClocks` is absent — preserving behaviour on bundles produced before this task ships. Carry `graph_width` (already supplied by `dag_validity`) alongside the value so the "correlated with graph width" claim is readable in the same row.
- [x] Tests (`benchmark/tests/test_intra_trial_timing.py`): a synthetic bundle with `taskWallClocks = {01: 90, 02: 110, 03: 50, 04: 50}` and `wallClockSeconds = 200` yields `speedup = 300 / 200 = 1.5`; a bundle without `taskWallClocks` falls back to the old quantity and logs the fallback; the schema round-trip for `ArtifactBundle` still holds with the new optional field present and absent.
- [x] Update `parallel_speedup_for_arm`'s docstring to drop the "intra-campaign estimate" caveat — once `taskWallClocks` is present, the quantity is the one the spec defines.

## Definition of done

- [x] An A1 trial captured under the new path carries a populated `ArtifactBundle.taskWallClocks` whose keys match the plan's task ids and whose sum is ≤ `Telemetry.wallClockSeconds` (the orchestrator's own clock bounds the sum of its children). **Keys-match half structurally SATISFIED via `_certificate_task_id`; the sum-bound half is observational and `UNVERIFIED` until a live A1 run; the DoD wording also reads loose — sum CAN exceed wall when speedup > 1, which is the whole point of the metric.**
- [x] `parallel_speedup_for_arm` returns `sum(taskWallClocks) / wallClockSeconds` per trial on bundles that carry the series, and returns the present `sum / max` quantity (with a logged warning) on bundles that do not — so existing saved evidence still scores, just not against the spec definition.
- [x] Negative-space test: a single-task plan (`taskWallClocks` of length 1) yields `speedup = 1.0`, not a divide-by-zero or a nonsensical >1.
- [x] Schema delta applied: `canonical-types.schema.json` carries the new optional `ArtifactBundle.taskWallClocks` property; every existing record still validates against the schema.
- [x] Meets the repo definition of done (uv-locked deps, ruff format + lint clean, pyright clean, pytest clean, schema sidecar updated — see `plan.md` baseline).
- [x] Reviewable: a reviewer re-runs the live A1 test (or replays the saved A1 evidence through the updated path) and reads a `parallel_speedup` value computed from real per-task wall-clocks, with `graph_width = 4` on the seed instance. **Replay-fires-fallback half SATISFIED in-workspace (saved A1 evidence triggers the documented warning and returns `used_per_task_timing=False`); real-per-task-wall-clocks half UNVERIFIED — needs `BENCHMARK_RUN_A1_LIVE=1 uv run pytest benchmark/tests/ -k live` to produce a fresh A1 bundle whose certificates carry `Elapsed:` lines under the new directive.**

## Gate verdicts

- **Gate 1 — semi-formal review:** `VERDICT: CORRECT` / `CONFIDENCE: high`. Spec-defined ratio computed, back-compat fallback fires with a per-arm warning, schema delta is back-compat (`minimum: 0` on values), single-task plan = 1.0, zero-wall edge folded into the same default. 276 tests passed.
- **Gate 2 — validate done:** `VERDICT: PARTIAL` / `CONFIDENCE: high` — all in-workspace evidence SATISFIES; the strict-PARTIAL reading is driven solely by the live-A1 reproduce being `UNVERIFIED`-by-design. Per `build-loop.md`, `UNVERIFIED` is surfaced to the user, not re-dispatched.

## Open questions

- *Where per-task elapsed is written.* The first probe in §Steps decides between extending the certificate parser or amending the orchestrating prompt. If neither path is workable (`spec-builder` writes no per-task timing on either surface today), a third option is for the harness to time the certificate-write events from the transcript — a heavier lift the spec quantity may not be worth without a stronger reading of "sequentially".
