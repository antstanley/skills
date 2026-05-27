# 06 — Scoring and Statistics

This page defines how a candidate patch becomes a `ScoreReport`, and how per-trial reports become per-arm `MetricResult`s with confidence intervals and pairwise deltas. It is the scoring half of the architecture in [05-harness-architecture.md](05-harness-architecture.md) and the treatment behind the quantities in [04-metrics.md](04-metrics.md).

---

## Responsibilities

Scoring decides, for each Trial, whether the candidate resolved the task and how well it conforms to the spec, in a container the run never touched. Statistics decides, for each (Arm, Suite) and each arm pair, what the trials say with what confidence. Scoring owns the per-trial truth; statistics owns the aggregate claim.

Neither step is ever run by the arm under test. The oracle is the harness's, not the workflow's — the integrity rule of [05-harness-architecture.md](05-harness-architecture.md).

---

## The test oracle

Per Trial, in the clean scoring container:

1. Start from the TaskInstance base image.
2. Apply the `candidatePatch`.
3. Inject the hidden `failToPass` and `passToPass` test selectors (absent from the run container).
4. Run them.

A trial is **resolved** when *every* `failToPass` test passes and *every* `passToPass` test still passes — the SWE-bench Pro convention. Two derived facts are recorded on the `ScoreReport`:

- **regressed** — a `passToPass` test that previously passed now fails. A trial can be both `resolved: false` and `regressed: true`.
- **gateEscape** — for arms with gates, a `Done` task whose hidden tests fail: the false-`Done` signal that feeds the gate-efficacy metric ([04-metrics.md](04-metrics.md)). Per-task attribution requires the instance's `testTags` mapping ([01-domain-model.md](01-domain-model.md)) to link a failing test to the spec section a `Done` task claims via its `Implements` pointer. Absent that mapping, escape is recorded only at instance granularity — the whole plan reached `Done` yet the instance is unresolved.

The `failToPass` / `passToPass` split is the same for both suites; only the source of the tests differs ([03-task-suites.md](03-task-suites.md)).

---

## The conformance judge

Resolution is necessary but not sufficient: code can pass the hidden tests while diverging from the spec (arXiv 2601.03878). For arms that produced a spec (and for the greenfield suite generally), a **rubric-driven LLM judge** scores how well the final code satisfies the spec, written to `ScoreReport.conformanceScore` in `[0, 1]`.

The judge is not taken on faith. It is **calibrated against human labels** on a sample of trials, and its score is reported with a stated agreement figure against those labels. Where the spec-creator plugin's own `spec-reviewer` (R2 canonical / R3 change) is available, it serves as the judge's procedure; otherwise the judge applies the same conformance rubric directly.

---

## Gate-efficacy probes

The gate metrics ([04-metrics.md](04-metrics.md)) need cases with a *known* answer, which organic trials do not supply. Probes provide them:

- **Injected defects.** A known-bad patch (`InjectedDefect`, classified by `defectKind`) is introduced into a gated build, and the harness records whether a gate flagged it (`caughtBy`) or it escaped. Aggregated, this is the **catch rate**.
- **False-`Done` escapes.** Across organic gated trials, the fraction of `Done` tasks with failing hidden tests is the **escape rate**.

Catch rate and escape rate bound gate quality from opposite sides ([04-metrics.md](04-metrics.md) → Bucket 3). Both depend on the gates never having seen the hidden suite — the integrity rule of [05-harness-architecture.md](05-harness-architecture.md).

---

## Repetition and Pass@k

Agentic arms are nondeterministic even at a fixed seed. Each TaskInstance is therefore run `trialsPerInstance` times per arm ([01-domain-model.md](01-domain-model.md)):

- **Pass@1** — mean resolution over single trials; the headline outcome.
- **Pass@k** — fraction of instances resolved by at least one of `k` trials; reported to separate "can the arm ever do this" from "does it do this reliably".

Only `scored` trials enter the statistics; `failed` (infra) trials are excluded and re-queued ([05-harness-architecture.md](05-harness-architecture.md)).

---

## Confidence intervals and pairwise tests

| Quantity | Treatment |
|---|---|
| **Per-arm %Resolved** | Point estimate with a **95% binomial confidence interval**, as SWE-bench Pro reports. |
| **Arm-pair delta** (e.g. A1 − A0) | Computed on **paired** TaskInstances — the same instances run by both arms — using **McNemar's test** on the discordant pairs (resolved-by-one-not-the-other). |
| **Cost-matched delta** | The same paired comparison after equalising the token/dollar budget across the two arms ([04-metrics.md](04-metrics.md)). |

Pairing is what gives the deltas their power: because both arms in a comparison face the *same* instances, shared task difficulty and shared training-data contamination cancel out, and the test sees only the difference the arm makes. The arm pairs and what each isolates are defined in [02-arms.md](02-arms.md).

---

## Reporting

A Campaign's output is an **ablation table**, not a single rank: each row an arm, each column a metric (Pass@1, cost-matched Pass@1, regression rate, conformance, gate catch/escape), every cell a value with its 95% interval, and the four pairwise-delta rows (A1−A0, A1−A2, A2−A3, A1−A4) called out with their McNemar results. This format makes the attribution claim — *which stage of the workflow earns its keep* — the readable result, in line with the *SWE-Skills-Bench* discipline (arXiv 2603.15401).

---

## Implementation layout

```
benchmark/
  harness/
    scoring/
      oracle/         # clean-container test runner → resolved / regressed / gateEscape
      conformance/    # rubric judge + human-label calibration harness
      probes/         # InjectedDefect generation and catch-rate accounting
    stats/            # binomial CIs, McNemar, Pass@k, cost-matching, ablation-table render
```

---

## Assumptions and open questions

**Assumptions**

- The hidden test suites are deterministic enough that a resolved/not-resolved verdict is stable across scoring-container runs of the same patch.
- A patch produced by a parallel arm applies cleanly in the scoring container against `baseCommit` (depends on the patch-extraction question in [05-harness-architecture.md](05-harness-architecture.md)).

**Decisions**

- *Resolution follows the SWE-bench Pro convention.* **All `failToPass` pass and all `passToPass` hold.** Reusing the established definition keeps A0's numbers comparable to the published leaderboard.
- *Deltas are paired and tested with McNemar.* **Same instances, both arms.** Pairing cancels shared difficulty and contamination, which is what makes the within-suite comparison hold despite the `public` tier of the SWE-bench Pro suite.
- *Output is an ablation table, not a rank.* **Per-arm metrics plus four delta rows.** A single leaderboard number would discard the attribution the benchmark is built to produce.

**Open questions**

- *Trial count.* How many `trialsPerInstance` are needed to stabilise Pass@1 intervals given agent nondeterminism, and does that count fit the cost budget? Drives the suite-size power analysis in [03-task-suites.md](03-task-suites.md).
- *Conformance calibration.* The human-label agreement threshold and sample size that make `conformanceScore` reportable (shared with [00-overview.md](00-overview.md) and [04-metrics.md](04-metrics.md)).
- *Multiple-comparison correction.* Four pairwise deltas per suite invite a multiple-comparison adjustment; whether to apply one, and which, is unsettled.
- *Per-task escape attribution.* The per-task false-`Done` rate needs `testTags` on greenfield instances plus a join through each task's `Implements` pointer. How reliably can hidden tests be tagged to spec sections at authoring time, and is the instance-granularity fallback informative enough where they cannot?
