# eval-judge harness — Design Overview

**Status:** Draft · **Date:** 2026-05-30 · **Owner:** Ant Stanley · **Scope:** apps/evaljudge

The **eval-judge harness** (`.specs/evaljudge/`) runs the `evals.json` fixtures that ship with each `spec-*` skill, invokes the skill live against each fixture's prompt, and uses an LLM judge to score the skill's actual behavior against the fixture's `expected_output` — producing a per-eval score, band, and PASS/FAIL verdict plus an aggregate pass rate.

This document is the entry point for the harness's design. It states the problem, the goals, the system shape, and the scope. Detail pages are linked from each section.

> **Status note.** The harness is **not yet built** — this spec set is the target the implementation will be built to match (the build happens in another environment). The body describes the intended design in present tense, as the contract the code must satisfy; everything genuinely undecided is in the closing Open questions, not the body. When the code lands, `Status` flips to `Built` and any divergence becomes change-spec material rather than a silent body edit.

---

## Problem

Each `spec-*` skill ships an `evals/evals.json` file: a set of fixtures, each a `prompt` (what a user would say) paired with an `expected_output` (a prose description of how the skill should behave — what it should produce, what it should refuse, what structure its output should have). These fixtures encode the intended behavior of every skill in the marketplace.

Nothing executes them. They are inert documentation: a human or an ad-hoc LLM read is the only thing that checks a skill still does what its evals say. When a skill's `SKILL.md` is edited — trimmed, refactored, re-scoped — there is no mechanical signal that its behavior still matches its evals. The repo's `scripts/check.sh` gate runs ruff, pyright, and pytest over the Python harness; it never invokes a skill or reads an `evals.json`.

The repo already contains the machinery to close this gap. The benchmark's **conformance judge** ([`benchmark/harness/scoring/conformance/judge.py`](../../../benchmark/harness/scoring/conformance/judge.py)) is an injectable, budget-bounded `claude -p` LLM judge that scores a `(spec, code)` pair against a rubric, with tolerant JSON parsing, named-constant safety rails, and a calibration module. The eval-judge harness reuses that judging pattern, pointed at a different pair — `(expected_output, actual skill behavior)` — and adds a **run stage** that produces the *actual behavior* by invoking the skill live, mirroring the benchmark's run/score split.

---

## Goals

