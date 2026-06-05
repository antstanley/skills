# Change: Add the SWE-bench Pro issue-fixing suite

**Status:** Proposed · **Date:** 2026-05-27 · **Owner:** Ant Stanley · **Target:** apps/benchmark

Add an `issue-fixing` suite, `swe-bench-pro-public`, that reuses [SWE-bench Pro](https://scaleapi.github.io/SWE-bench_Pro-os/)'s public instances, prebuilt Docker images (`jefzda/sweap-images`), and `fail-to-pass` / `pass-to-pass` test oracle. The suite runs the A0 baseline on the same tasks and the same hidden oracle as a published benchmark, so the floor arm's `%Resolved` sits on a recognised difficulty scale, and gives the workflow arms a second suite shape — fixing a long-horizon issue in existing code — alongside the greenfield build-from-spec suite. This restores a capability the canonical spec deliberately omitted to keep the first implementation minimal: the production architecture, the arm set, and the greenfield suite are unchanged; the change adds a suite kind, an oracle convention, and the prose that frames the comparability it buys.

---

## Motivation

The minimal canonical spec runs the ablation on a single suite — `greenfield-features` — plus the Docker-free `local-fixture` verification instance. Greenfield exercises the workflow's home ground (spec authoring, planning, the gates) but supplies no external calibration: every number is self-defined, so a reader cannot tell whether the A0 baseline is weak or strong in absolute terms, nor whether the suite's difficulty band is realistic. An issue-fixing suite anchored to a published benchmark closes that gap.

SWE-bench Pro is the natural anchor: it is a published, hidden-oracle, long-horizon SWE benchmark with prebuilt per-instance Docker images and a settled `fail-to-pass` / `pass-to-pass` resolution convention. Reusing its instances rather than re-deriving them means A0 runs the same tasks and the same oracle, so its `%Resolved` is comparable on tasks and oracle (a difficulty calibration, not a like-for-like leaderboard entry, since the published numbers use SWE-bench Pro's own reference agent). It also gives the workflow arms a task shape — issue-fixing on an existing codebase — that the greenfield suite cannot reach, widening what the benchmark observes. The cost is a hard dependency on Docker and the pullable public images, which is why it was deferred out of the minimal build and is reintroduced here as a self-contained addition.

---

## Affected spec pages

| Canonical page | Nature of change |
|---|---|
| [`00-overview.md`](../00-overview.md) | Restore the SWE-bench Pro prior-art framing in §Problem; add the reuse goal; add the suite to §System shape, the detail-pages table, and §Scope summary; add the images assumption and the baseline-benchmark decision |
| [`01-domain-model.md`](../01-domain-model.md) | Restore `swe-bench-pro-public` / `swepro__django__12345` in the ID-scheme table; restore the two-suite Suite description; add `issue-fixing` to `kind` and `swe-bench-pro` to `oracleConvention`; restore the issue-fixing `goldPatch` source and the `testTags` issue-fixing clause |
| [`02-arms.md`](../02-arms.md) | §A0: restore the SWE-bench Pro comparability sentence |
| [`03-task-suites.md`](../03-task-suites.md) | Add the **Suite: `swe-bench-pro-public`** section; restore the two-suite intro/responsibilities; restore the suite in §Implementation layout, the assumptions, and the decisions |
| [`04-metrics.md`](../04-metrics.md) | §Bucket 1: restore "comparable to SWE-bench Pro" and the leaderboard-comparability sentence; restore the issue-fixing clause in §Bucket 3 spec conformance |
| [`05-harness-architecture.md`](../05-harness-architecture.md) | §Backends: restore "reusing the SWE-bench Pro evaluation flow"; §Run container: restore the issue-fixing image bullet; §Scoring isolation: restore the SWE-bench Pro free-separation note |
| [`06-scoring-and-statistics.md`](../06-scoring-and-statistics.md) | §The test oracle: add the `swe-bench-pro` convention (back to three) and the SWE-bench Pro resolution attribution; restore "as SWE-bench Pro reports"; restore the two decisions |
| [`canonical-types.schema.json`](../canonical-types.schema.json) | Add `issue-fixing` to `Suite.kind` and `swe-bench-pro` to `Suite.oracleConvention` |

No new canonical page is added; the change extends existing pages.

---

## Proposed changes

Each block is the prose as it should read in the canonical page after merge.

### `00-overview.md` → §Problem (Modify)

> Existing code benchmarks answer a narrower question. [SWE-bench Pro](https://scaleapi.github.io/SWE-bench_Pro-os/) measures whether an agent resolves a long-horizon issue, scored by a hidden `fail-to-pass` / `pass-to-pass` test oracle. It evaluates a model-plus-agent as a single black box and reports one `%Resolved` number. It does not isolate the contribution of a workflow layered on top, and it does not exercise the spec-authoring and planning stages at all. The literature on agent skills warns that this gap matters: skills do not uniformly help (*SWE-Skills-Bench*, arXiv 2603.15401), and code that passes tests can still violate its specification (*Specification-Driven Code Generation*, arXiv 2601.03878). A benchmark for this workflow must attribute outcomes to workflow stages, not just report a single score.

### `00-overview.md` → §Goals (Add)

> 6. Reuse SWE-bench Pro's instances, Docker images, and test oracle for the issue-fixing suite, so the baseline arm's numbers are comparable to a published benchmark.

### `00-overview.md` → §System shape (Modify)

> ```
>    task registry (TaskInstance × Suite)
>    ┌─────────────────────────────────────────────────────────────┐
>    │  swe-bench-pro-public        greenfield-features             │
>    │  (issue + gold/test patch)   (spec + hidden test suite)      │
>    └───────────────────────────────┬─────────────────────────────┘
> ```

### `00-overview.md` → §Detail pages table (Modify)

> | [03-task-suites.md](../03-task-suites.md) | The SWE-bench Pro public suite and the greenfield feature suite |

### `00-overview.md` → §Scope summary (Modify)

> | Suites | Two: `swe-bench-pro-public` (11 repos), `greenfield-features` (newly authored) | [03-task-suites.md](../03-task-suites.md). Both built in parallel. |

### `00-overview.md` → §Assumptions (Add)

> - SWE-bench Pro's public Docker images (`jefzda/sweap-images`) and its `fail-to-pass` / `pass-to-pass` test data remain available for the issue-fixing suite.

### `00-overview.md` → §Decisions (Add)

> - *Baseline benchmark.* **SWE-bench Pro public set.** It is a published, hidden-oracle, long-horizon SWE benchmark, so the A0 arm's numbers are comparable to external results rather than self-defined.

### `01-domain-model.md` → §ID scheme table (Modify)

> | suite slug (`swe-bench-pro-public`, `greenfield-features`) | Suite |
> | task slug (suite-scoped, e.g. `swepro__django__12345`) | TaskInstance |

### `01-domain-model.md` → §Entities → Suite (Modify)

> A named collection of task instances drawn from one source with one oracle convention. Two suites exist by design: `swe-bench-pro-public` (issue-fixing, reusing SWE-bench Pro instances) and `greenfield-features` (build-from-spec, newly authored); the `local-fixture` suite is a Docker-free verification instance for the pipeline itself. See [03-task-suites.md](../03-task-suites.md).
>
> Carries:
>
> - `slug` — stable suite identifier.
> - `kind` — `issue-fixing`, `greenfield`, or `local-fixture`.
> - `oracleConvention` — `swe-bench-pro`, `greenfield-hidden-tests`, or `local`.

### `01-domain-model.md` → §Entities → TaskInstance → `goldPatch` (Modify)

> - `goldPatch` — reference solution, present for issue-fixing instances reused from SWE-bench Pro and for the `local-fixture` instance; `null` for greenfield, which has no single reference solution.

### `01-domain-model.md` → §Entities → TaskInstance → `testTags` (Modify)

> Absent it — and on issue-fixing, where it is always absent — escape is computed only at instance granularity.

### `02-arms.md` → §A0 — Baseline (Modify)

> A plain Claude Code agent on the fixed model, no `spec-*` plugins. It receives the TaskInstance's `problemStatement` and produces a patch. On the `swe-bench-pro-public` suite A0 runs the same tasks and the same hidden oracle as SWE-bench Pro, so its `%Resolved` is comparable on tasks and oracle — though not directly to a published leaderboard number, which is produced by SWE-bench Pro's own reference agent rather than plain Claude Code.

### `03-task-suites.md` → intro and §Responsibilities (Modify)

> This page defines the two suites of task instances the arms run against. Each suite is a `Suite` entity holding `TaskInstance`s ([01-domain-model.md](../01-domain-model.md)). The two suites are deliberately different in shape: one exercises issue-fixing on existing code, the other exercises building a feature from a specification — the workflow's home ground. A third suite, `local-fixture`, is harness infrastructure: a Docker-free instance that verifies the run → score → aggregate pipeline.

> Both ablation suites are in scope from the first campaign and are built in parallel; `local-fixture` exists only to verify the pipeline.

### `03-task-suites.md` → new section **Suite: `swe-bench-pro-public`** (Add)

Insert before §Suite: `greenfield-features`.

> ## Suite: `swe-bench-pro-public`
>
> **Kind:** `issue-fixing`. **Oracle convention:** `swe-bench-pro` (reused).
>
> Sourced from the [SWE-bench Pro](https://scaleapi.github.io/SWE-bench_Pro-os/) public set — 11 open-access repositories of long-horizon, multi-file issues. Each instance reuses SWE-bench Pro's own fields and Docker images rather than re-deriving them:
>
> | TaskInstance field | Source in SWE-bench Pro |
> |---|---|
> | `problemStatement` | the issue description |
> | `repo` / `baseCommit` | the instance's repo and base commit |
> | `goldPatch` | the reference solution patch |
> | `failToPass` / `passToPass` | the instance's test selectors |
> | `dockerImage` | the prebuilt `jefzda/sweap-images` tag |
> | `contaminationTier` | `public` |
>
> This suite's purpose is **comparability**: A0 runs the same tasks and the same hidden oracle as SWE-bench Pro, so its `%Resolved` sits on the same scale as the published results (top score ≈ 43.7%) — a calibration of difficulty, not a like-for-like leaderboard entry, since the published numbers use SWE-bench Pro's own reference agent rather than plain Claude Code. For the workflow arms, the issue text seeds a change spec rather than being patched directly.
>
> A caveat carries through to the metrics: the public set is `public` tier, so a base model may have seen these repositories. The comparison that matters here is *across arms on the same instances* (a within-suite, paired delta), which is insensitive to shared contamination because every arm faces the same exposure.

### `03-task-suites.md` → §Suite: `local-fixture` (Modify)

> The suite is not part of the ablation result; it is harness infrastructure. Real arms (A0–A4) and the comparative metrics still run on the `swe-bench-pro` and `greenfield-features` suites under the `container` backend.

### `03-task-suites.md` → §Implementation layout (Modify)

> ```
> benchmark/
>   suites/
>     swe-bench-pro-public/
>       instances.jsonl        # TaskInstance records, validated against canonical-types.schema.json
>       (Docker images referenced by tag; not vendored)
>     greenfield-features/
>       instances.jsonl        # TaskInstance records
>       <slug>/                # per-instance skeleton repo + withheld test suite
>     local-fixture/           # bundled fixture repo + hidden tests + goldPatch (Docker-free)
> ```

### `03-task-suites.md` → §Assumptions (Add)

> - SWE-bench Pro's public instances and `jefzda/sweap-images` tags remain pullable for the lifetime of the benchmark.

### `03-task-suites.md` → §Decisions (Modify)

> - *Two suites of different shape.* **Issue-fixing plus greenfield.** Issue-fixing buys comparability to a published baseline; greenfield exercises the spec-authoring and planning stages that issue-fixing leaves idle. One suite alone would under-test the workflow.
> - *Within-suite paired deltas are the primary readout.* **Arms compared on shared instances.** This makes the `public`-tier contamination on the SWE-bench Pro suite tolerable, since every arm shares the same exposure.

### `04-metrics.md` → §Bucket 1 — Outcome (Modify)

> The "did it work" bucket, comparable to SWE-bench Pro.

> `%Resolved` is the metric directly comparable across A0 and the published SWE-bench Pro leaderboard. Regression rate is reported separately because a multi-agent merge can resolve the target while breaking something adjacent — a failure mode the parallel arms (A1, A2, A3, A4) risk more than A0.

### `04-metrics.md` → §Bucket 3 — Process and artifact quality (Modify)

> - **Spec conformance** is scored wherever a spec exists to score against: on the greenfield suite for *every* arm (the spec is the instance input, so even A0 and A4 are judged against it), and on the issue-fixing suite for the arms that have a spec (A1 authored it; A2 and A3 were given it).

### `05-harness-architecture.md` → §Backends → `ScoringBackend` (Modify)

> - **`ScoringBackend`** — applies a `candidatePatch` to a clean copy of the instance base, injects the hidden tests, runs them, and returns a `ScoreReport`. Implementations: `container` (a fresh scoring container, reusing the SWE-bench Pro evaluation flow) and `local` (a fresh temp checkout, hidden tests run as a local subprocess).

### `05-harness-architecture.md` → §Run container (Modify)

> The `container` backend provisions per suite from the TaskInstance's `dockerImage`:
>
> - **Issue-fixing suite** — the SWE-bench Pro `jefzda/sweap-images` tag for the instance, reused as-is.
> - **Greenfield suite** — an image built for the instance from its skeleton repo, with the hidden test suite **excluded** from this image.

### `05-harness-architecture.md` → §Scoring isolation — the integrity rule (Modify)

> Without this separation, a workflow arm could discharge its gates against the very tests it is later scored on, overfitting the metric and making the gate-efficacy numbers ([04-metrics.md](../04-metrics.md)) meaningless. SWE-bench Pro gives this separation for free on the issue-fixing suite — the test patch is held out of the agent's environment — and the greenfield suite enforces it by construction, baking the hidden tests only into the scoring image. The gate-efficacy probes ([06-scoring-and-statistics.md](../06-scoring-and-statistics.md)) depend entirely on this rule holding.

### `06-scoring-and-statistics.md` → §The test oracle (Modify)

> The oracle runs under one of three conventions, selected by the suite and the active `ScoringBackend`:
>
> - **`swe-bench-pro`** — reuse SWE-bench Pro's evaluation harness in a scoring container (the `container` backend, issue-fixing suite).
> - **`greenfield-hidden-tests`** — run the instance's withheld suite in a scoring container built with the hidden tests included (the `container` backend, greenfield suite).
> - **`local`** — apply the candidate patch to a fresh temp checkout and run the hidden tests as a local subprocess (the `local` backend).
>
> A trial is **resolved** when *every* `failToPass` test passes and *every* `passToPass` test still passes — the SWE-bench Pro convention, identical across every backend and oracle convention.

### `06-scoring-and-statistics.md` → §Confidence intervals and pairwise tests (Modify)

> | **Per-arm %Resolved** | Point estimate with a **95% binomial confidence interval**, as SWE-bench Pro reports. |

### `06-scoring-and-statistics.md` → §Decisions (Modify)

> - *Resolution follows the SWE-bench Pro convention.* **All `failToPass` pass and all `passToPass` hold.** Reusing the established definition keeps A0's numbers comparable to the published leaderboard.
> - *Deltas are paired and tested with McNemar.* **Same instances, both arms.** Pairing cancels shared difficulty and contamination, which is what makes the within-suite comparison hold despite the `public` tier of the SWE-bench Pro suite.

---

## Type changes

```json
{
  "$comment": "Fragment for 2026-05-27-add_swe_bench_pro_suite. Folds into apps/benchmark canonical-types.schema.json on merge. Shows the modified Suite $def; the changed members are the kind and oracleConvention enums, each gaining one value.",
  "$defs": {
    "Suite": {
      "type": "object",
      "required": ["slug", "kind", "oracleConvention"],
      "additionalProperties": false,
      "properties": {
        "slug": { "$ref": "#/$defs/Slug" },
        "kind": { "type": "string", "enum": ["issue-fixing", "greenfield", "local-fixture"] },
        "oracleConvention": { "type": "string", "enum": ["swe-bench-pro", "greenfield-hidden-tests", "local"] }
      }
    }
  }
}
```

`TaskInstance` is unchanged: issue-fixing instances set `dockerImage` to a `jefzda/sweap-images` tag (a string, already permitted), `goldPatch` to the reference patch, and `contaminationTier` to `public` (already an enum member).

---

## Implementation notes

Pointers for the implementing agent. The `issue-fixing` / `swe-bench-pro` vocabulary was removed from both the schema and the code by [`2026-05-27-trim_deferred_swe_bench_pro_code.md`](merged/2026-05-27-trim_deferred_swe_bench_pro_code.md), so this work re-introduces the strings in both places.

```
1. Schema + domain: re-add the enum members to .specs/benchmark/specs/canonical-types.schema.json
   (Suite.kind gains "issue-fixing"; Suite.oracleConvention gains "swe-bench-pro") and to the
   mirror constants in benchmark/harness/domain.py (SUITE_KINDS, ORACLE_CONVENTIONS).
2. Suite data: add benchmark/suites/swe-bench-pro-public/instances.jsonl with TaskInstance
   records sourced from the SWE-bench Pro public set (problemStatement, repo/baseCommit,
   goldPatch, failToPass/passToPass, dockerImage = jefzda/sweap-images tag,
   contaminationTier = "public"). Validate against canonical-types.schema.json.
3. container ScoringBackend: implement the swe-bench-pro oracle path — a fresh scoring
   container reusing the SWE-bench Pro evaluation flow. This is the container backend
   deferred from the minimal build (depends on Docker + pullable images).
4. container RunBackend: provision the run container from the instance's jefzda/sweap-images
   tag, with no hidden test content crossing into it (the integrity rule).
5. Tests: re-add swe-bench-pro-public / issue-fixing / swe-bench-pro fixtures to
   benchmark/tests/test_domain.py (removed by the trim change) and add coverage for the
   swe-bench-pro oracle convention in the scorer.
```

This change depends on Docker and the prebuilt SWE-bench Pro images (a peer dependency already documented for the `container` backend); it does not affect the Docker-free `local` pipeline or the greenfield suite.

---

## Merge plan

1. Apply each `Proposed changes` block to its canonical page; bump that page's `**Date:**` to the merge date. (Modify §Problem, add Goal 6, modify §System shape / detail-pages table / §Scope summary, add the assumption and decision in `00`; modify the ID-scheme table, Suite entity, `goldPatch`, and `testTags` in `01`; modify §A0 in `02`; add §Suite: `swe-bench-pro-public` and modify the intro, `local-fixture` sentence, layout, assumptions, and decisions in `03`; modify §Bucket 1 and §Bucket 3 in `04`; modify §Backends, §Run container, §Scoring isolation in `05`; modify §The test oracle, §Confidence intervals, and §Decisions in `06`.)
2. Fold the `Type changes` `$def` into `canonical-types.schema.json` — add `issue-fixing` to `Suite.kind` and `swe-bench-pro` to `Suite.oracleConvention`.
3. No new canonical page; nothing to index beyond existing entries.
4. Flip this file's `**Status:**` to `Merged`, add `**Merged:** YYYY-MM-DD`, and move it to `.specs/benchmark/specs/changes/merged/`.
5. Update `.specs/README.md`: remove this file from the pending change-specs list, add it under the merged area; restore the SWE-bench Pro mention in `.specs/benchmark/README.md` if it was trimmed.

---

## Assumptions and open questions

**Assumptions**

- SWE-bench Pro's public instances and `jefzda/sweap-images` tags remain pullable for the lifetime of the benchmark, and its `fail-to-pass` / `pass-to-pass` test data is reusable under its licence.
- The `container` backend (deferred from the minimal build) is available by the time this suite lands; without it there is no path to run the `swe-bench-pro` oracle, since the `local` backend cannot reproduce the SWE-bench Pro images' system dependencies.

**Decisions**

- *Reuse, do not re-derive.* **Take SWE-bench Pro's instances, images, and oracle as-is.** Re-deriving the test split or rebuilding the images would forfeit the comparability that is the suite's entire purpose and risk diverging from the published difficulty scale.
- *`container`-only.* **The suite runs on the `container` backend.** Its Docker images carry system dependencies the `local` temp-checkout path cannot satisfy; the suite is therefore unavailable in the Docker-free pipeline by design.
- *Added back as a change, not restored silently.* **A dated change spec rather than an edit to the canonical body.** The minimal canonical describes a benchmark without this suite; reintroducing it follows the normal `Proposed → Merged` lifecycle so the deferral and its reversal are recorded history.

**Open questions**

- *Instance subset.* The full SWE-bench Pro public set is 11 repositories; does the first campaign run all of them, or a power-analysis-sized subset paired across arms ([06-scoring-and-statistics.md](../06-scoring-and-statistics.md) → suite-size question)?
- *Change-spec seeding for workflow arms.* On issue-fixing the workflow arms seed a change spec from the issue text rather than patching directly ([02-arms.md](../02-arms.md)). Does the existing `spec-creator` change-spec path accept a raw issue as input cleanly, or does it need an adapter step?
- *Contamination reporting.* The `public` tier means base models may have seen these repos. Beyond the paired-delta defence, should the absolute A0 `%Resolved` carry an explicit contamination caveat wherever it is reported next to the published number?
