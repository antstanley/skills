# 03 — Task Suites

This page defines the two suites of task instances the arms run against. Each suite is a `Suite` entity holding `TaskInstance`s ([01-domain-model.md](01-domain-model.md)). The two suites are deliberately different in shape: one exercises issue-fixing on existing code, the other exercises building a feature from a specification — the workflow's home ground.

---

## Responsibilities

A suite supplies, per instance: the starting repo state, the input the arms receive, the hidden oracle that scores a candidate patch, and the metadata that controls fairness (`contaminationTier`, `headlessVerifiable`). A suite does **not** define how a candidate is produced (that is an Arm, [02-arms.md](02-arms.md)) or how a result is aggregated (that is [06-scoring-and-statistics.md](06-scoring-and-statistics.md)).

Both suites are in scope from the first campaign and are built in parallel.

---

## Suite: `swe-bench-pro-public`

**Kind:** `issue-fixing`. **Oracle convention:** `swe-bench-pro` (reused).

Sourced from the [SWE-bench Pro](https://scaleapi.github.io/SWE-bench_Pro-os/) public set — 11 open-access repositories of long-horizon, multi-file issues. Each instance reuses SWE-bench Pro's own fields and Docker images rather than re-deriving them:

| TaskInstance field | Source in SWE-bench Pro |
|---|---|
| `problemStatement` | the issue description |
| `repo` / `baseCommit` | the instance's repo and base commit |
| `goldPatch` | the reference solution patch |
| `failToPass` / `passToPass` | the instance's test selectors |
| `dockerImage` | the prebuilt `jefzda/sweap-images` tag |
| `contaminationTier` | `public` |

This suite's purpose is **comparability**: A0 runs the same tasks and the same hidden oracle as SWE-bench Pro, so its `%Resolved` sits on the same scale as the published results (top score ≈ 43.7%) — a calibration of difficulty, not a like-for-like leaderboard entry, since the published numbers use SWE-bench Pro's own reference agent rather than plain Claude Code. For the workflow arms, the issue text seeds a change spec rather than being patched directly.

A caveat carries through to the metrics: the public set is `public` tier, so a base model may have seen these repositories. The comparison that matters here is *across arms on the same instances* (a within-suite, paired delta), which is insensitive to shared contamination because every arm faces the same exposure.

---

## Suite: `greenfield-features`

**Kind:** `greenfield`. **Oracle convention:** `greenfield-hidden-tests`.

Newly authored, Commit0-style ([arXiv 2412.01769](https://arxiv.org/pdf/2412.01769)) build-from-spec tasks. Each instance gives the arms a prose specification of a multi-component feature or small library and starts from an empty or skeleton repo; resolution is decided by a **withheld** test suite the arms never see.

| TaskInstance field | Greenfield source |
|---|---|
| `problemStatement` | the prose specification seed |
| `repo` / `baseCommit` | a skeleton repo at a fixed commit |
| `goldPatch` | `null` — there is no single reference solution |
| `failToPass` | the hidden acceptance test suite |
| `passToPass` | skeleton smoke tests that must keep passing |
| `dockerImage` | an image built for the instance with the hidden tests baked in but withheld from the run container |
| `contaminationTier` | `authored-private` |

This suite is where the full pipeline's strengths — decomposition into a task graph, parallel waves, and the two gates — have room to pay off, and where the issue-fixing suite cannot reach. Two design constraints make it trustworthy:

1. **Private and novel.** Tasks are authored fresh and kept out of public channels, so `authored-private` means absent from training data at campaign time. This is the contamination defence the `public` suite cannot offer.
2. **Multi-component by construction.** Each spec names several components with dependencies between them, so the task graph has width (for the parallel arms) and depth (for the reviewability ordering). Single-file tasks would not exercise the workflow.

---

## Instance selection and fairness

| Concern | Handling |
|---|---|
| **Headless verifiability** | `spec-builder` pauses for manual sign-off on visually-reviewable tasks. Instances are selected `headlessVerifiable: true` so the oracle runs without a human, unless a scripted oracle stands in (an Open question in [00-overview.md](00-overview.md)). |
| **Comparable difficulty** | The greenfield suite targets a difficulty band where the baseline does not trivially saturate, mirroring the SkillsBench target of SOTA below 50% (arXiv 2602.12670) so there is headroom for the workflow to show value. |
| **Suite size** | Large enough that paired confidence intervals are informative ([06-scoring-and-statistics.md](06-scoring-and-statistics.md)); the concrete counts are an Open question pending a power analysis. |

---

## Implementation layout

```
benchmark/
  suites/
    swe-bench-pro-public/
      instances.jsonl        # TaskInstance records, validated against canonical-types.schema.json
      (Docker images referenced by tag; not vendored)
    greenfield-features/
      instances.jsonl        # TaskInstance records
      <slug>/                # per-instance skeleton repo + withheld test suite
```

Instance records conform to the `TaskInstance` `$def` in [`canonical-types.schema.json`](canonical-types.schema.json). The withheld test suites live beside the instances but are injected only into the *scoring* container, never the run container ([05-harness-architecture.md](05-harness-architecture.md)).

---

## Assumptions and open questions

**Assumptions**

- SWE-bench Pro's public instances and `jefzda/sweap-images` tags remain pullable for the lifetime of the benchmark.
- Greenfield tasks can be authored with hidden test suites strong enough that passing them is good evidence of a correct implementation, not just of hitting a thin happy path.

**Decisions**

- *Two suites of different shape.* **Issue-fixing plus greenfield.** Issue-fixing buys comparability to a published baseline; greenfield exercises the spec-authoring and planning stages that issue-fixing leaves idle. One suite alone would under-test the workflow.
- *Greenfield is `authored-private`.* **Newly authored, kept private.** It is the only contamination defence available; reusing public greenfield tasks would reintroduce the exposure the suite exists to avoid.
- *Within-suite paired deltas are the primary readout.* **Arms compared on shared instances.** This makes the `public`-tier contamination on the SWE-bench Pro suite tolerable, since every arm shares the same exposure.

**Open questions**

- *Suite sizes.* How many instances per suite are needed for the paired confidence intervals in [06-scoring-and-statistics.md](06-scoring-and-statistics.md) to separate the arms? Pending a power analysis.
- *Greenfield authoring cost.* Authoring novel multi-component tasks with strong hidden suites is expensive; how many can realistically be produced for the first campaign, and does that number give usable intervals?
