# 04 — Metrics

This page defines what the benchmark measures. Metrics are computed from `ScoreReport`s and `ArtifactBundle`s over the Trials of an (Arm, Suite), and surfaced as `MetricResult` records with confidence intervals ([01-domain-model.md](01-domain-model.md)). The statistics that turn per-trial scores into per-arm intervals and pairwise deltas live in [06-scoring-and-statistics.md](06-scoring-and-statistics.md); this page defines the quantities, that page defines their treatment.

---

## Responsibilities

The metric set answers three questions the design exists to answer: *did the code work*, *what did it cost*, and *did the workflow's own machinery (spec, plan, gates) do its job*. A single outcome score answers only the first; a benchmark of a workflow needs all three, because a workflow can resolve more tasks while costing more than it is worth, or pass tests while diverging from the spec (arXiv 2601.03878).

Metrics are grouped in four buckets. Every metric is reported per (Arm, Suite); the headline reports are the pairwise deltas from [02-arms.md](02-arms.md).

---

## Bucket 1 — Outcome

The "did it work" bucket.

| Metric | Definition | Source |
|---|---|---|
| **%Resolved (Pass@1)** | Fraction of trials where every `failToPass` test passes and every `passToPass` test still passes. | `ScoreReport.resolved` |
| **Pass@k** | Fraction of instances resolved by at least one of `k` trials. | aggregate over trials |
| **Regression rate** | Fraction of trials where a previously-passing `passToPass` test now fails. | `ScoreReport.regressed` |

`%Resolved` is the headline outcome metric, read pairwise against the A0 baseline ([02-arms.md](02-arms.md)). Regression rate is reported separately because a multi-agent merge can resolve the target while breaking something adjacent — a failure mode the parallel arms (A1, A2, A3, A4) risk more than A0.

---

## Bucket 2 — Cost and efficiency

The "what did it cost" bucket. **Mandatory** — the workflow arms consume far more tokens than A0, so a raw `%Resolved` comparison flatters the workflow. All cost metrics read from `ArtifactBundle.telemetry`.

| Metric | Definition |
|---|---|
| **Tokens per trial** | `inputTokens + outputTokens`, mean over trials. |
| **Cost per trial** | `costUsd`, mean over trials. |
| **Wall-clock per trial** | `wallClockSeconds`, mean over trials. |
| **Cost-matched %Resolved** | `%Resolved` recomputed at an equalised token (or dollar) budget across arms. The fair A1-vs-A0 comparison. |
| **Parallel speedup** | A1's wall-clock vs the same plan run sequentially, correlated with task-graph width. |

Cost-matched %Resolved is the bucket's headline. Raw %Resolved says whether the workflow *can* do better; cost-matched %Resolved says whether it does better *for the same spend*. Parallel speedup, correlated against graph width, tests the multi-agent finding that concurrency helps wide graphs but not narrow ones (Augment / vibecoding evidence in [00-overview.md](00-overview.md)).

---

## Bucket 3 — Process and artifact quality

The "did the workflow's machinery work" bucket. These metrics are unobtainable from a black-box outcome score and are the benchmark's distinctive contribution. Applicability varies by metric and arm:

- **Spec conformance** is scored on the greenfield suite for *every* arm: the spec is the instance input, so even A0 and A4 are judged against it, and A1's authored spec (or the spec handed to A2 and A3) is judged the same way.
- **Plan coverage** and **DAG validity** apply to the arms that produce a plan — A1, A2, A3.
- The two **gate** metrics apply to the arms that run gates — A1 and A2 (A3 disables them; A0 and A4 have none).

| Metric | Definition | Source |
|---|---|---|
| **Spec conformance** | Degree to which the final code satisfies the spec, scored by a rubric-driven LLM judge calibrated against human labels. | `ScoreReport.conformanceScore` |
| **Plan coverage** | Fraction of in-scope spec sections mapped to at least one plan task. | `planArtifacts` analysis |
| **DAG validity** | Whether the plan's dependency graph is acyclic and every edge resolves. | `planArtifacts` analysis |
| **Gate catch rate** | Fraction of `InjectedDefect`s the gates flagged (true positive rate). | `InjectedDefect.caughtBy` |
| **False-`Done` escape rate** | Fraction of tasks the gates marked `Done` whose hidden tests fail. | `ScoreReport.gateEscape` |

