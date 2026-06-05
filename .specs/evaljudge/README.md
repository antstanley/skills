# eval-judge

Design specs for the **eval-judge harness** — a tool that runs each `spec-*` skill's `evals/evals.json` fixtures by invoking the skill live against each fixture's `prompt`, then uses an LLM judge to score the skill's actual behavior against the fixture's `expected_output`, producing a per-eval score, band, and PASS/FAIL verdict plus an aggregate pass rate.

Read the global specs first: [`.specs/`](../) (repo-wide design). The pages below are the eval-judge harness's per-app spec set.

> **Status: Draft — not yet built.** This spec set is the *target* the implementation will be built to match; the build happens in another environment. The bodies describe the intended design as the contract the code must satisfy. When the code lands under `benchmark/evaljudge/`, the status flips to `Built`.

## Relationship to the benchmark

The eval-judge harness lives under `benchmark/` (as `benchmark/evaljudge/`) and **reuses the benchmark's conformance-judge machinery** ([`benchmark/harness/scoring/conformance/`](../../benchmark/harness/scoring/conformance/)) — the injectable bounded `claude -p` judge, tolerant JSON parsing, `[0,1]` clamping, and calibration. It answers a *different* question from the benchmark: not "does the `spec-*` workflow beat a baseline on hidden-test resolution?" but "does each skill's live behavior match its own declared evals?" See [05-architecture.md](specs/05-architecture.md).

## Specs (`.specs/evaljudge/specs/`)

| Page | Topic |
|---|---|
| [00-overview.md](specs/00-overview.md) | Problem, goals, system shape, scope |
| [01-domain-model.md](specs/01-domain-model.md) | Entities, IDs, lifecycle — EvalCase, EvalRun, EvalJudgment, EvalResult, EvalReport |
| [02-run-stage.md](specs/02-run-stage.md) | Fixture discovery, live skill invocation, behavior capture, the run backend |
| [03-judge-stage.md](specs/03-judge-stage.md) | The rubric, the bounded judge call, score→band→verdict, calibration |
| [04-report-and-cli.md](specs/04-report-and-cli.md) | The EvalReport artifact, the opt-in entrypoint, exit status, gate posture |
| [05-architecture.md](specs/05-architecture.md) | Package layout, reuse of the benchmark judge, the two injectable seams, isolation |
| [canonical-types.schema.json](specs/canonical-types.schema.json) | eval-judge entity shapes as JSON Schema |

## Requirements

The harness runs on the repo-wide toolchain ([development guidelines](../development-guidelines.md)): Python 3.13, `uv`, ruff, pyright, pytest. It is **opt-in and live** — invoking skills and the judge spends model budget and needs an authenticated `claude` CLI, so it is gated behind `EVALJUDGE_RUN_LIVE=1` and is **not** part of `scripts/check.sh` (the default test path uses injected fakes and stays hermetic). This mirrors the benchmark's `BENCHMARK_RUN_*_LIVE` posture.
