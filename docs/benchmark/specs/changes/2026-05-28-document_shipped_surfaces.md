# Change: Document shipped public surfaces the canonical spec does not name

**Status:** Proposed · **Date:** 2026-05-28 · **Owner:** Ant Stanley · **Target:** apps/benchmark

The benchmark harness ships several public surfaces — persistence helpers, runtime aggregates, an arm-or-solver interface alias, the A4 budget-matching invariant, the A4 naive-merge policy, gate observability via parsed certificates, three per-instance suite assets, GateEvent threading off the run backend, the McNemar pairing-reduction rule, the InjectedDefect taxonomy, and the live-probe verdict mapping — that the canonical spec set never names in its body. Each is a real surface a reader needs to understand the system; each lives in code as named constants, public dataclasses, or documented module-level functions. This change spec adds spec body for them, distributed across the pages that own each surface. **No schema changes** — every field involved already exists in `canonical-types.schema.json`; the gap is in the prose that describes how the fields are used and where they are produced.

---

## Motivation

A canonical spec is "the canonical definition of what exists in the current branch". When a public surface ships without ever being named in the spec body, two things break. First, a reader has no way to discover the surface from the spec — they have to read the code and reconstruct the model. Second, the spec stops being a faithful map of the codebase, so subsequent edits cannot trust it as a base.

The R2 review consolidated under [`docs/plans/2026-05-27-spec_workflow_benchmark/plan.md`](../../../plans/2026-05-27-spec_workflow_benchmark/plan.md) catalogued these gaps page by page. Each one is small in isolation — one paragraph or one table row — but together they cover ten public surfaces across five canonical pages. Routing them through one change spec keeps the merge mechanical and lets the reader see the whole shape at once.

A separate companion change spec ([`2026-05-28-promote_built_state_and_resolved_decisions.md`](2026-05-28-promote_built_state_and_resolved_decisions.md)) handles the *other* axis of divergence — built reality the spec asserts is not built yet, and Open questions the build resolved. That change spec edits framing and Decisions; this one adds new body.

---

## Affected spec pages

| Canonical page | Nature of change |
|---|---|
| [`01-domain-model.md`](../01-domain-model.md) | Add §Persistence subsection (`dump_jsonl` / `load_jsonl` / `dump_json` / `load_json` / `iter_jsonl`); add §Runtime aggregates subsection (`TrialResult`, `CampaignRun`) |
| [`02-arms.md`](../02-arms.md) | Extend the *A4 matches A1's parallelism budget* Decision to record the **dollar-budget matching** invariant; add an §A4 paragraph on the **naive-merge policy**; add a §A2/§A3 paragraph on **gate observability** via parsed certificates |
| [`03-task-suites.md`](../03-task-suites.md) | Add a §Per-instance assets subsection covering the `given_spec/given_spec.md`, optional `reference/solution.patch`, and the `testTags` field (with a new row in the greenfield field table); cross-reference the agent run image to [05-harness-architecture.md](../05-harness-architecture.md) |
| [`05-harness-architecture.md`](../05-harness-architecture.md) | Add §GateEvent threading paragraph to §Responsibilities; describe the `ArmOrSolver` alias under §Backends as the backend-input shape |
| [`06-scoring-and-statistics.md`](../06-scoring-and-statistics.md) | Add a pairing-reduction sentence to §Confidence intervals and pairwise tests; enumerate the **defect taxonomy** under §Gate-efficacy probes; describe the **live-probe verdict mapping** under §Gate-efficacy probes |

No new canonical page is added; no schema fragment is changed.

---

## Proposed changes

Each block below is the prose as it should read in the canonical page after merge. Marked **Add** when introducing a new section/subsection/row, **Modify** when amending existing prose.

### `01-domain-model.md` → §Persistence (Add — new subsection after §Required query patterns)

> ## Persistence
>
> Entity records are read and written as JSON, validated against [`canonical-types.schema.json`](canonical-types.schema.json) on both sides of the boundary. The persistence helpers in `benchmark/harness/domain.py` are:
>
> - `dump_jsonl(records, path)` / `load_jsonl(record_type, path)` / `iter_jsonl(record_type, path)` — one JSON object per line, used for collections of homogeneous records (a campaign's trials, an arm's score reports, the gate-event log).
> - `dump_json(record, path)` / `load_json(record_type, path)` — one JSON object per file, used for singleton records (an ArtifactBundle, a Campaign).
>
> Every `load_*` call re-validates against the schema before constructing the dataclass, so a stale or partially-written record fails at read time rather than poisoning a downstream computation. The on-disk shape is the same as the JSON the schema describes; there is no separate serialised form.

### `01-domain-model.md` → §Runtime aggregates (Add — new subsection after §Persistence)

