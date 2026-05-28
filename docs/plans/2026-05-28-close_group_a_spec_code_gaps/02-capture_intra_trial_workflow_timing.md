# Task 02 — Capture intra-trial workflow timing for honest parallel speedup

**Plan:** [plan.md](plan.md) · **Status:** Todo

**Implements:** [04-metrics.md](../../benchmark/specs/04-metrics.md) §Bucket 2 — Cost and efficiency, "Parallel speedup = A1's wall-clock vs the same plan run sequentially, correlated with task-graph width."
**Depends on:** —
**Produces:** `ContainerRunBackend._run_workflow_arm` records per-task wall-clocks alongside the orchestrator's wall-clock; the `ArtifactBundle` carries the per-task series in a typed sidecar; `parallel_speedup_for_arm` is rewritten to read the series and return `sum(per-task wall-clocks) / orchestrator wall-clock` — the quantity the spec defines, not the intra-campaign `sum / max` the docstring is candid about today.
**Pointers:** `benchmark/harness/backends/container.py:677` (`_run_workflow_arm`); `benchmark/harness/arms/a2_a3.py:311` (`extract_gate_events`, the captured-certificate parser the timing capture can reuse if certificates carry an elapsed line); `benchmark/harness/domain.py:361` (`Telemetry`); `benchmark/harness/domain.py:372` (`ArtifactBundle`); `benchmark/harness/stats/cost_robustness.py:309` (`parallel_speedup_for_arm`, the consumer).

## Steps

- [ ] Decide where per-task wall-clocks come from. First probe: do the discharged done-certificates `extract_gate_events` already parses carry an `Elapsed:`/`Duration:` line? If so, extend the parser to surface per-task elapsed seconds alongside the verdict. Second probe: if certificates do not carry the line, add an instruction to the A1/A2/A3 orchestrating prompts telling `spec-builder` to write a per-task `elapsed_seconds` line into each certificate (or into a sibling JSONL log). Pick the smaller of the two; document the choice in `_run_workflow_arm`'s docstring.
- [ ] Carry the per-task series on the `ArtifactBundle` as a typed sidecar. Option A: add an optional `taskWallClocks: dict[str, float] | None` field to `ArtifactBundle` (schema change required — extend `ArtifactBundle` in `canonical-types.schema.json` and `benchmark/harness/domain.py`). Option B: persist the series in a sibling JSON file referenced from the bundle's `transcript` path. Prefer Option A — the bundle is the canonical home for telemetry that drives a metric.
- [ ] Rewrite `parallel_speedup_for_arm` to compute `speedup = sum(taskWallClocks.values()) / wallClockSeconds` per trial (the orchestrator's wall-clock is already on `Telemetry`); average across the arm's scored trials. Fall back to the present `sum / max` estimate (with a logged warning) only when `taskWallClocks` is absent — preserving behaviour on bundles produced before this task ships. Carry `graph_width` (already supplied by `dag_validity`) alongside the value so the "correlated with graph width" claim is readable in the same row.
- [ ] Tests (`benchmark/tests/test_intra_trial_timing.py`): a synthetic bundle with `taskWallClocks = {01: 90, 02: 110, 03: 50, 04: 50}` and `wallClockSeconds = 200` yields `speedup = 300 / 200 = 1.5`; a bundle without `taskWallClocks` falls back to the old quantity and logs the fallback; the schema round-trip for `ArtifactBundle` still holds with the new optional field present and absent.
- [ ] Update `parallel_speedup_for_arm`'s docstring to drop the "intra-campaign estimate" caveat — once `taskWallClocks` is present, the quantity is the one the spec defines.

## Definition of done

- [ ] An A1 trial captured under the new path carries a populated `ArtifactBundle.taskWallClocks` whose keys match the plan's task ids and whose sum is ≤ `Telemetry.wallClockSeconds` (the orchestrator's own clock bounds the sum of its children).
- [ ] `parallel_speedup_for_arm` returns `sum(taskWallClocks) / wallClockSeconds` per trial on bundles that carry the series, and returns the present `sum / max` quantity (with a logged warning) on bundles that do not — so existing saved evidence still scores, just not against the spec definition.
- [ ] Negative-space test: a single-task plan (`taskWallClocks` of length 1) yields `speedup = 1.0`, not a divide-by-zero or a nonsensical >1.
- [ ] Schema delta applied: `canonical-types.schema.json` carries the new optional `ArtifactBundle.taskWallClocks` property; every existing record still validates against the schema.
- [ ] Meets the repo definition of done (uv-locked deps, ruff format + lint clean, pyright clean, pytest clean, schema sidecar updated — see `plan.md` baseline).
- [ ] Reviewable: a reviewer re-runs the live A1 test (or replays the saved A1 evidence through the updated path) and reads a `parallel_speedup` value computed from real per-task wall-clocks, with `graph_width = 4` on the seed instance.

## Open questions

- *Where per-task elapsed is written.* The first probe in §Steps decides between extending the certificate parser or amending the orchestrating prompt. If neither path is workable (`spec-builder` writes no per-task timing on either surface today), a third option is for the harness to time the certificate-write events from the transcript — a heavier lift the spec quantity may not be worth without a stronger reading of "sequentially".
