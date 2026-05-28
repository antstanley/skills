# 05 — Harness Architecture

This page defines how the benchmark runs: the driver that executes a Campaign, the containerization that isolates each Trial, the BenchFlow substrate, and the scoring-isolation rule that keeps the workflow's gates from seeing the oracle. The entities it operates on are defined in [01-domain-model.md](01-domain-model.md); the scoring it feeds is defined in [06-scoring-and-statistics.md](06-scoring-and-statistics.md).

---

## Responsibilities

The harness owns the execution of a Campaign: expanding the Arms × Suites × Trials matrix into Trials, provisioning a container per Trial, running the arm to completion, capturing the candidate patch and artifact bundle, and handing them to scoring. It does **not** decide whether a candidate resolved (that is the oracle, [06-scoring-and-statistics.md](06-scoring-and-statistics.md)) and it does **not** decide what to measure (that is [04-metrics.md](04-metrics.md)).

The harness owns one invariant above all others: **the run environment and the scoring environment are separate containers, and the hidden test suite exists only in the latter.**

The driver also re-keys `GateEvent`s onto the Trial. A `RunBackend` that surfaces gate activity (the `container` backend on the workflow arms A1 and A2) accumulates events on a `last_gate_events` attribute during each `run()` call; the driver reads that attribute via duck-typing, rewrites each event's `trial` field to the current Trial's id, and attaches the re-keyed tuple to `TrialResult.gate_events`. The `CampaignRun` aggregates the per-trial gate events. This contract is **backend-neutral**: a backend without a `last_gate_events` attribute (the `local` backend, the A0 path on the `container` backend) contributes the empty tuple, and the `RunBackend` Protocol itself does not require the attribute. Gate-efficacy metrics ([04-metrics.md](04-metrics.md) → Bucket 3, [06-scoring-and-statistics.md](06-scoring-and-statistics.md) → §Gate-efficacy probes) read from `TrialResult.gate_events`, not from the backend.

---

## Component shape

```
   Campaign record
        │  expand matrix
        ▼
   ┌──────────────┐     reads Arm + TaskInstance
   │   driver     │────────────────────────────────────┐
   │ (scheduler)  │                                     │
   └──────┬───────┘                                     ▼
          │ per Trial                          ┌──────────────────┐
          ▼                                    │  Arm registry    │
   ┌────────────────────────────┐             │  (provisioning   │
   │  RUN CONTAINER              │             │   recipes)       │
   │  base = TaskInstance.image  │             └──────────────────┘
   │  + arm's plugins installed  │
   │  + jj/git available         │
   │  NO hidden tests present    │
   │  → CandidatePatch           │
   │  → ArtifactBundle           │
   └──────────────┬──────────────┘
                  │ patch + bundle (no test data crossed in)
                  ▼
   ┌────────────────────────────┐
   │  SCORING CONTAINER (clean)  │   defined in 06-scoring-and-statistics.md
   │  base image, apply patch,   │
   │  inject hidden failToPass / │
   │  passToPass, run oracle     │
   │  → ScoreReport              │
   └────────────────────────────┘
```

The driver is a scheduler over the Trial lifecycle (`queued → provisioning → running → captured → scored → aggregated`, [01-domain-model.md](01-domain-model.md)). Run and scoring are two distinct containers; nothing from the scoring side is ever mounted into the run side.

---

## Substrate — BenchFlow