> ## Runtime aggregates
>
> The driver returns two in-memory aggregates that group the entities defined above:
>
> - **`TrialResult`** (`benchmark/harness/driver/scheduler.py`) — the outcome of driving one Trial through the lifecycle. Carries the `Trial`, its `ArtifactBundle` and `ScoreReport` (both `None` for a `failed` trial), the `fault` string for the re-queue log, and the `GateEvent`s the run backend surfaced for the trial. Properties `is_scored` and `is_failed` partition trials into the two metric-relevant buckets.
> - **`CampaignRun`** — the rollup over a Campaign's `TrialResult`s. Exposes `score_reports`, `scored_results`, `failed_results`, `gate_events`, and `raw_resolved_rate` as the canonical access surface for the §Required query patterns above. The whole stats layer (`benchmark/harness/stats/`) consumes a `CampaignRun`; downstream callers never iterate raw `results` lists.
>
> Neither aggregate is persisted to disk — they are the per-process view a campaign run produces. Persisting requires writing the underlying entities through the JSONL helpers above.

### `02-arms.md` → §Assumptions and open questions, *A4 matches A1's parallelism budget* Decision (Modify)

> - *A4 matches A1's parallelism budget on both dollars and concurrency.* **`N ≈ A1's task count` and total `--max-budget-usd` matched.** `A4_TOTAL_MAX_BUDGET_USD = A1_MAX_BUDGET_USD` and each agent's cap is `A4_TOTAL_MAX_BUDGET_USD / A4_N` (`benchmark/harness/arms/a4.py:115, 120`), so the sum of A4's per-agent caps equals A1's single-run cap by construction. Without the dollar match, A1 − A4 would partly measure who got a bigger budget rather than what structure adds over raw parallelism.

### `02-arms.md` → §A4 — Parallel but unstructured (Add — new paragraph at the end of the existing §A4 description)

> The N per-agent diffs are merged naively: each diff is applied with plain `git apply` in agent-index order, the first applier wins, and any overlapping diff that fails to apply is **recorded as a merge conflict** (in `ContainerRunBackend.last_merge_conflicts`) rather than 3-way-resolved. The merged candidate patch is `git diff <base>..HEAD` after the apply pass. This is the point of A4: an arm with no structure has no principled way to resolve conflicts between agents, so surfacing the conflict — not papering over it — is the honest reading. The merge-conflict rate appears as a robustness metric ([04-metrics.md](04-metrics.md) → Bucket 4).

### `02-arms.md` → §A3 — Build without gates (Add — new paragraph after the existing §A3 description)

> The gate ON vs OFF difference becomes observable through `spec-builder`'s discharged done-certificates: a gates-on run (A1, A2) emits one `GateEvent` per discharged certificate whose `VERDICT:` line carries a `GATE_VERDICTS` value (PASS / FAIL / PARTIAL / UNVERIFIED), parsed by `extract_gate_events` in `benchmark/harness/arms/a2_a3.py`; a gates-off run (A3) leaves the authored `(blank …)` placeholder and emits no events. So A2 surfaces ≥ 1 `GateEvent` and A3 surfaces zero on the same instance, observable from `ArtifactBundle.certificateArtifacts` plus the threaded `TrialResult.gate_events` ([05-harness-architecture.md](05-harness-architecture.md) → §Responsibilities → GateEvent threading).

### `03-task-suites.md` → §Suite: `greenfield-features`, the field table (Modify — add the `testTags` row)

Append after the existing `contaminationTier` row:

> | `testTags` | every greenfield instance carries a `selector → component or spec section` mapping for its hidden tests, so a failing hidden test can be attributed to the task that claimed responsibility for it. The component name doubles as the per-instance plan-task key the gate-escape attribution uses ([06-scoring-and-statistics.md](06-scoring-and-statistics.md) → §Gate-efficacy probes). |

### `03-task-suites.md` → §Per-instance assets (Add — new subsection after the greenfield narrative paragraphs, before §Suite: `local-fixture`)

> ### Per-instance assets
>
> A greenfield instance directory at `benchmark/suites/greenfield-features/<slug>/` carries up to three per-instance asset trees alongside `repo/{base,hidden}/`:
>
> - **`given_spec/given_spec.md`** — a frozen, human-authored specification of the feature the instance asks the arms to build. Consumed identically by A2 and A3 (the spec-given arms; see [02-arms.md](02-arms.md) → §Decisions → *Given-spec provenance for A2/A3*); A0/A1/A4 do not read it. Loaded by `benchmark.suites.greenfield.load_given_spec(slug)`.
> - **`reference/solution.patch`** (optional, per-instance) — a private reference solution carried **outside** the arms-visible `TaskInstance`. Loaded only by `benchmark.suites.greenfield.load_reference_solution(slug)`; `TaskInstance.goldPatch` stays `null` regardless. The reference solution exists so the greenfield self-test can demonstrate the scoring pipeline recognises a known-good patch (`resolved: true`) and rejects a no-op (`resolved: false`) without ever exposing the solution to a run-side arm.
> - **`repo/base/`** — the run-visible skeleton the run backend provisions from (plus the `passToPass` smoke tests that must keep passing). **`repo/hidden/`** — the withheld acceptance suite the scoring backend injects. The `hidden/` tree is never copied into the run image; the integrity rule lives in the image build ([05-harness-architecture.md](05-harness-architecture.md) → §Scoring isolation).

### `03-task-suites.md` → §Implementation layout (Modify — already updated by the companion change spec; this block extends with one cross-link)

The companion change spec [`2026-05-28-promote_built_state_and_resolved_decisions.md`](2026-05-28-promote_built_state_and_resolved_decisions.md) rewrites the §Implementation layout block to reflect the actual on-disk shape. This change spec adds a one-line pointer at the end of that block:

> The agent run image (the run image plus a non-root user with the `claude` CLI installed) is built from the run image and described under [05-harness-architecture.md](05-harness-architecture.md) → §Run container.

### `05-harness-architecture.md` → §Responsibilities, GateEvent threading (Add — new paragraph at the end of §Responsibilities)

> The driver also re-keys `GateEvent`s onto the Trial. A `RunBackend` that surfaces gate activity (the `container` backend on the workflow arms A1 and A2) accumulates events on a `last_gate_events` attribute during each `run()` call; the driver reads that attribute via duck-typing, rewrites each event's `trial` field to the current Trial's id, and attaches the re-keyed tuple to `TrialResult.gate_events`. The `CampaignRun` aggregates the per-trial gate events. This contract is **backend-neutral**: a backend without a `last_gate_events` attribute (the `local` backend, the A0 path on the `container` backend) contributes the empty tuple, and the `RunBackend` Protocol itself does not require the attribute. Gate-efficacy metrics ([04-metrics.md](04-metrics.md) → Bucket 3, [06-scoring-and-statistics.md](06-scoring-and-statistics.md) → §Gate-efficacy probes) read from `TrialResult.gate_events`, not from the backend.

### `05-harness-architecture.md` → §Backends, ArmOrSolver (Add — new paragraph at the end of §Backends)

> `RunBackend.run` takes a polymorphic second argument — an `Arm` record (a real arm A0–A4) or a solver-mode slug string (a `Campaign.solver` value such as `"fixture"`). The `ArmOrSolver` alias in `benchmark/harness/backends/interfaces.py` names this input shape. The `local` `RunBackend` plus the `fixture` solver is the deterministic Docker-free path the run-local demo uses; the `container` `RunBackend` plus a real `Arm` is the production path. The two backends and the two solvers compose freely.

### `06-scoring-and-statistics.md` → §Confidence intervals and pairwise tests (Add — new paragraph after the existing table)

> Each arm-instance pair is reduced to one resolved bool before McNemar pairs the arms: the rule is **`any` over the arm's `k` trials on that instance** (`benchmark/harness/stats/outcome.py::_instance_resolved_any`), so the pair's bool matches the `Pass@k` notion at `k = trialsPerInstance` and is well-defined at `k = 1`. Majority-of-trials was considered and rejected because it requires a tie-break rule at even `k`; `any` is parameter-free and the same shape the §Reporting ablation table already uses.

### `06-scoring-and-statistics.md` → §Gate-efficacy probes (Modify — extend the existing §Gate-efficacy probes section with two paragraphs)

Add after the existing definition of catch rate and escape rate:

> **Defect taxonomy.** The InjectedDefect generator works from a closed taxonomy of three `defectKind`s — `off-by-one`, `dropped-branch`, and `wrong-return` (`DEFECT_KINDS` in `benchmark/harness/scoring/probes/defects.py:53`). Each kind ships a concrete `before → after` line mutation against the seed instance's private reference solution; the catch-rate accounting breaks the rate down per kind in addition to the aggregate, so a gate that catches one kind of fault but misses another is visible in the report.
>
> **Live-probe verdict mapping.** The opt-in live gate probe (`benchmark/harness/scoring/probes/live.py`, gated by `BENCHMARK_RUN_GATE_PROBE_LIVE=1`) injects one classified mutation, runs the `semi-formal-review` gate as a bounded `claude -p` call, and maps the verdict line to `caughtBy`: verdicts in `{CONCERNS, BUGGY}` count as caught (with `caughtBy = "semi-formal-review"`); verdicts in `{CORRECT, LIKELY_CORRECT}` count as escaped. The PARTIAL / UNVERIFIED verdicts are unmapped — they should not appear on a defect-injected diff, so seeing one is a probe failure to report, not a silent third bucket.

---

## Implementation notes

This change spec is body-only — no code edits, no schema edits, no new entities. The merge step is a copy of the Proposed-changes blocks above into the named canonical sections.

Anchors for the merging agent:

```
1. 01-domain-model.md: add §Persistence and §Runtime aggregates as two new subsections
   after §Required query patterns, before §Assumptions and open questions.
