# Task 06 — Telemetry capture

**Plan:** [plan.md](../plan.md) · **Certificate:** [06-telemetry_capture-certificate.md](06-telemetry_capture-certificate.md)

**Implements:** [04-metrics.md](../../../benchmark/specs/04-metrics.md) §Bucket 2 — Cost and efficiency (sources), [05-harness-architecture.md](../../../benchmark/specs/05-harness-architecture.md) §Implementation layout (telemetry)
**Depends on:** 05
**Produces:** every run records `inputTokens`, `outputTokens`, `costUsd`, `wallClockSeconds`, and `agentTurns` into `ArtifactBundle.telemetry`, uniformly across arms
**Pointers:** `benchmark/harness/telemetry/`; wraps the run loop from task 05

## Steps

- [ ] Capture token counts, dollar cost, wall-clock, and agent-turn count around a run and write them into `Telemetry`.
- [ ] Make capture arm-agnostic so the plain A0 baseline reports at the same granularity as the plugin arms.
- [ ] Persist telemetry into the `ArtifactBundle` alongside the patch and transcript.
- [ ] Add a test asserting all five telemetry fields are present and non-negative after an A0 run.
- [ ] If A0 cannot expose token/cost at the same granularity as plugin arms, record the gap in plan.md's Open questions.

## Definition of done

- [ ] An A0 run yields a `Telemetry` record with all five fields populated and non-negative.
- [ ] Capture is uniform across arms, or the A0 granularity gap is documented.
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer inspects the `ArtifactBundle` from an A0 run and sees complete telemetry.