The harness uses the **BenchFlow `bench` SDK** ([benchflow-ai/benchflow](https://github.com/benchflow-ai/benchflow)) as a complementary layer for task authoring and validation — `bench tasks init` and `bench tasks check` validate a probe task in `benchmark/suites/benchflow-probe/` against BenchFlow's task layout, so the benchmark stays compatible with that SDK without depending on it for runtime execution.

The **runtime substrate** for the two-container split and the custom `TaskInstance` schema is the benchmark's own `RunBackend` / `ScoringBackend` seam, recorded as a substrate finding in `benchmark/harness/substrate.py` (named constants `BENCH_TASKS_CLI_AVAILABLE = True`, `BENCH_NATIVE_TWO_CONTAINER_SPLIT = False`, `BENCH_VALIDATES_TASKINSTANCE_SCHEMA = False`). BenchFlow's stock `bench eval create` runs an agent rollout in the task's single sandbox and then runs the verifier in that same sandbox; the benchmark's integrity rule (a fresh scoring container distinct from the run container, hidden tests injected only there) is not expressible in that eval model, so the run/scoring split lives on the benchmark's own seam. Reusing BenchFlow for authoring keeps the probe task discoverable by `bench tasks check`; the bespoke surface shrinks to the two backend protocols and the arm provisioning recipes.

---

## Backends

The run side and the scoring side are each a **pluggable backend** behind a fixed interface, so the driver, the scorer's resolution rule, and the statistics are agnostic to how a trial is actually run and scored.

- **`RunBackend`** — provisions an environment, runs an arm (or a fixture solver) against a `TaskInstance`, and returns a `candidatePatch` plus an `ArtifactBundle`. Implementations: `container` (provision from the instance's `dockerImage`, install the arm's plugins, run in the container — the production default) and `local` (run in an isolated temp working directory / subprocess, no Docker).
- **`ScoringBackend`** — applies a `candidatePatch` to a clean copy of the instance base, injects the hidden tests, runs them, and returns a `ScoreReport`. Implementations: `container` (a fresh scoring container running the suite's hidden tests) and `local` (a fresh temp checkout, hidden tests run as a local subprocess).

A `Campaign` selects the backend (`backend: container | local`, default `container`). The `local` backend requires only Python, `uv`, and the repo under test; the `container` backend requires Docker and the prebuilt images. The two backends honour the **same** integrity rule (below): the run side never sees the hidden tests, whichever backend runs.

`RunBackend.run` takes a polymorphic second argument — an `Arm` record (a real arm A0–A4) or a solver-mode slug string (a `Campaign.solver` value such as `"fixture"`). The `ArmOrSolver` alias in `benchmark/harness/backends/interfaces.py` names this input shape. The `local` `RunBackend` plus the `fixture` solver is the deterministic Docker-free path the run-local demo uses; the `container` `RunBackend` plus a real `Arm` is the production path. The two backends and the two solvers compose freely.

---

## Run container

The run side is a **`RunBackend`** (see [Backends](#backends)). The `container` `RunBackend` provisions a run container per trial from the instance's `dockerImage` with `jj` and `git` available, installs the arm's plugin set, runs the arm to completion, and extracts the `candidatePatch` (the diff of the working state against `baseCommit`) and the `ArtifactBundle`. The `local` `RunBackend` does the same in an isolated temp working directory checked out at `baseCommit` — no container — for arms whose execution does not require one and for the fixture solver. Neither backend's run environment carries any hidden test content.

The `container` backend provisions from the TaskInstance's `dockerImage` — for the greenfield suite, an image built for the instance from its skeleton repo, with the hidden test suite **excluded** from this image.

Onto the base, the driver installs the arm's plugin set (per the `Arm` record) and ensures `jj` and `git` are present, since `spec-builder` selects its workspace backend itself (jj preferred). The arm runs non-interactively to completion. On finish, the driver extracts the candidate patch (the diff of the working state, or the integration tip, against `baseCommit`) and the artifact bundle (specs, plans, certificates, transcript, telemetry), then discards the run environment.

---

## Scoring isolation — the integrity rule

This is the rule the harness exists to enforce, and the reason run and scoring are separate environments.

> The workflow's own gates — `semi-formal-review` and `validate-done-certificate` — operate **only** on each task's definition of done. They never see the hidden `failToPass` / `passToPass` suite, which is introduced only on the scoring side. The rule holds across **both** backends:
>
> - The `container` `ScoringBackend` injects the hidden tests into a fresh scoring container, separate from the run container.
> - The `local` `ScoringBackend` injects them into a fresh temp checkout in a directory distinct from the run working directory, run as a separate process.
>
> In both cases the run side and the scoring side are different filesystems/processes, and the hidden suite exists only on the scoring side.

Without this separation, a workflow arm could discharge its gates against the very tests it is later scored on, overfitting the metric and making the gate-efficacy numbers ([04-metrics.md](04-metrics.md)) meaningless. The greenfield suite enforces this separation by construction, baking the hidden tests only into the scoring image. The gate-efficacy probes ([06-scoring-and-statistics.md](06-scoring-and-statistics.md)) depend entirely on this rule holding.

---

## Runtime verification

The integrity rule and the two-container split are enforced in code and covered by unit tests with injected backends; a separate **opt-in live self-test** proves they hold against real Docker and a real model, so `Status: Built` is runtime-checkable rather than review-only. It is gated behind `BENCHMARK_RUN_CONTAINER_LIVE=1` (mirroring the gate probe's `BENCHMARK_RUN_GATE_PROBE_LIVE`) and is skipped by default — CI and `check.sh` never pay its Docker or token cost. The entrypoint is `benchmark/harness/run_container_check.py`; the default-skipped pytest wrapper is `benchmark/tests/test_live_container.py`.

When enabled, the self-test runs one greenfield instance end to end on the `container` backends and asserts, with known answers:

- **Provisioning + capture.** The `container` `RunBackend` builds/loads the instance run image, runs a bounded real arm (A0 by default; A1/A2/A3 when a budget is supplied), and returns a `candidatePatch` plus an `ArtifactBundle`.
- **The integrity rule, observed not assumed.** The run image carries no file from the instance's `hidden/` tree and no `failToPass` / `passToPass` selector content — checked by inspecting the provisioned image, not by trusting the build.
- **Two-container scoring.** The `container` `ScoringBackend` stands up a *fresh* scoring image (hidden suite overlaid) distinct from the run container and produces a `ScoreReport` whose `resolved` verdict matches the `local` backend's verdict on the same patch — the shared resolution rule, proven identical across backends.
- **Gate emission.** On A2 the captured certificates yield ≥ 1 `GateEvent` and on A3 zero, threaded onto the `TrialResult` exactly as the metrics consume them.
- **The live `claude -p` gate probe.** `run_gate_probe` with the real `cli_review_gate` reviewer issues one bounded `claude -p` review of a known-bad diff and maps the returned verdict to `caughtBy` ([06-scoring-and-statistics.md](06-scoring-and-statistics.md) → §Gate-efficacy probes).

A green run refreshes the `benchmark/tests/_a*_live_evidence/` bundles; the captured evidence remains the default, zero-cost regression surface for everything downstream.

---

## Concurrency and reproducibility

| Concern | Handling |
|---|---|
| **Trial parallelism** | The driver runs independent Trials concurrently up to a configured pool size; Trials are independent by construction (separate containers, separate instances). |
| **Intra-arm parallelism** | A1/A2/A3 run `spec-builder`'s own wave scheduler *inside* the run container; that concurrency is the arm's, not the driver's. |
| **Determinism** | Each Trial records its `seed`; locked dependencies (BenchFlow `uv.lock`-style) fix the toolchain. Residual agent nondeterminism is handled by repetition and Pass@k ([06-scoring-and-statistics.md](06-scoring-and-statistics.md)). |
| **Infra failure** | A container that fails to provision or crashes mid-run sets the Trial to `failed` and is excluded from metrics and re-queued — distinct from a legitimate `resolved: false` ([01-domain-model.md](01-domain-model.md)). |
| **Live verification** | The opt-in container self-test (`BENCHMARK_RUN_CONTAINER_LIVE=1`) runs serially against real Docker, bounded by a per-call budget cap; default-skipped so routine runs stay Docker-free and deterministic. |

---

## Implementation layout

```
benchmark/
  harness/
    driver/            # matrix expansion, Trial scheduler, lifecycle
    backends/          # RunBackend / ScoringBackend Protocols + container + local impls
    arms/              # one provisioning recipe per Arm (plugins, flags, exec mode)
    scoring/           # the clean-container oracle runner + shared resolution rule
    telemetry/         # token/cost/wall-clock/turn capture → ArtifactBundle.telemetry
    stats/             # binomial CIs, McNemar, Pass@k, cost-matching, ablation-table render (see 04, 06)
    domain.py          # entity records (Campaign, Trial, ScoreReport, …; see 01)
    substrate.py       # the BenchFlow substrate finding (see §Substrate)
    run_local_demo.py  # Docker-free pipeline demo entrypoint
    run_container_check.py  # opt-in live container + claude -p self-test (BENCHMARK_RUN_CONTAINER_LIVE)
  suites/              # TaskInstance records + greenfield skeletons + local-fixture + benchflow-probe (see 03)
```

---

## Assumptions and open questions

**Assumptions**

- BenchFlow's SDK can host a benchmark with this TaskInstance schema, per-arm provisioning, and a two-container scoring split without forking it.
- The `spec-*` plugins run unattended in a container with no interactive prompts, given the non-interactive defaults the plugins document.
- Per-arm telemetry can be captured uniformly, including for the plain A0 baseline.

**Decisions**

- *Run and scoring are separate containers.* **Hidden tests live only in scoring.** This is the integrity backbone; collapsing them into one container would let the gates overfit the oracle and void the gate-efficacy metrics.
- *Build on BenchFlow only for task authoring.* **`bench tasks check` is wired against a probe; the runtime two-container split stays on the benchmark's own backend seam.** BenchFlow's stock eval runs the agent and the verifier in one sandbox, which collapses the integrity rule. The substrate finding in `benchmark/harness/substrate.py` records this narrowing; the bespoke surface is the two backend protocols.
- *Intra-arm concurrency belongs to the arm, not the driver.* **`spec-builder`'s waves run inside the run container.** Pulling that scheduling into the driver would change the system under test; the benchmark must run the workflow as it actually executes.

**Open questions**

- *Greenfield image build.* **Resolved.** The two-image build (`benchmark/suites/greenfield_images.py`) builds a run image that copies only `base/` and a scoring image that overlays `hidden/`; the live runtime verification (§Runtime verification) confirms at runtime that the run image carries no hidden-test content. The build-arg-vs-two-Dockerfiles question is settled in favour of two Dockerfiles from a shared base.
- *Patch extraction for parallel arms.* Deriving one clean `candidatePatch` from a multi-merge integration tip (shared with [01-domain-model.md](01-domain-model.md)) needs an implementation that survives conflict resolution without smuggling test files into the diff.
- *Telemetry fidelity for A0.* Whether the plain baseline exposes token/cost counts at the same granularity as the plugin arms is unconfirmed.
