# Task 14 — Workflow-artifact metrics

**Plan:** [plan.md](plan.md) · **Status:** Todo · **Certificate:** [certificates/14-workflow_artifact_metrics.md](certificates/14-workflow_artifact_metrics.md)

**Implements:** [04-metrics.md](../../benchmark/specs/04-metrics.md) §Bucket 3 (plan coverage, DAG validity, gate catch rate, false-`Done` escape rate); [06-scoring-and-statistics.md](../../benchmark/specs/06-scoring-and-statistics.md) §Gate-efficacy probes
**Depends on:** 08, 10, 12
**Produces:** plan coverage and DAG validity from plan artifacts, gate catch rate from injected defects, and false-`Done` escape rate
**Pointers:** `benchmark/harness/scoring/probes/`, plan-artifact analysis in `benchmark/harness/stats/`

## Steps

- [ ] Compute plan coverage (fraction of in-scope spec sections mapped to ≥1 task) and DAG validity (acyclic, edges resolve) from the captured `planArtifacts`.
- [ ] Generate `InjectedDefect`s (classified by `defectKind`), inject each into a gated build, and record whether a gate flagged it (`caughtBy`) — the catch rate.
- [ ] Compute false-`Done` escape rate from `ScoreReport.gateEscape`, attributing per-task via `testTags` where present (greenfield) and falling back to instance granularity otherwise.
- [ ] Restrict each metric to the arms it applies to: coverage/DAG to A1/A2/A3; gate metrics to A1/A2.
- [ ] Add tests with known-bad patches that the catch rate counts a caught defect and an escaped one correctly.

## Definition of done

- [ ] Catch rate and escape rate are produced for the gated arms; plan coverage and DAG validity for the plan-producing arms.
- [ ] Per-task escape attribution works where `testTags` exist and falls back to instance granularity where they do not.
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer injects a known defect, sees it counted as caught or escaped, and reads the coverage and DAG-validity figures for a workflow trial.
