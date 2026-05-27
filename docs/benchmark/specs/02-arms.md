# 02 — Ablation Arms

This page defines the five scaffold configurations the benchmark runs. The frame is set by [00-overview.md](00-overview.md): the model is fixed within a Campaign, and the arm is the only thing that varies. Each arm is an `Arm` entity ([01-domain-model.md](01-domain-model.md)); the set is closed at five.

---

## Responsibilities

The arms exist to *attribute* outcomes to workflow stages. A single arm produces a score; a *pair* of arms, differing in exactly one stage, isolates that stage's contribution. The arm set is designed so that every stage of the `spec-*` pipeline — spec authoring, planning, the two gates, structured decomposition — is the sole difference in at least one pair.

The arm set does **not** vary the base model, the task suite, or the test oracle. Those are Campaign and Suite concerns ([01-domain-model.md](01-domain-model.md), [03-task-suites.md](03-task-suites.md)).

---

## The arms

| Arm | Plugins active | Gates | Spec given? | Execution | One-line role |
|---|---|---|---|---|---|
| **A0** | none | n/a | input only | single | Plain single-agent baseline. The floor. |
| **A1** | creator + planner + builder | on | no — authored | parallel-structured | The full pipeline. The system under test. |
| **A2** | planner + builder | on | yes — handed in | parallel-structured | Spec authoring removed. |
| **A3** | planner + builder | **off** | yes — handed in | parallel-structured | Gates removed (relative to A2). |
| **A4** | none (naive split) | off | input only | parallel-unstructured | Parallelism without spec structure. |

### A0 — Baseline

A plain Claude Code agent on the fixed model, no `spec-*` plugins. It receives the TaskInstance's `problemStatement` and produces a patch. On the `swe-bench-pro-public` suite A0 runs the same tasks and the same hidden oracle as SWE-bench Pro, so its `%Resolved` is comparable on tasks and oracle — though not directly to a published leaderboard number, which is produced by SWE-bench Pro's own reference agent rather than plain Claude Code.

### A1 — Full pipeline

The complete workflow: `spec-creator` authors a spec from the problem statement, `spec-planner` decomposes it into a task graph with definitions of done and done-certificates, and `spec-builder` builds each task in an isolated workspace behind both gates, merging into an integration point. This is the system the benchmark exists to evaluate.

### A2 — Plan + build (spec handed in)

Identical to A1 except `spec-creator` does not run; a ready-made spec is provided as input. Isolates the value of *spec authoring* by the workflow versus starting from a spec someone already wrote.

### A3 — Build without gates

Identical to A2 except `spec-builder`'s two gates — `semi-formal-review` (correctness) and `validate-done-certificate` (completeness) — are disabled. The implementer's self-report decides task completion. Isolates the value of the gates, which is the workflow's central claim ("a task is only done when proven done by someone other than its builder").

### A4 — Parallel but unstructured

A naive N-way decomposition of the problem across parallel agents, with no dependency-ordered DAG, no per-task definition of done, and no gates. Controls for the possibility that any A1 gain is merely the effect of running several agents at once rather than of the spec-driven structure. `N` is set to match A1's typical task count on the same instance so the parallelism budget is comparable.

---

## The pairwise deltas

Each comparison holds everything constant but one stage. The deltas are computed on *paired* TaskInstances ([06-scoring-and-statistics.md](06-scoring-and-statistics.md)).

| Comparison | Isolates | Reading |
|---|---|---|
| **A1 − A0** | The whole workflow vs a plain agent | Headline: does the scaffold help at all, and at what cost? |
| **A1 − A2** | Spec authoring | Does having `spec-creator` write the spec beat starting from a given spec? |
| **A2 − A3** | The two gates | Do the correctness and completeness gates improve outcomes and reduce regressions? |
| **A1 − A4** | Structured workflow vs equal-budget raw parallelism | Is the gain from the spec-driven structure (spec + plan + gates together), or just from running agents concurrently? |

The chain A0 → A4 → A2 → A1, with A3 hanging off A2, lets a reader walk from "no scaffold" to "full scaffold" and see where the value enters. The literature motivates each isolation: skills do not uniformly help (*SWE-Skills-Bench*, arXiv 2603.15401), so A1 − A0 alone is insufficient; multi-agent execution helps on parallelizable work but can degrade sequential work, so A1 − A4 must separate structure from concurrency.

One stage is *not* isolated by any single-variable pair: **planning**. `spec-planner` runs in A1, A2, and A3, but A4 (the only plan-less workflow arm) also drops the spec and the gates, so A1 − A4 measures the bundle, not planning alone. See the Open questions.

---

## Flow

```
problem statement / spec seed (from TaskInstance)
        │
        ├─ A0 ─────────────────────────────────► patch
        │
        ├─ A4 ─ naive split ─ N agents ─ merge ─► patch
        │
        ├─ A3 ─ [given spec] ─ plan ─ build (no gates) ─ merge ─► patch
        │
        ├─ A2 ─ [given spec] ─ plan ─ build ─ gate ─ gate ─ merge ─► patch
        │
        └─ A1 ─ create spec ─ plan ─ build ─ gate ─ gate ─ merge ─► patch
```

Every arm ends at a single candidate patch against `baseCommit`, scored identically by the hidden oracle ([06-scoring-and-statistics.md](06-scoring-and-statistics.md)). The arms differ only in what happens between the input and that patch.

---

## Implementation layout

Arms are configuration, not code branches: each is an `Arm` record ([`canonical-types.schema.json`](canonical-types.schema.json)) the driver reads to decide which plugins to install and which flags to set when provisioning a Trial container ([05-harness-architecture.md](05-harness-architecture.md)). Adding an arm is adding a record and a provisioning recipe, not forking the harness.

---

## Assumptions and open questions

**Assumptions**

- `spec-builder`'s gates can be disabled by configuration (for A3) without otherwise changing its build loop, so A2 and A3 differ in exactly one variable.
- A "given spec" for A2 and A3 can be produced once per instance to a fixed quality bar, so that variance in the handed-in spec does not leak into those arms' results.

**Decisions**

- *Five arms, closed set.* **A0–A4.** Each isolates one stage in a pair; more arms would add cost without isolating a new stage. The set is fixed so cross-campaign comparison is stable.
- *A3 ablates gates against A2, not A1.* **A2 − A3 is the gate delta.** Holding spec-authoring out of the comparison keeps the gate effect from being confounded with the spec-authoring effect.
- *A4 matches A1's parallelism budget.* **`N` ≈ A1's task count.** Equalising the concurrency budget is what makes A1 − A4 a test of *structure* rather than of *how many agents ran*.

**Open questions**

- *Planning is not independently isolated.* No single-variable pair isolates `spec-planner`'s contribution — A1 − A4 bundles spec authoring, planning, gates, and structure, and the closed five-arm set has no "build from a hand-given plan, no planner" arm. Should a sixth arm be added to isolate planning, or is the bundled A1 − A4 reading acceptable for the benchmark's purpose?
- *Given-spec provenance for A2/A3.* Should the handed-in spec be authored by `spec-creator` in a separate pass (risking that A2 then partly measures spec-creator anyway), by a human, or drawn from the greenfield suite's authoring materials? The choice affects what A1 − A2 means.
- *A4 decomposition policy.* What counts as a fair "naive split" — fixed file/region partition, or a single unstructured "split this N ways" prompt — needs pinning so A4 is reproducible.
