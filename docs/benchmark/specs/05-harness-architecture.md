# 05 — Harness Architecture

This page defines how the benchmark runs: the driver that executes a Campaign, the containerization that isolates each Trial, the BenchFlow substrate, and the scoring-isolation rule that keeps the workflow's gates from seeing the oracle. The entities it operates on are defined in [01-domain-model.md](01-domain-model.md); the scoring it feeds is defined in [06-scoring-and-statistics.md](06-scoring-and-statistics.md).

---

## Responsibilities

The harness owns the execution of a Campaign: expanding the Arms × Suites × Trials matrix into Trials, provisioning a container per Trial, running the arm to completion, capturing the candidate patch and artifact bundle, and handing them to scoring. It does **not** decide whether a candidate resolved (that is the oracle, [06-scoring-and-statistics.md](06-scoring-and-statistics.md)) and it does **not** decide what to measure (that is [04-metrics.md](04-metrics.md)).

The harness owns one invariant above all others: **the run environment and the scoring environment are separate containers, and the hidden test suite exists only in the latter.**

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

The harness is built on the **BenchFlow `bench` SDK** (the substrate behind [benchflow-ai/skillsbench](https://github.com/benchflow-ai/skillsbench)) rather than a bespoke runner. BenchFlow already provides task init/validation (`bench tasks init`, `bench tasks check`), evaluation execution (`bench eval create`), a runnable/excluded task split, and locked dependencies for reproducibility. The benchmark supplies its own TaskInstance schema, Arm provisioning recipes, and scoring step on top.

Reusing BenchFlow keeps the bespoke surface to what is genuinely specific to this benchmark — the arm provisioning and the two-container scoring split — and inherits a maintained harness for everything else.

---

## Run container

Provisioned per Trial from the TaskInstance's `dockerImage`:

- **Issue-fixing suite** — the SWE-bench Pro `jefzda/sweap-images` tag for the instance, reused as-is.
- **Greenfield suite** — an image built for the instance from its skeleton repo, with the hidden test suite **excluded** from this image.

Onto the base, the driver installs the arm's plugin set (per the `Arm` record) and ensures `jj` and `git` are present, since `spec-builder` selects its workspace backend itself (jj preferred). The arm runs non-interactively to completion. On finish, the driver extracts the candidate patch (the diff of the working state, or the integration tip, against `baseCommit`) and the artifact bundle (specs, plans, certificates, transcript, telemetry), then discards the container.

---

## Scoring isolation — the integrity rule

This is the rule the harness exists to enforce, and the reason run and scoring are separate containers.

> The workflow's own gates — `semi-formal-review` and `validate-done-certificate` — operate **only** on each task's definition of done. They never see the hidden `failToPass` / `passToPass` suite. The hidden suite is injected only into the clean scoring container, after the run container is gone.

Without this separation, a workflow arm could discharge its gates against the very tests it is later scored on, overfitting the metric and making the gate-efficacy numbers ([04-metrics.md](04-metrics.md)) meaningless. SWE-bench Pro gives this separation for free on the issue-fixing suite — the test patch is held out of the agent's environment — and the greenfield suite enforces it by construction, baking the hidden tests only into the scoring image. The gate-efficacy probes ([06-scoring-and-statistics.md](06-scoring-and-statistics.md)) depend entirely on this rule holding.

---

## Concurrency and reproducibility

| Concern | Handling |
|---|---|
| **Trial parallelism** | The driver runs independent Trials concurrently up to a configured pool size; Trials are independent by construction (separate containers, separate instances). |
| **Intra-arm parallelism** | A1/A2/A3 run `spec-builder`'s own wave scheduler *inside* the run container; that concurrency is the arm's, not the driver's. |
| **Determinism** | Each Trial records its `seed`; locked dependencies (BenchFlow `uv.lock`-style) fix the toolchain. Residual agent nondeterminism is handled by repetition and Pass@k ([06-scoring-and-statistics.md](06-scoring-and-statistics.md)). |
| **Infra failure** | A container that fails to provision or crashes mid-run sets the Trial to `failed` and is excluded from metrics and re-queued — distinct from a legitimate `resolved: false` ([01-domain-model.md](01-domain-model.md)). |

---

## Implementation layout

```
benchmark/
  harness/
    driver/            # matrix expansion, Trial scheduler, lifecycle
    arms/              # one provisioning recipe per Arm (plugins, flags, exec mode)
    scoring/           # the clean-container oracle runner (see 06)
    telemetry/         # token/cost/wall-clock/turn capture → ArtifactBundle.telemetry
  suites/              # TaskInstance records + greenfield skeletons (see 03)
```

---

## Assumptions and open questions

**Assumptions**

- BenchFlow's SDK can host a benchmark with this TaskInstance schema, per-arm provisioning, and a two-container scoring split without forking it.
- The `spec-*` plugins run unattended in a container with no interactive prompts, given the non-interactive defaults the plugins document.
- Per-arm telemetry can be captured uniformly, including for the plain A0 baseline.

**Decisions**

- *Run and scoring are separate containers.* **Hidden tests live only in scoring.** This is the integrity backbone; collapsing them into one container would let the gates overfit the oracle and void the gate-efficacy metrics.
- *Build on BenchFlow rather than bespoke.* **Reuse the `bench` SDK.** It already solves task validation, eval execution, and locked reproducibility; the bespoke surface shrinks to arm provisioning and the scoring split.
- *Intra-arm concurrency belongs to the arm, not the driver.* **`spec-builder`'s waves run inside the run container.** Pulling that scheduling into the driver would change the system under test; the benchmark must run the workflow as it actually executes.

**Open questions**

- *Greenfield image build.* What is the cleanest way to bake hidden tests into the scoring image while guaranteeing they are absent from the run image — two Dockerfiles from a shared base, or a build arg that gates the test layer?
- *Patch extraction for parallel arms.* Deriving one clean `candidatePatch` from a multi-merge integration tip (shared with [01-domain-model.md](01-domain-model.md)) needs an implementation that survives conflict resolution without smuggling test files into the diff.
- *Telemetry fidelity for A0.* Whether the plain baseline exposes token/cost counts at the same granularity as the plugin arms is unconfirmed.
