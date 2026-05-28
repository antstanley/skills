# benchmark — the spec-workflow benchmark harness

Run instructions for the harness. The design lives in [`docs/benchmark/specs/`](../docs/benchmark/specs/); the build plan and certificates in [`docs/plans/2026-05-27-spec_workflow_benchmark/`](../docs/plans/2026-05-27-spec_workflow_benchmark/). This page is the *how to run it* companion.

## Package layout

```
benchmark/
  harness/
    domain.py           # entities (Campaign, Trial, Arm, TaskInstance, …)
    driver/             # run_campaign — matrix expand → drive → score → aggregate
    arms/               # A0–A4 recipes
    backends/           # local + container RunBackends + the shared Protocol
    scoring/            # local + container ScoringBackends, oracle, conformance, probes
    stats/              # outcome, cost+robustness, artifact metrics, ablation report
    telemetry/          # arm-agnostic Telemetry capture
    run_local_demo.py   # the Docker-free pipeline demo entrypoint
  suites/
    local-fixture/      # the bundled Docker-free verification instance
    greenfield-features/  # the authored ablation suite (text_toolkit, scheduler)
    benchflow-probe/    # the BenchFlow `bench tasks check` probe
  tests/                # the gate (`scripts/check.sh` runs this)
```

## Prerequisites

| Required for | Tool | Notes |
|---|---|---|
| Always | **`uv` 0.11+** | `~/.local/bin/uv`. `export PATH="$HOME/.local/bin:$PATH"` in every shell; system `python3` is 3.9 — never use it. |
| Always | **Python 3.13** | Materialised by `uv sync --frozen`. |
| Container run/scoring backends (M1+) | **Docker 25+** | Daemon must be reachable (`docker info`). Peer dependency — installed at the OS level, not via `uv`. |
| Live arm runs (A0–A4) | **`claude` CLI v2.1+** + OAuth credentials at `~/.claude/.credentials.json` | Run a local `claude` session once (or `/login`) before live runs; the credential file is mounted writable into agent containers so token refreshes persist in-container. |
| Live A1/A2/A3 only | **spec-* plugins installed at `~/.claude/plugins/marketplaces/skills/plugins/{spec-creator,spec-planner,spec-builder,reasoning-semiformally}`** | Each must carry a `.claude-plugin/plugin.json`; the run image bind-mounts them read-only. |

Set up the project once:

```sh
export PATH="$HOME/.local/bin:$PATH"
uv sync --frozen
```

## The gate

Every change is held to `scripts/check.sh` (`uv sync --frozen` → `ruff format --check` → `ruff check` → `pyright` → `pytest`). It is wired into a pre-push hook (`.githooks/pre-push`, enable with `git config core.hooksPath .githooks`) and CI (`.github/workflows/ci.yml`). To run it locally:

```sh
export PATH="$HOME/.local/bin:$PATH"
bash scripts/check.sh
```

A green gate is **262 passed + 5 skipped** — the five skips are the opt-in `BENCHMARK_RUN_*_LIVE` arms below, which spend real API budget and therefore never fire automatically.

> **Cost note for local runs of `check.sh`:** when Docker is reachable **and** host claude credentials are present, the **A0 baseline live test runs as part of the suite** (it has no env opt-in — only the recursive workflow arms do), so a local gate run costs ~$0.15 in API spend. CI has neither Docker nor credentials, so it skips the live A0 too.

## Running the harness

### 1 · The Docker-free local pipeline demo (no Docker, no API)

The fastest end-to-end exercise: the bundled `local-fixture` suite driven by the real `run_campaign` driver against the `local` backends, with a scripted fixture solver that emits the instance `goldPatch`. Deterministic, offline, free.

```sh
export PATH="$HOME/.local/bin:$PATH"
uv run python -m benchmark.harness.run_local_demo
```

Expected: the fixture solver yields **%Resolved = 1.0** and the no-op solver yields **%Resolved = 0.0** on the single fixture instance — the whole `run → score → aggregate` pipeline without Docker, BenchFlow, or an LLM.

### 2 · A greenfield campaign on the `container` backends (Docker required, live API)

A real ablation campaign provisions Docker containers from the per-instance run/scoring images and runs the arm's recipe inside them. The four live arms (`A0`, `A1`, `A2`/`A3`, `A4`) each have an opt-in test that drives one bounded run on the `text_toolkit` seed instance and saves evidence — the easiest way to exercise the end-to-end live path.

```sh
export PATH="$HOME/.local/bin:$PATH"
# A0 baseline (plain agent, ~$0.15, ~1 min)
BENCHMARK_RUN_A1_LIVE=  BENCHMARK_RUN_A2_A3_LIVE=  BENCHMARK_RUN_A4_LIVE= \
  uv run pytest -s -v benchmark/tests/test_container_run.py -k live
```

To drive a multi-arm campaign yourself (e.g. all five arms over a slice of greenfield), call `run_campaign` directly:

```python
from benchmark.harness.arms import A0, A1, A2, A3, A4
from benchmark.harness.backends import ContainerRunBackend
from benchmark.harness.scoring import ContainerScoringBackend
from benchmark.harness.driver import run_campaign
from benchmark.harness.domain import Campaign, new_record_id, CAMPAIGN_ID_PREFIX
from benchmark.suites.greenfield import load_instance, TEXT_TOOLKIT_SLUG
from datetime import datetime, timezone

campaign = Campaign(
    id=new_record_id(CAMPAIGN_ID_PREFIX),
    createdAt=datetime.now(timezone.utc).isoformat(),
    model="sonnet",
    arms=["A0", "A1", "A2", "A3", "A4"],
    suites=["greenfield-features"],
    trialsPerInstance=1,
)
instances = [load_instance(TEXT_TOOLKIT_SLUG)]
run = run_campaign(
    campaign,
    arms=[A0, A1, A2, A3, A4],
    instances=instances,
    run_backend=ContainerRunBackend(),
    scoring_backend=ContainerScoringBackend(),
    pool_size=1,                       # serialise the live arms; raise for parallel suite-wide runs
)
print(f"%Resolved = {run.raw_resolved_rate}")
```

The container images build on first use. The run side excludes the hidden suite (integrity rule); the scoring side is a fresh container with the hidden suite baked in.

### 3 · The live tests (one bounded run per arm; saves reviewable evidence)

The recursive workflow arms (A1, A2/A3, A4) and the live judge/probe spend real budget, so they are `pytest.mark.skipif` behind an env opt-in plus a Docker/credentials probe — `scripts/check.sh` and CI stay green by default. The A0 baseline is cheap (~$0.15) and runs **automatically** whenever Docker and host credentials are present.

| Live path | Env opt-in | Test | Cost cap | Typical observed | Saved evidence |
|---|---|---|---:|---:|---|
| A0 baseline | *(none — auto when Docker+creds)* | `test_container_run.py::test_live_a0_run_…` | $3 | ~$0.15, ~1 min | (asserted in-test) |
| A1 full pipeline | `BENCHMARK_RUN_A1_LIVE=1` | `test_a1_pipeline.py::test_live_a1_pipeline_…` | $20 | ~$1, ~7 min | `tests/_a1_live_evidence/` |
| A2 + A3 (gated/ungated) | `BENCHMARK_RUN_A2_A3_LIVE=1` | `test_a2_a3_arms.py::test_live_a2_a3_…` | $20 each | A2 ~$4 / ~19 min · A3 ~$2 / ~8 min | `tests/_a2_a3_live_evidence/{a2,a3}/` |
| A4 naive parallel | `BENCHMARK_RUN_A4_LIVE=1` | `test_a4_arm.py::test_live_a4_…` | $20 total (split N=4 → $5/agent) | ~$0.65, ~2 min | `tests/_a4_live_evidence/` |
| Conformance judge | `BENCHMARK_RUN_CONFORMANCE_LIVE=1` | `test_conformance.py::test_live_conformance_…` | $1 | ~$0.05, ~10 s | `tests/_conformance_live_evidence/` |
| Gate probe (catch rate) | `BENCHMARK_RUN_GATE_PROBE_LIVE=1` | `test_gate_probes.py::test_live_gate_probe_…` | $1 | ~$0.05, ~10 s | `tests/_gate_probe_live_evidence/` |

```sh
# Single live arm, single instance — the recommended way to exercise the path
BENCHMARK_RUN_A2_A3_LIVE=1 uv run pytest -s -v benchmark/tests/test_a2_a3_arms.py -k live
```

The saved evidence directories carry the patch, score report, telemetry, transcript, and any per-arm side data (GateEvents for A1/A2, merge conflicts for A4). They are durable artifacts — a reviewer reads them instead of re-spending budget.

#### The `BENCHMARK_RUN_CONTAINER_LIVE=1` live container witness

One more opt-in stitches the per-arm live paths into a single end-to-end runtime witness of the two-container split. With `BENCHMARK_RUN_CONTAINER_LIVE=1` set, `benchmark/tests/test_live_container.py::test_live_container_round_trip` calls `run_container_check()`, which on real Docker:

- runs the **A0 container round-trip** (provision the run container, run A0, score the captured patch in a *separate* scoring container) and asserts **resolved-parity** between the `container` and `local` scoring backends at both poles — the private reference solution (known-GOOD, resolves) and the no-op `None` patch (known-FALSE, does not resolve);
- asserts **run-image integrity** observed at runtime — the provisioned RUN image carries no `hidden/` path and none of the instance's hidden-test bodies (the hidden suite is scoring-side only);
- asserts **A2/A3 gate emission** — A2 surfaces ≥ 1 `GateEvent` and A3 zero, at both the backend (`last_gate_events`) and the driver-threaded (`TrialResult.gate_events`) layers;
- runs the **live `claude -p` gate probe** and asserts the review gate catches an injected off-by-one defect.

