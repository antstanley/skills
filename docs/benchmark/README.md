# benchmark

Design specs for the **spec-workflow benchmark** — a harness that measures the development workflow implemented by this repo's `spec-creator`, `spec-planner`, and `spec-builder` plugins against a plain single-agent baseline, using [SWE-bench Pro](https://scaleapi.github.io/SWE-bench_Pro-os/) as the baseline.

Read the global specs first: [`docs/specs/`](../specs/) (repo-wide design). The pages below are the benchmark's per-app spec set.

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

Status: **Draft** — this is a design spec; no component is implemented yet.