2. 02-arms.md: replace the *A4 matches A1's parallelism budget* Decision; append the
   naive-merge paragraph at the end of §A4 — Parallel but unstructured; append the
   gate-observability paragraph at the end of §A3 — Build without gates.
3. 03-task-suites.md: append the `testTags` row to the greenfield field table; add
   §Per-instance assets as a new subsection between the greenfield narrative and
   §Suite: local-fixture; append the agent-image cross-link to §Implementation layout.
4. 05-harness-architecture.md: append the GateEvent threading paragraph to
   §Responsibilities; append the ArmOrSolver paragraph to §Backends.
5. 06-scoring-and-statistics.md: append the pairing-reduction paragraph to
   §Confidence intervals and pairwise tests; append the defect-taxonomy and
   live-probe-mapping paragraphs to §Gate-efficacy probes.
6. Bump each touched page's **Date:** to 2026-05-28.
```

The 03 §Implementation layout cross-link to the agent image assumes the companion change spec ([`2026-05-28-promote_built_state_and_resolved_decisions.md`](2026-05-28-promote_built_state_and_resolved_decisions.md)) has merged first (because it rewrites the §Implementation layout block on 03 from scratch). If this change spec merges first, the agent-image pointer should still land at the end of the existing §Implementation layout block; the §Implementation layout rewrite from the companion change spec then carries it through.

---

## Merge plan

1. **Merge ordering.** Merge the companion change spec [`2026-05-28-promote_built_state_and_resolved_decisions.md`](2026-05-28-promote_built_state_and_resolved_decisions.md) **first**, because (a) its §Implementation layout rewrites on 03/05/06 are the base this change spec extends, and (b) its `task slug` example bump in §ID scheme references the same canonical slug (`greenfield__text_toolkit__0001`) this change spec assumes when describing the `reference/solution.patch` self-test. Then merge this one.
2. Apply each Proposed-changes block to its canonical page; bump that page's `**Date:**` to the merge date.
3. There are no schema changes; the `Type changes` section is intentionally omitted.
4. No new canonical page is added.
5. Flip this file's `**Status:**` to `Merged`, add a `**Merged:** YYYY-MM-DD` field to its header, and move it to `docs/benchmark/specs/changes/merged/`.
6. Update `docs/README.md`: remove the file from the *Change specs → Pending* list, add a one-line entry in the *Change specs → Merged* list.
7. Sanity-check the merged canonical pages with the spec-creator checklist: every cross-link still resolves; each touched page's closing block is intact; no MVP/Draft framing leaks back in; every new prose block names existing code that backs it.

---

## Assumptions and open questions

**Assumptions**

- The integration tip `4184092d` on the `spec-workflow-benchmark` bookmark is the reality this change spec describes. If the bookmark advances before merge, the file:line anchors in §Implementation notes may shift but the §Proposed changes blocks are anchored by section name and stay valid.
- The §Persistence subsection on `01-domain-model.md` is the right home for the JSONL helpers. The alternative (placing them on `05-harness-architecture.md` as a §Driver-adjacent concern) is also defensible; this change spec puts them on 01 because they operate over the entities 01 defines, not over the driver's runtime shape.

**Decisions**

- *Body-only, no schema delta.* **No `Type changes` section.** Every field this change spec names (`TrialResult.gate_events`, `TaskInstance.testTags`, the `GATE_VERDICTS` enum, etc.) already exists in `canonical-types.schema.json`. The gap is body prose; widening the schema would be a separate, second-order change.
- *One change spec per coherent kind of edit.* **This one covers Group C only.** Group B (build-status updates + resolved Open questions → Decisions + layout fixes) is the companion change spec [`2026-05-28-promote_built_state_and_resolved_decisions.md`](2026-05-28-promote_built_state_and_resolved_decisions.md). Mixing them would make either harder to review.

**Open questions**

- *Where does `ArmOrSolver` belong?* This change spec puts it on `05-harness-architecture.md` (it is a backend-interface concern). The original R2 review noted it could also be a `01-domain-model.md` concern (it is a polymorphic input to the run side, which is what the domain model lays out). If `01` is preferred, the §Backends paragraph here moves to a §Inputs subsection under 01's §Entities; the prose is otherwise unchanged.
- *Naming for the per-instance asset section.* The proposed subheading is §Per-instance assets, placed under §Suite: greenfield-features. If spec-creator prefers per-asset-type sub-subheadings (§Given specs, §Reference solutions, §Test tags), the merge can split the paragraph into three; the proposed-changes blocks above already separate each asset's prose by bullet.
