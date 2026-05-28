# Change: Promote built state and resolved decisions into the canonical spec

**Status:** Merged · **Date:** 2026-05-28 · **Merged:** 2026-05-28 · **Owner:** Ant Stanley · **Target:** apps/benchmark

The benchmark harness described by `docs/benchmark/specs/` has shipped — milestones M0–M4 are merged on the `spec-workflow-benchmark` bookmark (integration tip `4184092d`), 262 tests pass, and every per-task certificate is `Validated`. In the course of building it, five Open questions were resolved (with the resolutions encoded as named constants in code), one §Substrate paragraph drifted out of date, two §Implementation layout boxes drifted out of date, the `dockerImage` row on greenfield's field table was written before the two-image build crystallised, and the §ID-scheme example slug names an instance the suite does not author. This change spec catches the canonical pages up to that built reality. **No schema changes**, no new content; every block here is a stale paragraph rewritten to describe what already exists in the current branch.

---

## Motivation

A canonical spec is "the canonical definition of what exists in the current branch" — code that ships, decisions that have been made, layouts that the harness actually has. The benchmark spec was authored in `Draft` at the start of the build with explicit framing ("No component described here is implemented … `Status: Draft` records that the build has not started"). That framing earned its place at the time. It is now wrong: the build started, ran to M4, and shipped. Leaving it asserts a false reality every reviewer has to mentally subtract.

The same pattern shows up smaller in five Open questions. Each was honestly Open when written; each was resolved during the build with a named constant or a dedicated module; each is still listed as Open in the canonical page. spec-creator's "Decisions" pattern exists for exactly this case — once a non-obvious choice is made, the question moves out of `Open questions` and into `Decisions` with a short rationale and a pointer to where the choice lives in code. Carrying these resolutions in code without ever recording them in the spec breaks the contract that the canonical pages describe the current branch.

The remaining edits (§Substrate, §Implementation layout on 05 and 06, the `dockerImage` row on 03, the example slug on 01) are the same shape: prose that was accurate at draft time and now under- or over-describes what shipped.

---

## Affected spec pages

| Canonical page | Nature of change |
|---|---|
| [`00-overview.md`](../../00-overview.md) | `Status: Draft → Built`; rewrite the "No component described here is implemented" preamble; replace the Scope-summary "Implementation: None" row with a row that names what shipped; close the *Build sequence* Open question with a Decision pointing at the executed plan |
| [`01-domain-model.md`](../../01-domain-model.md) | Replace the §ID-scheme example slug `greenfield__url_shortener` with a real bundled slug |
| [`02-arms.md`](../../02-arms.md) | Promote *Given-spec provenance for A2/A3* and *A4 decomposition policy* from Open questions to Decisions |
| [`03-task-suites.md`](../../03-task-suites.md) | Rewrite the greenfield field-table `dockerImage` row to reflect the two-image build |
| [`04-metrics.md`](../../04-metrics.md) | Promote *Conformance judge trust* and *Cost-matching method* from Open questions to Decisions |
| [`05-harness-architecture.md`](../../05-harness-architecture.md) | Rewrite §Substrate to record the substrate finding (BenchFlow used for task authoring, the two-container split stays on the benchmark seam); update §Implementation layout to list `backends/`, `substrate.py`, `domain.py`, `stats/` |
| [`06-scoring-and-statistics.md`](../../06-scoring-and-statistics.md) | Promote *Multiple-comparison correction* to a Decision; rewrite §Implementation layout to drop the absent `scoring/oracle/` subdirectory |

No new canonical page is added; no schema fragment is changed.

---

## Proposed changes

Each block below is the prose as it should read in the canonical page after merge. Marked **Modify** when replacing existing prose, **Add** when adding a new entry to an existing list, **Remove** when deleting an entry.

### `00-overview.md` → header (Modify)

> # spec-workflow-benchmark — Design Overview
>
> **Status:** Built · **Date:** 2026-05-28 · **Owner:** Ant Stanley · **Scope:** apps/benchmark

### `00-overview.md` → intro paragraph 3 (Modify)

> The harness is implemented and running. The benchmark package under `benchmark/` covers every component this spec set defines — driver, backends (`local` and `container`), arms A0–A4, the greenfield-features and local-fixture suites, the scoring and conformance and probes layers, and the full five-arm ablation report. `Status: Built` records that the build has shipped; the implementation history is in [`docs/plans/2026-05-27-spec_workflow_benchmark/`](../../../../plans/2026-05-27-spec_workflow_benchmark/plan.md).

### `00-overview.md` → §Scope summary, the "Implementation" row (Modify)

> | Implementation | Built and tested | The whole pipeline ships under `benchmark/`; live arms verified end to end on the greenfield seed (`benchmark/tests/_a*_live_evidence/`). See [`benchmark/README.md`](../../../../benchmark/README.md) for how to run a campaign. |