```sh
export PATH="$HOME/.local/bin:$PATH"
BENCHMARK_RUN_CONTAINER_LIVE=1 uv run pytest -s -v benchmark/tests/test_live_container.py -k live
```

Prerequisites (all three, or the test SKIPs cleanly): **Docker ≥ 25** with a reachable daemon, an **authenticated `claude` CLI on `PATH`** (the A0 run side and the live gate probe both invoke it), and a **small real budget** (it spends the recursive-workflow + probe API cost — a few dollars, bounded by the existing per-probe caps). Unset / not `1`, or Docker/CLI missing, and the test reports SKIPPED — `scripts/check.sh` and CI stay green, never touching Docker.

**Evidence refresh is conditional and operator-run.** A green live run MAY regenerate the `benchmark/tests/_a*_live_evidence/` bundles, but that is an explicit operator action, not a CI step — whether to promote a fresh witness to the committed evidence is an open question (auto-vs-manual promotion; see [plan.md](../docs/plans/2026-05-28-add_live_container_verification/plan.md)).

### 4 · Rendering the ablation report

Once you have a `CampaignRun` (live or replayed from saved score reports), build the full ablation table:

```python
from benchmark.harness.stats import build_ablation_report, render_ablation_report

report = build_ablation_report(
    run=run,
    suite="greenfield-features",
    # supply the captured artifacts the per-arm metrics need:
    plan_artifacts_by_arm={...},
    spec_artifacts_by_arm={...},
    conformance_scores_by_arm_trial={...},
    catch_rates_by_arm={...},
    escape_inputs_by_arm={...},
    merge_conflict_counts_by_trial={...},
)
print(render_ablation_report(report))
```

The output is Markdown: five arm rows × every metric column (Pass@1 with Wilson CI, cost-matched %Resolved, regression rate, conformance, gate catch/escape, plan coverage, DAG validity, robustness columns), then the four pairwise-delta rows (A1−A0, A1−A2, A2−A3, A1−A4) with their McNemar χ², raw p-value, and Holm–Bonferroni-adjusted p-value (α = 0.05). N/A cells are distinguished from a measured 0.

## Pinned decisions (resolved Open questions)

- **Cost-matching basis:** dollars (`Telemetry.costUsd`); `CostBasis.TOKENS` / `CostBasis.WALL_CLOCK` selectable per call (`stats/cost_robustness.py`).
- **Multiple-comparison correction:** Holm–Bonferroni at α = 0.05 over the four pairwise deltas (`HOLM_BONFERRONI_ALPHA` in `stats/ablation_report.py`).
- **Given-spec provenance (A2/A3):** frozen per-instance `given_spec.md` shared identically between A2 and A3 — `benchmark/suites/greenfield-features/<slug>/given_spec/`.
- **A4 decomposition:** fixed identical-statement N-way split with no planning (`arms/a4.py`); `N` matches A1's task count on the seed.
- **BenchFlow substrate:** `bench tasks check` is used for task authoring/validation; the two-container run/scoring split stays on this benchmark's own `RunBackend`/`ScoringBackend` seam (recorded in `harness/substrate.py`).

## Common pitfalls

- **System `python3` is 3.9.** Always invoke `uv run` after `export PATH="$HOME/.local/bin:$PATH"`. A `uv: command not found` is the usual symptom of a missed `PATH` export.
- **Docker daemon down.** Container backends raise a clear `ContainerRunError`. Start the daemon (`sudo systemctl start docker`) and ensure non-sudo access (member of the `docker` group, or socket permissions).
- **In-container `claude` 401 "Please run /login".** The host OAuth token expired; re-login (`claude` once, or `/login` in Claude Code) and retry. The credential copy is taken at run start, so long live runs need a host token valid for the run's duration.
- **A1 under-builds on a single orchestrator turn.** Known limitation (see [task 08](../docs/plans/2026-05-27-spec_workflow_benchmark/08-arm_a1_pipeline.md) Open questions): the single `claude -p` ends its turn after ~1 plan task on the seed. The harness mechanism is correct; the headline A1−A0 delta is bounded by this until the orchestration is tuned (continuation loop / higher turn budget).
- **Stale Docker images.** If a `:scoring` or `:run` greenfield image was built before a Dockerfile change (e.g. before `pytest` was baked into the scoring image), per-selector scoring runs will fail silently. `docker rmi -f $(docker images -q 'greenfield-*')` and let the next run rebuild.

## Related docs

- Design specs: [`docs/benchmark/specs/`](../docs/benchmark/specs/) — start at [`00-overview.md`](../docs/benchmark/specs/00-overview.md).
- Build plan + certificates: [`docs/plans/2026-05-27-spec_workflow_benchmark/`](../docs/plans/2026-05-27-spec_workflow_benchmark/).
- Repo-wide development guidelines: [`docs/specs/development-guidelines.md`](../docs/specs/development-guidelines.md).
