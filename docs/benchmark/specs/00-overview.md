# spec-workflow-benchmark — Design Overview

**Status:** Draft · **Date:** 2026-05-27 · **Owner:** Ant Stanley · **Scope:** apps/benchmark

The **spec-workflow benchmark** (`docs/benchmark/`) is a harness that measures the software-development workflow implemented by this repo's three `spec-*` plugins — `spec-creator`, `spec-planner`, `spec-builder` — against a plain single-agent baseline, on shared task suites with hidden test oracles.

This document is the entry point for the benchmark's design. It states the problem, the goals, the system shape, and the scope. Detail pages are linked from each section.

No component described here is implemented. This page and its siblings define the intended design; `Status: Draft` records that the build has not started. The implementation sequence is an Open question, deferred to a separate plan (see [§Assumptions and open questions](#assumptions-and-open-questions)).

---

## Problem

The `spec-*` plugins implement a multi-stage workflow: `spec-creator` writes a formal spec, `spec-planner` decomposes it into a dependency-ordered task graph with a definition of done per task, and `spec-builder` executes each task in an isolated workspace behind two review gates before merging. The workflow is a substantial scaffold around whatever base model runs it. Whether that scaffold produces better software than the same model used plainly — and whether each stage earns its token and latency cost — is unmeasured.

Existing code benchmarks answer a narrower question. The established long-horizon issue-fixing benchmarks measure whether an agent resolves an issue, scored by a hidden `fail-to-pass` / `pass-to-pass` test oracle, and evaluate a model-plus-agent as a single black box that reports one `%Resolved` number. They do not isolate the contribution of a workflow layered on top, and they do not exercise the spec-authoring and planning stages at all. The literature on agent skills warns that this gap matters: skills do not uniformly help (*SWE-Skills-Bench*, arXiv 2603.15401), and code that passes tests can still violate its specification (*Specification-Driven Code Generation*, arXiv 2601.03878). A benchmark for this workflow must attribute outcomes to workflow stages, not just report a single score.

---

## Goals

1. Measure the end-to-end value of the full `spec-*` pipeline against a plain single-agent baseline on the same model and the same tasks.
2. Attribute that value to individual workflow stages — spec authoring, the two review gates, and structured-vs-merely-parallel execution — through a fixed set of ablation arms ([02-arms.md](02-arms.md)). Planning runs in every workflow arm; the closed five-arm set does not isolate it with a single-variable pair (a known limitation, [02-arms.md](02-arms.md) → Open questions).
3. Report outcomes against a hidden test oracle that the workflow's own gates never see, so the workflow cannot overfit the metric ([06-scoring-and-statistics.md](06-scoring-and-statistics.md)).
4. Report cost alongside outcome, so a token-hungry workflow is judged on cost-matched resolution, not raw resolution.
5. Measure artifacts the workflow produces — spec conformance, plan coverage, and gate efficacy — that a black-box outcome score cannot observe ([04-metrics.md](04-metrics.md)).

## Non-goals

- Ranking base models. The model is held fixed within a campaign; the variable under test is the scaffold, not the model.
- Evaluating the `reasoning-semiformally` or `jj-workspaces` plugins on their own. They appear only as dependencies the workflow arms invoke.
- Producing a public leaderboard. The output is an ablation table with confidence intervals, not a single headline rank.
- Authoring the implementation plan. Sequencing the build into task packages is `spec-planner`'s job, not this spec's.

---

## System shape

```
   task registry (TaskInstance × Suite)
   ┌─────────────────────────────────────────────────────────────┐
   │  greenfield-features                                         │
   │  (spec + hidden test suite)                                  │
   └───────────────────────────────┬─────────────────────────────┘
                                    │
        Campaign = Arms × Suites × Trials, on one fixed model
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
        ┌──────────┐  driver provisions a container per Trial,
        │  Trial   │  installs the arm's plugin set, runs to
        │ (arm ×   │  completion, captures the CandidatePatch +
        │  task ×  │  ArtifactBundle (specs, plans, certs,
        │  seed)   │  transcripts, token/cost/wall-clock telemetry)
        └────┬─────┘
             │  patch + artifacts handed to a SEPARATE clean container
             ▼
   ┌───────────────────────────────────────────────────────────────┐
   │  SCORING — isolated from the run                                │
   │   hidden fail-to-pass / pass-to-pass oracle  → resolved?        │
   │   spec-conformance judge                     → conformance      │
   │   injected-defect probes                     → gate efficacy    │
   └───────────────────────────────┬───────────────────────────────┘
                                    ▼
                ScoreReport per Trial → MetricResult per (Arm, Suite)
                paired stats across arms (McNemar, binomial CIs, Pass@k)
```

A **Campaign** fixes a model and runs every **Arm** over every **Suite** for a set number of **Trials**. Each Trial provisions a fresh container, runs one arm against one task instance, and emits a candidate patch plus an artifact bundle. Scoring runs in a *separate* clean container that the run never touched — the integrity rule that keeps the workflow's gates from seeing the oracle ([05-harness-architecture.md](05-harness-architecture.md) → *Scoring isolation*). Per-trial score reports aggregate into per-arm metrics, and arms are compared pairwise on paired instances.

---

## Detail pages

| Page | Topic |
|---|---|
| [01-domain-model.md](01-domain-model.md) | Entities, IDs, lifecycles — Campaign, Trial, Arm, TaskInstance, ArtifactBundle, GateEvent, ScoreReport, MetricResult |
| [02-arms.md](02-arms.md) | The five ablation arms and the pairwise deltas each isolates |
| [03-task-suites.md](03-task-suites.md) | The greenfield feature suite and the local-fixture verification suite |
| [04-metrics.md](04-metrics.md) | The four metric buckets: outcome, cost, process/artifact quality, robustness |
| [05-harness-architecture.md](05-harness-architecture.md) | The driver, containerization, the BenchFlow substrate, the scoring-isolation rule |
| [06-scoring-and-statistics.md](06-scoring-and-statistics.md) | The test oracle, the conformance judge, gate-efficacy probes, and the paired statistics |
| [canonical-types.schema.json](canonical-types.schema.json) | Benchmark entity shapes as JSON Schema |

---

## Scope summary

| Area | Design | Notes |
|---|---|---|
| Arms | Five: A0 baseline, A1 full pipeline, A2 plan+build, A3 gates on/off, A4 structured-vs-parallel | [02-arms.md](02-arms.md). All five are in scope from the first campaign. |
| Suites | `greenfield-features` (newly authored), plus the `local-fixture` verification suite | [03-task-suites.md](03-task-suites.md). |
| Oracle | Hidden `fail-to-pass` / `pass-to-pass`, plus a conformance judge | [06-scoring-and-statistics.md](06-scoring-and-statistics.md). The workflow's gates never see it. |
| Substrate | BenchFlow `bench` SDK; Docker per trial | [05-harness-architecture.md](05-harness-architecture.md). jj and git both available in-container. |
| Model | Fixed per campaign | A campaign variable, not a benchmark axis. |
| Implementation | None | This spec defines the design; nothing is built. |

---

## Assumptions and open questions

**Assumptions**

- The `spec-*` plugins can be installed and driven non-interactively inside a container, with telemetry (token counts, cost, wall-clock, turn counts) recoverable per run.
- The greenfield suite's tasks can be authored fresh and kept private, so they are absent from any base model's training data at campaign time.
- A jj-or-git colocated repo is available in each container; `spec-builder` selects the backend itself.

**Decisions**

- *Subject of the spec.* **The benchmark's design, not a built system.** Nothing is implemented; the body describes the intended design and `Status` stays `Draft` until components exist. The alternative — withholding the spec until code exists — would block planning the build from it.
- *Variable under test.* **The scaffold, with the model fixed.** The question is whether the workflow helps, which is only answerable when the model is held constant across arms (the *SWE-Skills-Bench* attribution discipline, arXiv 2603.15401).

**Open questions**

- *Build sequence.* How the harness is decomposed into reviewable task packages and milestones is a plan, not a spec — it belongs to `spec-planner`, run against this spec. What is the minimal first slice (which arms, how many instances) that proves the harness end to end?
- *Conformance judge calibration.* The spec-conformance metric uses an LLM judge ([06-scoring-and-statistics.md](06-scoring-and-statistics.md)). How large a human-labelled sample is needed to trust its agreement, and what agreement threshold is acceptable?
- *UI-bound tasks.* `spec-builder` pauses for manual sign-off on visually-reviewable tasks. Are such tasks excluded from the suites, or is a scripted oracle supplied to stand in for the human reviewer?