### `00-overview.md` → §Assumptions and open questions, *Build sequence* Open question (Modify — promote to Decisions)

Remove from `**Open questions**`:

> - *Build sequence.* How the harness is decomposed into reviewable task packages and milestones is a plan, not a spec — it belongs to `spec-planner`, run against this spec. What is the minimal first slice (which arms, how many instances) that proves the harness end to end?

Add under `**Decisions**`:

> - *Build sequence.* **M0 (Docker-free local pipeline) → M1 (greenfield suite + container backends + A0) → M2 (A1 + the A1−A0 delta) → M3 (A2/A3 + A4) → M4 (conformance, gate efficacy, cost-matched, the full ablation report).** Decomposed and executed in [`docs/plans/2026-05-27-spec_workflow_benchmark/`](../../../../plans/2026-05-27-spec_workflow_benchmark/plan.md); 23 reviewable task packages, each gated by `semi-formal-review` (correctness) and `validate-done-certificate` (completeness) before merge.

### `01-domain-model.md` → §ID scheme, the `task slug` row of the prefix table (Modify)

> | task slug (suite-scoped, e.g. `greenfield__text_toolkit__0001`) | TaskInstance |

### `02-arms.md` → §Assumptions and open questions, *Given-spec provenance for A2/A3* (Modify — promote to Decisions)

Remove from `**Open questions**`:

> - *Given-spec provenance for A2/A3.* Should the handed-in spec be authored by `spec-creator` in a separate pass (risking that A2 then partly measures spec-creator anyway), by a human, or drawn from the greenfield suite's authoring materials? The choice affects what A1 − A2 means.

Add under `**Decisions**`:

> - *Given-spec provenance for A2/A3.* **A frozen, human-authored spec per instance**, checked into the suite at `benchmark/suites/greenfield-features/<slug>/given_spec/given_spec.md` and consumed identically (same bytes) by both A2 and A3. Authored once to the fixed quality bar named in `benchmark/harness/arms/a2_a3.py::GIVEN_SPEC_QUALITY_BAR` (overview → domain model and invariants → one contract section per component with ≥2 worked examples → definition of done). A per-run `spec-creator` pass would make A2 partly re-measure spec-creator (defeating A1 − A2) and inject run-to-run spec variance into A2 − A3; a human-frozen shared asset removes both confounds.

### `02-arms.md` → §Assumptions and open questions, *A4 decomposition policy* (Modify — promote to Decisions)

Remove from `**Open questions**`:

> - *A4 decomposition policy.* What counts as a fair "naive split" — fixed file/region partition, or a single unstructured "split this N ways" prompt — needs pinning so A4 is reproducible.

Add under `**Decisions**`:

> - *A4 decomposition policy.* **A fixed, prompt-only N-way split with no intelligent planning.** All `N` agents receive the identical full `problemStatement` plus a coordination-free framing ("you are agent _i_ of _N_ working concurrently with no coordination and no shared plan; implement your share"). No coordinator chooses the slices — a component partition was rejected because producing a sensible partition is itself planning, which would smuggle (un-gated) planning value into A1 − A4. The fixed template lives in `benchmark/harness/arms/a4.py::A4_SLICE_INSTRUCTION`; `N = A4_N = 4`, matching A1's typical task count on the seed.

### `03-task-suites.md` → §Suite: `greenfield-features`, the `dockerImage` row of the field table (Modify)

> | `dockerImage` | the per-instance **run image** tag, hidden tests excluded; a matching scoring image with the hidden tests overlaid is built alongside but lives outside `TaskInstance` (see [05-harness-architecture.md](05-harness-architecture.md) → §Run container) |

### `04-metrics.md` → §Assumptions and open questions, *Conformance judge trust* (Modify — promote to Decisions)

Remove from `**Open questions**`:

> - *Conformance judge trust.* What human-label agreement threshold makes the conformance score reportable, and how large a calibration sample reaches it? (Shared with [00-overview.md](00-overview.md).)

Add under `**Decisions**`:

> - *Conformance judge trust.* **A calibration sample of `MIN_CALIBRATION_SAMPLE_SIZE = 4` items at `MIN_CALIBRATION_AGREEMENT = 0.75` exact-bucket agreement, reported alongside Cohen's κ.** The judge's continuous scores are bucketed into three bands (low `[0, 0.34)`, partial `[0.34, 0.67)`, high `[0.67, 1.0]`); agreement is the exact-bucket-match fraction over the human-labelled sample. Both the sample size and the agreement threshold are deliberately modest given the current authoring scale (one seed instance and a small set of hand-labelled exemplars); a production-grade calibration should raise both as the seed grows. Named constants in `benchmark/harness/scoring/conformance/calibration.py:54-67`.

