# benchmark

Design specs for the **spec-workflow benchmark** — a harness that measures the development workflow implemented by this repo's `spec-creator`, `spec-planner`, and `spec-builder` plugins against a plain single-agent baseline, using [SWE-bench Pro](https://scaleapi.github.io/SWE-bench_Pro-os/) as the baseline.

Read the global specs first: [`docs/specs/`](../specs/) (repo-wide design). The pages below are the benchmark's per-app spec set.

## Requirements

The harness runs on Python 3.13 with `uv` (see the repo-wide [development guidelines](../specs/development-guidelines.md)). **Docker is a peer dependency** — installed at the OS level, not via `uv` — required for the `container` backend, the production run/scoring path on the SWE-bench Pro and greenfield suites ([05-harness-architecture.md](specs/05-harness-architecture.md) → Backends). The `local` backend and the bundled `local-fixture` suite need no Docker, so the milestone-M0 pipeline (run → score → aggregate) runs without it.

## Specs (`docs/benchmark/specs/`)

| Page | Topic |
|---|---|
| [00-overview.md](specs/00-overview.md) | Problem, goals, system shape, scope |
| [01-domain-model.md](specs/01-domain-model.md) | Entities, IDs, lifecycles |
| [02-arms.md](specs/02-arms.md) | The five ablation arms and their pairwise deltas |
| [03-task-suites.md](specs/03-task-suites.md) | SWE-bench Pro public suite + greenfield feature suite |
| [04-metrics.md](specs/04-metrics.md) | Outcome, cost, process/artifact, robustness metrics |
| [05-harness-architecture.md](specs/05-harness-architecture.md) | Driver, containerization, BenchFlow substrate, scoring isolation |
| [06-scoring-and-statistics.md](specs/06-scoring-and-statistics.md) | Test oracle, conformance judge, gate probes, paired statistics |
| [canonical-types.schema.json](specs/canonical-types.schema.json) | Benchmark entity shapes as JSON Schema |

Status: **In progress** — milestone M0 (the Docker-free `local` pipeline) is implemented; the container milestones M1–M4 are specified but not yet built. See the [build plan](../plans/2026-05-27-spec_workflow_benchmark/plan.md).
