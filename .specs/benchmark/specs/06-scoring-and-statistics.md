# 06 — Scoring and Statistics

This page defines how a candidate patch becomes a `ScoreReport`, and how per-trial reports become per-arm `MetricResult`s with confidence intervals and pairwise deltas. It is the scoring half of the architecture in [05-harness-architecture.md](05-harness-architecture.md) and the treatment behind the quantities in [04-metrics.md](04-metrics.md).

---

## Responsibilities

Scoring decides, for each Trial, whether the candidate resolved the task and how well it conforms to the spec, in a container the run never touched. Statistics decides, for each (Arm, Suite) and each arm pair, what the trials say with what confidence. Scoring owns the per-trial truth; statistics owns the aggregate claim.

Neither step is ever run by the arm under test. The oracle is the harness's, not the workflow's — the integrity rule of [05-harness-architecture.md](05-harness-architecture.md).

---

## The test oracle

Per Trial, on the clean scoring side (a scoring container for the `container` backend, a fresh temp checkout for the `local` backend — [05-harness-architecture.md](05-harness-architecture.md) → Backends):

1. Start from the TaskInstance base.
2. Apply the `candidatePatch`.
3. Inject the hidden `failToPass` and `passToPass` test selectors (absent from the run side).
4. Run them.

The oracle runs under one of two conventions, selected by the suite and the active `ScoringBackend`:

- **`greenfield-hidden-tests`** — run the instance's withheld suite in a scoring container built with the hidden tests included (the `container` backend, greenfield suite).
- **`local`** — apply the candidate patch to a fresh temp checkout and run the hidden tests as a local subprocess (the `local` backend).

A trial is **resolved** when *every* `failToPass` test passes and *every* `passToPass` test still passes — identical across every backend and oracle convention. Two derived facts are recorded on the `ScoreReport`:

- **regressed** — a `passToPass` test that previously passed now fails. A trial can be both `resolved: false` and `regressed: true`.
- **gateEscape** — for arms with gates, a `Done` task whose hidden tests fail: the false-`Done` signal that feeds the gate-efficacy metric ([04-metrics.md](04-metrics.md)). Per-task attribution requires the instance's `testTags` mapping ([01-domain-model.md](01-domain-model.md)) to link a failing test to the spec section a `Done` task claims via its `Implements` pointer. Absent that mapping, escape is recorded only at instance granularity — the whole plan reached `Done` yet the instance is unresolved.

The `failToPass` / `passToPass` split is the same across suites and backends; only the source of the tests differs ([03-task-suites.md](03-task-suites.md)).

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

**Defect taxonomy.** The InjectedDefect generator works from a closed taxonomy of three `defectKind`s — `off-by-one`, `dropped-branch`, and `wrong-return` (`DEFECT_KINDS` in `benchmark/harness/scoring/probes/defects.py:53`). Each kind ships a concrete `before → after` line mutation against the seed instance's private reference solution; the catch-rate accounting breaks the rate down per kind in addition to the aggregate, so a gate that catches one kind of fault but misses another is visible in the report.

