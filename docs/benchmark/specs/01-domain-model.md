# 01 — Domain Model

This page defines the entities the benchmark manages, how they relate, how they are identified, and what the harness queries over them. The storage shape of each entity is formalised in [`canonical-types.schema.json`](canonical-types.schema.json).

---

## ID scheme

Mutable, human-meaningful entities carry a **stable slug**; per-execution records carry a generated id of the form:

```
<prefix>_<uuid>
```

- **prefix** is a short lowercase tag identifying the record type.
- **uuid** is a v7 UUID (RFC 9562), so ids sort by creation time.

| Prefix / slug | Entity |
|---|---|
| `A0`–`A4` (slug) | Arm |
| suite slug (`greenfield-features`, `local-fixture`) | Suite |
| task slug (suite-scoped, e.g. `greenfield__text_toolkit__0001`) | TaskInstance |
| `camp_` | Campaign |
| `trial_` | Trial |
| `bundle_` | ArtifactBundle |
| `gate_` | GateEvent |
| `score_` | ScoreReport |
| `defect_` | InjectedDefect |
| `metric_` | MetricResult |

Arm slugs are fixed and never reused; the set is closed at five ([02-arms.md](02-arms.md)). Suite and task slugs are stable identifiers used to pair trials across arms.

---

## Entities

### Suite (slug)

A named collection of task instances drawn from one source with one oracle convention. The ablation result runs on `greenfield-features` (build-from-spec, newly authored); the `local-fixture` suite is a Docker-free verification instance for the pipeline itself. See [03-task-suites.md](03-task-suites.md).

Carries:

- `slug` — stable suite identifier.
- `kind` — `greenfield` or `local-fixture`.
- `oracleConvention` — `greenfield-hidden-tests` or `local`.

### TaskInstance (suite-scoped slug)

One benchmark problem: a starting repository state plus the input the arms receive plus the hidden oracle that scores them.

Carries:

- `slug` — suite-scoped stable id.
- `suite` — owning Suite slug.
- `repo` / `baseCommit` — the starting code state.
- `problemStatement` — the prose specification seed (greenfield) or short task description (local-fixture) that the arms receive as input.
- `goldPatch` — reference solution, present for the `local-fixture` instance (the patch that makes its hidden suite pass); `null` for greenfield, which has no single reference solution.
- `failToPass` / `passToPass` — the hidden test selectors that define resolution. Never exposed to any arm.
- `testTags` — for greenfield instances, an optional mapping from each hidden test selector to the spec section or component it exercises. It lets the `gateEscape` metric ([06-scoring-and-statistics.md](06-scoring-and-statistics.md)) attribute a failing test to the specific `Done` task that claims that section (via the task's `Implements` pointer). Absent it, escape is computed only at instance granularity.
- `dockerImage` — the prebuilt environment tag the trial container is based on.
- `contaminationTier` — `public`, `held-out`, or `authored-private`; records training-data exposure risk.
- `headlessVerifiable` — whether the oracle runs without a human in the loop (gates the UI-pause concern from [00-overview.md](00-overview.md)).

### Arm (slug)

A scaffold configuration: which plugins are active, whether the gates run, and the execution mode. The model is *not* an arm field — it is fixed by the Campaign. The five arms are defined in [02-arms.md](02-arms.md).

Carries:

- `slug` — `A0`–`A4`.
- `pluginsEnabled` — the `spec-*` plugins active for this arm.
- `gatesEnabled` — whether `spec-builder`'s correctness and done-certificate gates run.
- `specProvided` — whether a ready-made spec is handed to the arm rather than authored by `spec-creator`.
- `executionMode` — `single`, `parallel-structured`, or `parallel-unstructured`.

### Campaign (`camp_`)

One full benchmark execution: every Arm over every Suite, for `trialsPerInstance` repetitions, on one fixed model.

Carries:

- `id`, `createdAt`.
- `model` — the fixed base model id (e.g. `claude-opus-4-7`).
- `arms` — the Arm slugs included (all five by default).
- `suites` — the Suite slugs included.
- `trialsPerInstance` — repetition count for Pass@k and nondeterminism.
- `backend` — `container` (default) or `local`; the run/scoring backend the campaign uses.
- `solver` — `agent` (default) or `fixture`; `fixture` runs the scripted solver that emits the instance `goldPatch`, for deterministic pipeline verification on the `local-fixture` suite without an LLM agent. Real arms use `agent`.

### Trial (`trial_`)

The atomic execution: one Arm run against one TaskInstance under one seed. Produces a candidate patch and an artifact bundle, then is scored.

Carries:

- `id`, `campaign`, `arm`, `taskInstance`, `seed`, `createdAt`.
- `status` — see [lifecycle](#lifecycle--state-machine).
- `candidatePatch` — the unified diff the arm produced against `baseCommit`.
- `artifactBundle` — id of the ArtifactBundle.
- `scoreReport` — id of the ScoreReport, once scored.

### ArtifactBundle (`bundle_`)

Everything one Trial produced besides the patch, captured for the process and cost metrics ([04-metrics.md](04-metrics.md)).

Carries:

- `id`, `trial`.
- `specArtifacts` / `planArtifacts` / `certificateArtifacts` — the spec, plan, and done-certificate files the workflow wrote (empty for A0).
- `transcript` — the full agent transcript.
- `telemetry` — `{ inputTokens, outputTokens, costUsd, wallClockSeconds, agentTurns }`.

### GateEvent (`gate_`)

One gate decision inside a Trial. Only arms with `gatesEnabled` emit these. Used for the gate-efficacy metric ([06-scoring-and-statistics.md](06-scoring-and-statistics.md)).

Carries:

- `id`, `trial`, `task` — the plan task being gated.
- `gateKind` — `semi-formal-review` (correctness) or `validate-done-certificate` (completeness).
- `verdict` — `PASS`, `FAIL`, `PARTIAL`, or `UNVERIFIED`.
- `retryIndex` — which retry of the build loop emitted this verdict.

### InjectedDefect (`defect_`)

A known-bad patch deliberately introduced into a gate-efficacy probe trial, to measure whether the gates catch it. Distinct from organic Trials.

Carries:

- `id`, `taskInstance`.
- `defectKind` — the class of fault injected. The closed taxonomy is `off-by-one`, `dropped-branch`, `wrong-return` ([06-scoring-and-statistics.md](06-scoring-and-statistics.md) → §Gate-efficacy probes → *Defect taxonomy*).
- `caughtBy` — the `gateKind` that flagged it, or `null` if it escaped.

### ScoreReport (`score_`)

The scoring of one Trial against the hidden oracle, produced in the isolated scoring container.

Carries:

- `id`, `trial`.
- `resolved` — `failToPass` all pass *and* `passToPass` all still pass.
- `failToPassResults` / `passToPassResults` — per-test outcomes.
- `regressed` — a previously-passing `passToPass` test now fails.
- `conformanceScore` — the spec-conformance judge's score (greenfield, and any arm that produced a spec).
- `gateEscape` — a task the workflow marked `Done` whose hidden tests fail (false-`Done`).

### MetricResult (`metric_`)

An aggregate over the Trials of one (Arm, Suite), with confidence intervals. The reportable output of a Campaign.

Carries:

- `id`, `campaign`, `arm`, `suite`, `metricName`.
- `value`, `ciLow`, `ciHigh` — point estimate and 95% interval.
- `nTrials`.

---

## Relationships

```
Campaign 1───* Trial *───1 Arm
                 │   *───1 TaskInstance *───1 Suite
                 │
                 ├──1 ArtifactBundle
                 ├──* GateEvent          (only when Arm.gatesEnabled)
                 └──1 ScoreReport

InjectedDefect *───1 TaskInstance        (gate-efficacy probe trials)
MetricResult   *───1 Campaign, aggregates ScoreReports over (Arm, Suite)
```

A Trial belongs to exactly one Campaign, one Arm, and one TaskInstance. The (Arm, TaskInstance, seed) triple is unique within a Campaign. Trials sharing a TaskInstance across different Arms are the *paired* observations the statistics compare ([06-scoring-and-statistics.md](06-scoring-and-statistics.md)).

---

## Lifecycle / state machine

A Trial moves through:

```
queued ─► provisioning ─► running ─► captured ─► scored ─► aggregated
                │             │          │
                └──► failed ◄──┴──────────┘     (infra error; excluded from metrics, logged)
```

- **queued** — scheduled in the Campaign matrix, not yet started.
- **provisioning** — container being built from the TaskInstance's `dockerImage`, plugins installed per Arm.
- **running** — the arm executes; the build loop, gates, and waves all happen here for workflow arms.
- **captured** — candidate patch and ArtifactBundle persisted; the run container is discarded.
- **scored** — the patch was applied in the isolated scoring container and a ScoreReport produced.
- **aggregated** — the ScoreReport has been folded into the (Arm, Suite) MetricResults.
- **failed** — an infrastructure fault (not a wrong answer). Excluded from metrics and logged for re-run; distinct from a `resolved: false` ScoreReport, which is a legitimate outcome.

---

## Required query patterns

| Query | Access pattern |
|---|---|
| All Trials for one (Arm, Suite) in a Campaign | Aggregating MetricResults. |
| The paired set of Trials sharing a TaskInstance across two Arms | McNemar / paired comparison ([06-scoring-and-statistics.md](06-scoring-and-statistics.md)). |
| All GateEvents for a Trial | Gate-efficacy and retry-count analysis. |
| All ScoreReports with `gateEscape` true | False-`Done` escape rate — the headline gate metric. |
| Telemetry summed over an Arm | Cost-matched resolution ([04-metrics.md](04-metrics.md)). |

---

## Persistence

Entity records are read and written as JSON, validated against [`canonical-types.schema.json`](canonical-types.schema.json) on both sides of the boundary. The persistence helpers in `benchmark/harness/domain.py` are:

- `dump_jsonl(records, path)` / `load_jsonl(record_type, path)` / `iter_jsonl(record_type, path)` — one JSON object per line, used for collections of homogeneous records (a campaign's trials, an arm's score reports, the gate-event log).
- `dump_json(record, path)` / `load_json(record_type, path)` — one JSON object per file, used for singleton records (an ArtifactBundle, a Campaign).

Every `load_*` call re-validates against the schema before constructing the dataclass, so a stale or partially-written record fails at read time rather than poisoning a downstream computation. The on-disk shape is the same as the JSON the schema describes; there is no separate serialised form.

---

## Runtime aggregates

The driver returns two in-memory aggregates that group the entities defined above:

- **`TrialResult`** (`benchmark/harness/driver/scheduler.py`) — the outcome of driving one Trial through the lifecycle. Carries the `Trial`, its `ArtifactBundle` and `ScoreReport` (both `None` for a `failed` trial), the `fault` string for the re-queue log, and the `GateEvent`s the run backend surfaced for the trial. Properties `is_scored` and `is_failed` partition trials into the two metric-relevant buckets.
- **`CampaignRun`** — the rollup over a Campaign's `TrialResult`s. Exposes `score_reports`, `scored_results`, `failed_results`, `gate_events`, and `raw_resolved_rate` as the canonical access surface for the §Required query patterns above. The whole stats layer (`benchmark/harness/stats/`) consumes a `CampaignRun`; downstream callers never iterate raw `results` lists.

Neither aggregate is persisted to disk — they are the per-process view a campaign run produces. Persisting requires writing the underlying entities through the JSONL helpers above.

---

## Assumptions and open questions

**Assumptions**

- Telemetry fields (`inputTokens`, `outputTokens`, `costUsd`, `wallClockSeconds`, `agentTurns`) are recoverable from the run harness for every Arm, including the plain baseline.
- A Trial's candidate patch is expressible as a single unified diff against `baseCommit`, even for multi-task workflow arms whose integration point accumulated several merges.

**Decisions**

- *Atomic unit is the Trial, not the Run.* **(Arm × TaskInstance × seed).** Pass@k and nondeterminism handling need repetition as a first-class axis, so the repeated execution is the entity, and Campaign is the aggregation over it.
- *Model is a Campaign field, not an Arm field.* **Held fixed across arms.** Putting it on the Arm would conflate scaffold effects with model effects, which is exactly what the benchmark must avoid.
- *Infra failure is a distinct state from a wrong answer.* **`failed` ≠ `resolved: false`.** A container that never started carries no information about the arm and must not depress its score; only `scored` trials enter metrics.

**Open questions**

- *Patch reconstruction for parallel arms.* When `spec-builder` merges several task workspaces into an integration point, the cleanest way to derive the single `candidatePatch` for scoring (diff of integration tip vs `baseCommit`) needs validation against conflict-resolution edge cases.
- *Seed determinism.* How much run-to-run determinism a fixed `seed` actually buys with an agentic scaffold is unknown; the repetition count may need tuning per [06-scoring-and-statistics.md](06-scoring-and-statistics.md).