The two gate metrics are the headline of this bucket and the empirical test of the workflow's central claim — that a task is only done when proven done by an agent other than its builder. **Gate catch rate** measures whether the gates catch deliberately injected faults; **false-`Done` escape rate** measures whether tasks the gates passed actually hold up against the hidden oracle. A high catch rate with a low escape rate is the gates working; the A2 − A3 delta ([02-arms.md](02-arms.md)) shows whether they change outcomes at all.

Spec conformance is reported alongside %Resolved precisely because the two can diverge: code can pass the hidden tests while violating the spec, and a spec can be conformant while the tests still fail. Reporting only one hides that divergence.

---

## Bucket 4 — Robustness

The "what went wrong along the way" bucket.

| Metric | Definition |
|---|---|
| **Merge-conflict rate** | Fraction of parallel trials where independent tasks conflicted at the integration point. |
| **Manual-pause rate** | Fraction of trials that hit an `UNVERIFIED` gate verdict requiring human sign-off. |
| **Gate retry depth** | Mean `retryIndex` reached before a task passed or was parked. |

Merge-conflict rate is a health signal for the plan's dependency edges — frequent conflicts between supposedly-independent tasks point at a missing edge. Manual-pause rate quantifies how hands-off a campaign actually is, and flags suites drifting toward UI-bound tasks the headless oracle cannot score.

---

## Implementation layout

Each metric is a named `MetricResult` keyed by (campaign, arm, suite, metricName), carrying `value` and a 95% interval ([`canonical-types.schema.json`](canonical-types.schema.json)). The aggregation reads `ScoreReport`s and `ArtifactBundle`s for the (Arm, Suite) and applies the treatment in [06-scoring-and-statistics.md](06-scoring-and-statistics.md). Pairwise-delta reports join two arms' MetricResults on shared TaskInstances.

---

## Assumptions and open questions

**Assumptions**

- Token and cost telemetry is recoverable identically for every arm, so cost-matched comparison is apples-to-apples.
- The LLM conformance judge, once calibrated, agrees with human labels closely enough to be reported with a stated agreement figure rather than as ground truth.

**Decisions**

- *Cost is co-equal with outcome, not a footnote.* **Cost-matched %Resolved is a headline.** A workflow that resolves more only by spending more has not been shown to help; the *SWE-Skills-Bench* discipline (arXiv 2603.15401) requires netting out the cost of the skill.
- *Gate efficacy is measured two ways.* **Injected-defect catch rate plus false-`Done` escape rate.** Catch rate alone can be gamed by a paranoid gate that fails everything; escape rate alone misses faults the hidden suite doesn't probe. Together they bound gate quality from both sides.
- *Conformance is separate from resolution.* **Both reported.** They measure different things and can disagree (arXiv 2601.03878); collapsing them into one number would hide the disagreement the benchmark wants to expose.
- *Conformance judge trust.* **A calibration sample of `MIN_CALIBRATION_SAMPLE_SIZE = 4` items at `MIN_CALIBRATION_AGREEMENT = 0.75` exact-bucket agreement, reported alongside Cohen's κ.** The judge's continuous scores are bucketed into three bands (low `[0, 0.34)`, partial `[0.34, 0.67)`, high `[0.67, 1.0]`); agreement is the exact-bucket-match fraction over the human-labelled sample. Both the sample size and the agreement threshold are deliberately modest given the current authoring scale (one seed instance and a small set of hand-labelled exemplars); a production-grade calibration should raise both as the seed grows. Named constants in `benchmark/harness/scoring/conformance/calibration.py:54-67`.
- *Cost-matching method.* **Dollars (`Telemetry.costUsd`) is the headline basis.** Tokens (`inputTokens + outputTokens`) and wall-clock (`wallClockSeconds`) are selectable via the `CostBasis` enum in `benchmark/harness/stats/cost_robustness.py:176` so an ablation report can factor out per-model pricing or compare at fixed time. The equal-budget rule is `B = min over arms of max(per-trial cost)`: the cheaper arm pays no penalty, the more expensive arm's overshoots count as un-resolved, and the cost-matched %Resolved is `|{trial : cost ≤ B AND resolved}| / n_scored` — the literal "for the same spend" comparison the bucket calls for.

**Open questions**

- *Defect injection realism.* Do hand-injected defects represent the faults the gates would face in practice, or should defects be mined from real failed trials instead?