### `04-metrics.md` → §Assumptions and open questions, *Cost-matching method* (Modify — promote to Decisions)

Remove from `**Open questions**`:

> - *Cost-matching method.* Is the fair budget equalised on tokens, on dollars, or on wall-clock? Each privileges a different arm; the choice needs justifying before the headline delta is reported.

Add under `**Decisions**`:

> - *Cost-matching method.* **Dollars (`Telemetry.costUsd`) is the headline basis.** Tokens (`inputTokens + outputTokens`) and wall-clock (`wallClockSeconds`) are selectable via the `CostBasis` enum in `benchmark/harness/stats/cost_robustness.py:157` so an ablation report can factor out per-model pricing or compare at fixed time. The equal-budget rule is `B = min over arms of max(per-trial cost)`: the cheaper arm pays no penalty, the more expensive arm's overshoots count as un-resolved, and the cost-matched %Resolved is `|{trial : cost ≤ B AND resolved}| / n_scored` — the literal "for the same spend" comparison the bucket calls for.

### `05-harness-architecture.md` → §Substrate — BenchFlow (Modify)

> ## Substrate — BenchFlow
>
> The harness uses the **BenchFlow `bench` SDK** ([benchflow-ai/benchflow](https://github.com/benchflow-ai/benchflow)) as a complementary layer for task authoring and validation — `bench tasks init` and `bench tasks check` validate a probe task in `benchmark/suites/benchflow-probe/` against BenchFlow's task layout, so the benchmark stays compatible with that SDK without depending on it for runtime execution.
>
> The **runtime substrate** for the two-container split and the custom `TaskInstance` schema is the benchmark's own `RunBackend` / `ScoringBackend` seam, recorded as a substrate finding in `benchmark/harness/substrate.py` (named constants `BENCH_TASKS_CLI_AVAILABLE = True`, `BENCH_NATIVE_TWO_CONTAINER_SPLIT = False`, `BENCH_VALIDATES_TASKINSTANCE_SCHEMA = False`). BenchFlow's stock `bench eval create` runs an agent rollout in the task's single sandbox and then runs the verifier in that same sandbox; the benchmark's integrity rule (a fresh scoring container distinct from the run container, hidden tests injected only there) is not expressible in that eval model, so the run/scoring split lives on the benchmark's own seam. Reusing BenchFlow for authoring keeps the probe task discoverable by `bench tasks check`; the bespoke surface shrinks to the two backend protocols and the arm provisioning recipes.

### `05-harness-architecture.md` → §Implementation layout (Modify)

> ## Implementation layout
>
> ```
> benchmark/
>   harness/
>     driver/            # matrix expansion, Trial scheduler, lifecycle
>     backends/          # RunBackend / ScoringBackend Protocols + container + local impls
>     arms/              # one provisioning recipe per Arm (plugins, flags, exec mode)
>     scoring/           # the clean-container oracle runner + shared resolution rule
>     telemetry/         # token/cost/wall-clock/turn capture → ArtifactBundle.telemetry
>     stats/             # binomial CIs, McNemar, Pass@k, cost-matching, ablation-table render (see 04, 06)
>     domain.py          # entity records (Campaign, Trial, ScoreReport, …; see 01)
>     substrate.py       # the BenchFlow substrate finding (see §Substrate)
>     run_local_demo.py  # Docker-free pipeline demo entrypoint
>   suites/              # TaskInstance records + greenfield skeletons + local-fixture + benchflow-probe (see 03)
> ```

### `05-harness-architecture.md` → §Assumptions and open questions, *Build on BenchFlow* Decision (Modify)

> - *Build on BenchFlow only for task authoring.* **`bench tasks check` is wired against a probe; the runtime two-container split stays on the benchmark's own backend seam.** BenchFlow's stock eval runs the agent and the verifier in one sandbox, which collapses the integrity rule. The substrate finding in `benchmark/harness/substrate.py` records this narrowing; the bespoke surface is the two backend protocols.

### `06-scoring-and-statistics.md` → §Implementation layout (Modify)

> ## Implementation layout
>
> ```
> benchmark/
>   harness/
>     scoring/
>       resolution.py       # the shared resolved/regressed rule, single-sourced across backends
>       local.py            # local ScoringBackend (Docker-free temp checkout)
>       container.py        # container ScoringBackend (fresh scoring container, hidden tests baked in)
>       conformance/        # rubric judge + human-label calibration harness
>       probes/             # InjectedDefect generation, catch-rate accounting, escape rate, opt-in live probe
>     stats/                # binomial CIs, McNemar, Pass@k, cost-matching, artifact metrics, ablation report
> ```

### `06-scoring-and-statistics.md` → §Assumptions and open questions, *Multiple-comparison correction* (Modify — promote to Decisions)

Remove from `**Open questions**`:

> - *Multiple-comparison correction.* Four pairwise deltas per suite invite a multiple-comparison adjustment; whether to apply one, and which, is unsettled.

Add under `**Decisions**`:

> - *Multiple-comparison correction.* **Holm-Bonferroni at α = 0.05 across the four pairwise deltas (A1 − A0, A1 − A2, A2 − A3, A1 − A4).** With four planned comparisons the uncorrected family-wise error rate is roughly `1 - 0.95^4 ≈ 0.185`, so omitting a correction is not honest at this many tests. Holm-Bonferroni (Holm 1979) is the textbook step-down procedure: uniformly more powerful than plain Bonferroni at the same family-wise rate, parameter-free, and valid under arbitrary dependence (which is what we have — the four deltas share arms). Each delta row carries the raw McNemar p-value, a Holm-Bonferroni-adjusted p-value, and a binary `significant_at_alpha` flag. The named constant `HOLM_BONFERRONI_ALPHA` lives in `benchmark/harness/stats/ablation_report.py:151`.

---

## Implementation notes

This change is prose-only — no code edits, no schema edits, no new entities. The merge step is a copy of the Proposed-changes blocks above into the named canonical sections.

Anchors for the merging agent:

```
1. 00-overview.md: replace lines 1-3 (header), line 9 (intro paragraph 3),
   line 97 (Scope summary "Implementation" row), and the *Build sequence* bullet
   in the Open questions block (currently the first bullet).
2. 01-domain-model.md: replace the `task slug` row of the prefix table in §ID scheme
   (currently uses `greenfield__url_shortener`).
3. 02-arms.md: remove the *Given-spec provenance for A2/A3* and *A4 decomposition
   policy* bullets from §Open questions, add the matching Decision bullets to §Decisions.
4. 03-task-suites.md: replace the `dockerImage` row of the §Suite: greenfield-features
   field table.
5. 04-metrics.md: remove the *Conformance judge trust* and *Cost-matching method*
   bullets from §Open questions, add the matching Decision bullets to §Decisions.
6. 05-harness-architecture.md: replace §Substrate — BenchFlow in full; replace
   §Implementation layout in full; replace the *Build on BenchFlow rather than
   bespoke* Decision in §Assumptions and open questions.
7. 06-scoring-and-statistics.md: replace §Implementation layout in full; remove
   the *Multiple-comparison correction* bullet from §Open questions, add the
   matching Decision bullet to §Decisions.
8. Bump each touched page's **Date:** to 2026-05-28.
```

The shared cross-references between resolved Open questions and `00-overview.md` are handled by the merge order above: `00-overview.md` no longer cross-links to *Conformance judge trust* once it lives as a Decision on `04-metrics.md`; the resolved Decision text records the cross-page resolution in one place.

---

## Merge plan

1. Apply each Proposed-changes block to its canonical page; bump that page's `**Date:**` to the merge date.
2. There are no schema changes; the `Type changes` section is intentionally omitted.
3. No new canonical page is added.
4. Flip this file's `**Status:**` to `Merged`, add a `**Merged:** YYYY-MM-DD` field to its header, and move it to `docs/benchmark/specs/changes/merged/`.
5. Update `docs/README.md`: remove the file from the *Change specs → Pending* list, add a one-line entry in the *Change specs → Merged* list.
6. Sanity-check the merged canonical pages with the spec-creator checklist: every cross-link still resolves; each touched page's closing block is intact; no MVP/Draft framing leaks back in.

---

## Assumptions and open questions

**Assumptions**

- The integration tip `4184092d` on the `spec-workflow-benchmark` bookmark is the reality this change spec is catching up to. If the bookmark advances before merge, the few file:line anchors in §Implementation notes may shift but the §Proposed changes blocks are anchored by section name and stay valid.

**Decisions**

- *One change spec, two groups.* **Group B only (spec staleness and layout drift).** Group C (shipped surfaces the spec body never named — persistence helpers, runtime aggregates, A4 budget matching, the given-spec asset, GateEvent threading, etc.) is a separate change spec under [`2026-05-28-document_shipped_surfaces.md`](../2026-05-28-document_shipped_surfaces.md). The two kinds of edit are coherent on their own and mixing them would make either change spec harder to review.
- *No schema delta.* **Body-only.** Every field this change spec mentions already exists in `canonical-types.schema.json`; the gap is in the prose that describes them, not in the type definitions.

**Open questions**

- *Should the resolved Open questions stay cross-linked back to the page they were shared with?* `00-overview.md` previously linked *Conformance judge trust* to `04-metrics.md`'s Open questions. Once both move to Decisions, the cross-link is redundant; this change spec drops it. If a different convention is preferred (keep a "see also" pointer between the two Decision bullets), spec-creator authors the small addition before merge.