**Live-probe verdict mapping.** The opt-in live gate probe (`benchmark/harness/scoring/probes/live.py`, gated by `BENCHMARK_RUN_GATE_PROBE_LIVE=1`, and also driven as part of the live runtime-verification self-test, [05-harness-architecture.md](05-harness-architecture.md) → §Runtime verification) injects one classified mutation, runs the `semi-formal-review` gate as a bounded `claude -p` call, and maps the gate's verdict line — drawn from `semi-formal-review`'s own four-verdict vocabulary `CORRECT / LIKELY_CORRECT / CONCERNS / BUGGY` — to `caughtBy`: verdicts in `{CONCERNS, BUGGY}` count as caught (with `caughtBy = "semi-formal-review"`); verdicts in `{CORRECT, LIKELY_CORRECT}` count as escaped. A reply whose verdict line parses to none of those four — a malformed or missing verdict — is read conservatively as **escaped** (`verdict_caught` returns `False` on no match, `benchmark/harness/scoring/probes/live.py:150`); the probe never opens a third bucket. (The closed `GateVerdict` enum's `PARTIAL` / `UNVERIFIED` belong to the *organic* gate path, not the probe: `extract_gate_events` maps the review verdicts onto the enum via `_REVIEW_VERDICT_MAP` in `benchmark/harness/arms/a2_a3.py`, and a parked-for-human `VERDICT: UNVERIFIED` becomes the manual-pause signal there. The live probe maps straight to `caughtBy` and never produces a `GateVerdict`.) On the organic path, `extract_gate_events` reads each discharged certificate's `VERDICT:` line tolerant of markdown emphasis around the label: the live `validate-done-certificate` / `semi-formal-review` gates write the label BOLD under a `## Verdict` heading (the literal captured line is `**VERDICT:** DONE`), and italic (`*VERDICT:*`) or underscore-bold (`__VERDICT:__`) shapes are equally valid markdown, so the parser absorbs the emphasis markers around the label and between the colon and the verdict token. A bare `VERDICT: DONE` and a bolded `**VERDICT:** DONE` therefore both register as the same gate event, while an undischarged A3 certificate — still carrying the authored `**Verdict:** (blank …)` placeholder — continues to yield no event.

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
| **Per-arm %Resolved** | Point estimate with a **95% binomial confidence interval**. |
| **Arm-pair delta** (e.g. A1 − A0) | Computed on **paired** TaskInstances — the same instances run by both arms — using **McNemar's test** on the discordant pairs (resolved-by-one-not-the-other). |
| **Cost-matched delta** | The same paired comparison after equalising the token/dollar budget across the two arms ([04-metrics.md](04-metrics.md)). |

Pairing is what gives the deltas their power: because both arms in a comparison face the *same* instances, shared task difficulty and shared training-data contamination cancel out, and the test sees only the difference the arm makes. The arm pairs and what each isolates are defined in [02-arms.md](02-arms.md).

Each arm-instance pair is reduced to one resolved bool before McNemar pairs the arms: the rule is **`any` over the arm's `k` trials on that instance** (`benchmark/harness/stats/outcome.py::_instance_resolved_any`), so the pair's bool matches the `Pass@k` notion at `k = trialsPerInstance` and is well-defined at `k = 1`. Majority-of-trials was considered and rejected because it requires a tie-break rule at even `k`; `any` is parameter-free and the same shape the §Reporting ablation table already uses.

---

## Reporting

A Campaign's output is an **ablation table**, not a single rank: each row an arm, each column a metric (Pass@1, cost-matched Pass@1, regression rate, conformance, gate catch/escape), every cell a value with its 95% interval, and the four pairwise-delta rows (A1−A0, A1−A2, A2−A3, A1−A4) called out with their McNemar results. This format makes the attribution claim — *which stage of the workflow earns its keep* — the readable result, in line with the *SWE-Skills-Bench* discipline (arXiv 2603.15401).

---

## Implementation layout

```
benchmark/
  harness/
    scoring/
      resolution.py       # the shared resolved/regressed rule, single-sourced across backends
      local.py            # local ScoringBackend (Docker-free temp checkout)
      container.py        # container ScoringBackend (fresh scoring container, hidden tests baked in)
      conformance/        # rubric judge + human-label calibration harness
      probes/             # InjectedDefect generation, catch-rate accounting, escape rate, opt-in live probe
    stats/                # binomial CIs, McNemar, Pass@k, cost-matching, artifact metrics, ablation report
```

---

## Assumptions and open questions

**Assumptions**

- The hidden test suites are deterministic enough that a resolved/not-resolved verdict is stable across scoring-container runs of the same patch.
- A patch produced by a parallel arm applies cleanly in the scoring container against `baseCommit` (depends on the patch-extraction question in [05-harness-architecture.md](05-harness-architecture.md)).

**Decisions**

- *Resolution is all-or-nothing.* **All `failToPass` pass and all `passToPass` hold.** A single definition across backends and suites keeps the resolved verdict comparable across arms.
- *Deltas are paired and tested with McNemar.* **Same instances, both arms.** Pairing cancels shared difficulty and any training-data contamination, which is what makes the within-suite comparison hold.
- *Output is an ablation table, not a rank.* **Per-arm metrics plus four delta rows.** A single leaderboard number would discard the attribution the benchmark is built to produce.
- *Multiple-comparison correction.* **Holm-Bonferroni at α = 0.05 across the four pairwise deltas (A1 − A0, A1 − A2, A2 − A3, A1 − A4).** With four planned comparisons the uncorrected family-wise error rate is roughly `1 - 0.95^4 ≈ 0.185`, so omitting a correction is not honest at this many tests. Holm-Bonferroni (Holm 1979) is the textbook step-down procedure: uniformly more powerful than plain Bonferroni at the same family-wise rate, parameter-free, and valid under arbitrary dependence (which is what we have — the four deltas share arms). Each delta row carries the raw McNemar p-value, a Holm-Bonferroni-adjusted p-value, and a binary `significant_at_alpha` flag. The named constant `HOLM_BONFERRONI_ALPHA` lives in `benchmark/harness/stats/ablation_report.py:157`. The four **cost-matched** pairwise deltas ([04-metrics.md](04-metrics.md)) form a *second, independent* Holm-Bonferroni family, corrected the same way over the same four comparisons by `apply_holm_bonferroni_per_family` (`benchmark/harness/stats/ablation_report.py:465`), so the raw-delta and cost-matched-delta families each control their own family-wise error rate rather than sharing one.

**Open questions**

- *Trial count.* How many `trialsPerInstance` are needed to stabilise Pass@1 intervals given agent nondeterminism, and does that count fit the cost budget? Drives the suite-size power analysis in [03-task-suites.md](03-task-suites.md).
- *Conformance calibration.* The human-label agreement threshold and sample size that make `conformanceScore` reportable (shared with [00-overview.md](00-overview.md) and [04-metrics.md](04-metrics.md)).
- *Per-task escape attribution.* The per-task false-`Done` rate needs `testTags` on greenfield instances plus a join through each task's `Implements` pointer. How reliably can hidden tests be tagged to spec sections at authoring time, and is the instance-granularity fallback informative enough where they cannot?
