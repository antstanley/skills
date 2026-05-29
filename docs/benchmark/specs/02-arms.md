# 02 — Ablation Arms

This page defines the six scaffold configurations the benchmark runs. The frame is set by [00-overview.md](00-overview.md): the model is fixed within a Campaign, and the arm is the only thing that varies. Each arm is an `Arm` entity ([01-domain-model.md](01-domain-model.md)); the set is closed at six (A0–A4 are the pairwise-delta arms; A5 is a lighter pre-canned variant — see §A5).

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
| **A5** | none (pre-canned) | on | input only | single | Lighter pre-canned variant: emits gate events without a recursive build. |

### A0 — Baseline

A plain Claude Code agent on the fixed model, no `spec-*` plugins. It receives the TaskInstance's `problemStatement` and produces a patch. A0 is the floor against which every workflow arm's pairwise delta is read ([06-scoring-and-statistics.md](06-scoring-and-statistics.md)).

### A1 — Full pipeline

The complete workflow: `spec-creator` authors a spec from the problem statement, `spec-planner` decomposes it into a task graph with definitions of done and done-certificates, and `spec-builder` builds each task in an isolated workspace behind both gates, merging into an integration point. This is the system the benchmark exists to evaluate.

### A2 — Plan + build (spec handed in)

Identical to A1 except `spec-creator` does not run; a ready-made spec is provided as input. Isolates the value of *spec authoring* by the workflow versus starting from a spec someone already wrote.

### A3 — Build without gates

Identical to A2 except `spec-builder`'s two gates — `semi-formal-review` (correctness) and `validate-done-certificate` (completeness) — are disabled. The implementer's self-report decides task completion. Isolates the value of the gates, which is the workflow's central claim ("a task is only done when proven done by someone other than its builder").

The gate ON vs OFF difference becomes observable through `spec-builder`'s discharged done-certificates: a gates-on run (A1, A2) emits one `GateEvent` per discharged certificate whose `VERDICT:` line carries a `GATE_VERDICTS` value (PASS / FAIL / PARTIAL / UNVERIFIED), parsed by `extract_gate_events` in `benchmark/harness/arms/a2_a3.py`; a gates-off run (A3) leaves the authored `(blank …)` placeholder and emits no events. So A2 surfaces ≥ 1 `GateEvent` and A3 surfaces zero on the same instance, observable from `ArtifactBundle.certificateArtifacts` plus the threaded `TrialResult.gate_events` ([05-harness-architecture.md](05-harness-architecture.md) → §Responsibilities → GateEvent threading).

### A4 — Parallel but unstructured

A naive N-way decomposition of the problem across parallel agents, with no dependency-ordered DAG, no per-task definition of done, and no gates. Controls for the possibility that any A1 gain is merely the effect of running several agents at once rather than of the spec-driven structure. `N` is set to match A1's typical task count on the same instance so the parallelism budget is comparable.

The N per-agent diffs are merged naively: each diff is applied with plain `git apply` in agent-index order, the first applier wins, and any overlapping diff that fails to apply is **recorded as a merge conflict** (in `ContainerRunBackend.last_merge_conflicts`) rather than 3-way-resolved. The merged candidate patch is `git diff <base>..HEAD` after the apply pass. This is the point of A4: an arm with no structure has no principled way to resolve conflicts between agents, so surfacing the conflict — not papering over it — is the honest reading. The merge-conflict rate appears as a robustness metric ([04-metrics.md](04-metrics.md) → Bucket 4).

### A5 — Lighter pre-canned

A lighter, **pre-canned (non-recursive)** arm that produces the same observable artifacts a gated workflow arm does — a candidate code patch and at least one discharged done-certificate carrying a real `VERDICT:` line — but WITHOUT running the full recursive `spec-planner` + `spec-builder` build. A5 runs a single FIXED `claude -p` call (the pre-canned `A5_INSTRUCTION`) under a small `A5_MAX_BUDGET_USD` cap and a short `A5_RUN_TIMEOUT_SECONDS` wall-clock bound, with `gatesEnabled = true` so the captured certificate flows through the same `extract_gate_events` path the recursive arms use.