1. **Execute every skill's `evals.json` as a runnable check** — for each fixture, invoke the target skill live against the fixture `prompt`, capture what the skill actually did, and score that behavior against the fixture's `expected_output`.
2. **Score with a calibratable LLM judge**, reusing the benchmark's conformance-judge pattern: a single bounded `claude -p` call per eval, an injectable backend so tests are hermetic, a continuous `[0, 1]` score with a rationale, and a named-constant threshold that maps the score to a PASS/FAIL band.
3. **Capture behavior honestly** — both the skill's final response *and* the files it created or modified, because `expected_output` blocks assert on both (e.g. "a new directory `.specs/website/specs/` with numbered files" and "ends with a VERDICT block").
4. **Isolate each run** in a temp working directory (Docker-free, like the benchmark's `local` run backend), behind an injectable backend protocol so the run side never contaminates the host and tests can substitute a deterministic fake.
5. **Produce an auditable report** — per eval: score, band, PASS/FAIL, and the judge's rationale; per skill and overall: a pass rate — written to a structured artifact a reviewer (or CI) can read.

## Non-goals

- **Replacing `scripts/check.sh`.** The eval-judge harness spends model budget and needs a live `claude` CLI; it is an opt-in check (like the benchmark's `BENCHMARK_RUN_*_LIVE` self-tests), not part of the default hermetic gate.
- **Benchmarking workflow quality.** The benchmark (`.specs/benchmark/`) measures whether the `spec-*` *workflow* beats a baseline on hidden-test resolution. This harness asks a narrower question: does each skill's live behavior match its own declared evals? It reuses the benchmark's judge plumbing but answers a different question.
- **Authoring or editing `evals.json` fixtures.** The harness consumes fixtures; writing them is the skill author's job.
- **Judging non-skill prompts.** The input is always a skill's eval fixture; the harness does not score free-form prompts.

---

## System shape

```
   eval discovery
   ┌──────────────────────────────────────────────────────────────┐
   │  plugins/<plugin>/skills/<skill>/evals/evals.json             │
   │  → EvalCase{ skill, id, name, prompt, expected_output, files }│
   └───────────────────────────────┬──────────────────────────────┘
                                    │  one EvalCase at a time
                                    ▼
   ┌────────────────────────────┐  RUN STAGE (RunBackend, injectable)
   │  isolated temp working dir │  invoke the skill live: claude -p with
   │  + the plugin installed    │  the fixture prompt, the plugin on the
   │  + seed files (case.files) │  path; capture final response + file tree
   │  → EvalRun{ response,      │  diff. Bounded budget + timeout (named
   │     file_changes }         │  constants). NEVER sees expected_output.
   └──────────────┬─────────────┘
                  │  EvalRun (the actual behavior)
                  ▼
   ┌────────────────────────────┐  JUDGE STAGE (JudgeCallable, injectable)
   │  one bounded claude -p call │  rubric: score how well the ACTUAL behavior
   │  rubric + expected_output   │  satisfies expected_output, [0,1] + rationale.
   │  + EvalRun behavior         │  Reuses the conformance judge's prompt-build,
   │  → EvalJudgment{ score,     │  JSON-parse, clamp, and budget-rail pattern.
   │     rationale }             │
   └──────────────┬─────────────┘
                  │  score → band → PASS/FAIL (named threshold)
                  ▼
        EvalResult per case → EvalReport per skill / overall
        (per-case score+band+verdict+rationale; aggregate pass rate)
```

The harness reads each skill's `evals.json` into `EvalCase` records, then runs a **two-stage pipeline per case**: the **run stage** invokes the skill live in an isolated working directory and captures the actual behavior (`EvalRun`), and the **judge stage** scores that behavior against the case's `expected_output` and maps the score to a verdict. The run stage never sees `expected_output` — the same isolation discipline the benchmark enforces between its run and scoring sides, so a skill cannot be coached toward the answer. Per-case results aggregate into an `EvalReport`.

---

## Detail pages

| Page | Topic |
|---|---|
| [01-domain-model.md](01-domain-model.md) | Entities, IDs, lifecycles — EvalCase, EvalRun, EvalJudgment, EvalResult, EvalReport |
| [02-run-stage.md](02-run-stage.md) | Discovering fixtures, invoking the skill live, capturing behavior, the run backend |
| [03-judge-stage.md](03-judge-stage.md) | The rubric, the bounded judge call, score→band→verdict, calibration |
| [04-report-and-cli.md](04-report-and-cli.md) | The EvalReport artifact, the opt-in entrypoint, exit status, CI/gate posture |
| [05-architecture.md](05-architecture.md) | Package layout, reuse of the benchmark judge, the two injectable seams, isolation |
| [canonical-types.schema.json](canonical-types.schema.json) | eval-judge entity shapes as JSON Schema |

---

## Scope summary

| Area | Design | Notes |
|---|---|---|
| Fixtures | Every `plugins/*/skills/*/evals/evals.json` in the repo | [02-run-stage.md](02-run-stage.md). The schema is the existing `{skill_name, evals:[{id,name,prompt,expected_output,files}]}` shape. |
| Run stage | Live skill invocation in an isolated temp dir, behind an injectable `RunBackend` | [02-run-stage.md](02-run-stage.md). `local` (Docker-free) is the only backend this spec defines; a container backend is an Open question. |
| Judge stage | One bounded `claude -p` call per eval, injectable, `[0,1]` score + rationale | [03-judge-stage.md](03-judge-stage.md). Reuses the benchmark conformance judge's pattern and safety rails. |
| Verdict | Continuous score → band → PASS/FAIL via a named threshold | [03-judge-stage.md](03-judge-stage.md). Calibratable against human labels, like the conformance judge. |
| Report | A structured `EvalReport` artifact + aggregate pass rate | [04-report-and-cli.md](04-report-and-cli.md). |
| Gate posture | Opt-in (`EVALJUDGE_RUN_LIVE=1`), not part of `scripts/check.sh` | [04-report-and-cli.md](04-report-and-cli.md). Spends budget + needs a live `claude` CLI; the hermetic default path uses injected fakes. |
| Implementation | **Not yet built.** This spec is the build target. | The build happens in another environment; the plan is [`.specs/plans/`](../../plans/) (to be authored by spec-planner). |

---

## Assumptions and open questions

**Assumptions**

- The existing `evals.json` files across the `spec-*` plugins all follow one shape: a top-level `skill_name` plus an `evals` array of `{id, name, prompt, expected_output, files}` objects (confirmed against the eight fixtures in the repo at this date).
- A live, authenticated `claude` CLI is available in the environment that runs the harness, exactly as the benchmark's conformance judge and live self-tests assume.
- A skill can be invoked non-interactively via `claude -p` with the plugin installed on the path, and its file-system effects observed in the working directory — the same execution model the benchmark uses for its arms.
- The toolchain is the repo-wide one ([`.specs/development-guidelines.md`](../../development-guidelines.md)): Python 3.13, `uv`, ruff, pyright, pytest.

**Decisions**

- *Subject of the spec.* **The harness's intended design, as a build target.** The code does not exist yet; the body describes what the build must produce, and `Status: Draft` records that nothing has shipped. This is the one spec in the repo whose subject is not yet branch reality — flagged here per the divergence rule.
- *Reuse the benchmark conformance judge, do not reinvent it.* **The judge stage is the conformance judge's pattern pointed at `(expected_output, actual behavior)`.** [`benchmark/harness/scoring/conformance/judge.py`](../../../benchmark/harness/scoring/conformance/judge.py) already supplies the injectable bounded `claude -p` call, tolerant JSON parsing, `[0,1]` clamping, named budget/timeout rails, and a calibration module. Building a second judge from scratch would duplicate that machinery; the harness imports or mirrors it. See [05-architecture.md](05-architecture.md).
- *Run and judge are separate stages, judge never coaches the run.* **The run stage never sees `expected_output`.** This mirrors the benchmark's run/scoring isolation ([`.specs/benchmark/specs/05-harness-architecture.md`](../../benchmark/specs/05-harness-architecture.md) → Scoring isolation): a skill invoked with foreknowledge of the expected answer would overfit the check and void it.
- *Live-only, opt-in.* **Gated behind `EVALJUDGE_RUN_LIVE=1`, never in `scripts/check.sh`.** Invoking skills spends model budget and needs a live CLI; the default hermetic test path injects deterministic fakes, exactly as the benchmark's `BENCHMARK_RUN_*_LIVE` self-tests do.

**Open questions**

- *Container backend.* The `local` Docker-free backend is the only run backend this spec defines. Should a `container` backend be added for stronger isolation (parity with the benchmark's two-backend design), and if so, is it worth the Docker cost for a skill-behavior check?
- *Pass threshold and calibration sample.* The PASS/FAIL band boundary ([03-judge-stage.md](03-judge-stage.md)) needs a calibration sample of human-labelled eval judgments to set honestly. How many labelled cases, across how many skills, before the threshold is trustworthy rather than a placeholder?
- *Skills with side-effect-only or interactive behavior.* Some skills (e.g. `spec-builder`) dispatch sub-agents or expect a workspace; some pause for interactive confirmation. Can every `spec-*` skill be exercised non-interactively in a single bounded run, or do some evals need a scripted stand-in for the interaction (the benchmark's UI-bound-task question, in a new guise)?
- *Cost ceiling for a full sweep.* Running every fixture across every skill is N bounded `claude -p` run calls plus N judge calls. What per-eval and per-sweep budget caps keep a full run affordable, and should the harness support sampling a subset?