A5 is **not** a pairwise-delta arm — it does not isolate a single workflow stage against another arm the way A0–A4 do. It exists for two operational needs the recursive arms serve poorly: (1) a fast, reliable **gate-emission witness** for `extract_gate_events` (`benchmark/harness/arms/a2_a3.py`) that does not depend on a long recursive build finishing before the run timeout; and (2) a **cheaper cost-curve point** between the plain A0 baseline and the full A1 workflow. The flow is deterministic and scripted: the fixed prompt instructs the single agent to implement the feature in place AND to write one done-certificate under the captured-artifact tree (`docs/plans/.../certificates/`) with a real `VERDICT:` line. The container backend routes the A5 slug to a dedicated pre-canned path (`_run_a5`) — NOT the recursive `_run_workflow_arm` path — so no `spec-*` plugin is mounted and no sub-agent recursion occurs. The captured certificate yields ≥ 1 `GateEvent` via the same structural extraction A2 uses; A5's candidate patch excludes the `docs/` artifact subtree exactly like the workflow arms.

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

- *Six arms, closed set.* **A0–A5.** A0–A4 each isolate one stage in a pair; A5 is a lighter **pre-canned (non-recursive) variant** added for gate-emission verification and as a cheaper cost-curve point, *not* to isolate a new workflow stage. The pairwise-delta chain (A0 → A4 → A2 → A1, with A3 off A2) is unchanged — A5 sits outside it. The set is fixed at six so cross-campaign comparison is stable; A5 is included because the recursive workflow arms (A1/A2) can exceed the run timeout, making them a poor fixture for a fast, reliable check that a discharged certificate `VERDICT:` line maps to a `GateEvent`.
- *A3 ablates gates against A2, not A1.* **A2 − A3 is the gate delta.** Holding spec-authoring out of the comparison keeps the gate effect from being confounded with the spec-authoring effect.
- *A4 matches A1's parallelism budget on both dollars and concurrency.* **`N ≈ A1's task count` and total `--max-budget-usd` matched.** `A4_TOTAL_MAX_BUDGET_USD = A1_MAX_BUDGET_USD` (`$60` — raised from `$20` to match the 3× increase of the recursive-workflow run timeout; see [05-harness-architecture.md](05-harness-architecture.md) → §Concurrency and reproducibility) and each agent's cap is `A4_TOTAL_MAX_BUDGET_USD / A4_N` (`benchmark/harness/arms/a4.py:115, 120`), so the sum of A4's per-agent caps equals A1's single-run cap by construction. Without the dollar match, A1 − A4 would partly measure who got a bigger budget rather than what structure adds over raw parallelism.
- *Given-spec provenance for A2/A3.* **A frozen, human-authored spec per instance**, checked into the suite at `benchmark/suites/greenfield-features/<slug>/given_spec/given_spec.md` and consumed identically (same bytes) by both A2 and A3. Authored once to the fixed quality bar named in `benchmark/harness/arms/a2_a3.py::GIVEN_SPEC_QUALITY_BAR` (overview → domain model and invariants → one contract section per component with ≥2 worked examples → definition of done). A per-run `spec-creator` pass would make A2 partly re-measure spec-creator (defeating A1 − A2) and inject run-to-run spec variance into A2 − A3; a human-frozen shared asset removes both confounds.
- *A4 decomposition policy.* **A fixed, prompt-only N-way split with no intelligent planning.** All `N` agents receive the identical full `problemStatement` plus a coordination-free framing ("you are agent _i_ of _N_ working concurrently with no coordination and no shared plan; implement your share"). No coordinator chooses the slices — a component partition was rejected because producing a sensible partition is itself planning, which would smuggle (un-gated) planning value into A1 − A4. The fixed template lives in `benchmark/harness/arms/a4.py::A4_SLICE_INSTRUCTION`; `N = A4_N = 4`, matching A1's typical task count on the seed.

**Open questions**

- *Planning is not independently isolated.* No single-variable pair isolates `spec-planner`'s contribution — A1 − A4 bundles spec authoring, planning, gates, and structure, and the closed six-arm set has no "build from a hand-given plan, no planner" arm (A5 is a lighter pre-canned variant, not a planning isolation). Should a further arm be added to isolate planning, or is the bundled A1 − A4 reading acceptable for the benchmark's purpose?
