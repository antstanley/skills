# 03 — Task Suites

This page defines the suites of task instances the arms run against. Each suite is a `Suite` entity holding `TaskInstance`s ([01-domain-model.md](01-domain-model.md)). The ablation result runs on a single suite — `greenfield-features`, which exercises building a feature from a specification, the workflow's home ground. A second suite, `local-fixture`, is harness infrastructure: a Docker-free instance that verifies the run → score → aggregate pipeline end to end.

---

## Responsibilities

A suite supplies, per instance: the starting repo state, the input the arms receive, the hidden oracle that scores a candidate patch, and the metadata that controls fairness (`contaminationTier`, `headlessVerifiable`). A suite does **not** define how a candidate is produced (that is an Arm, [02-arms.md](02-arms.md)) or how a result is aggregated (that is [06-scoring-and-statistics.md](06-scoring-and-statistics.md)).

The `greenfield-features` suite is the ablation suite, in scope from the first campaign; `local-fixture` exists only to verify the pipeline.

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

This suite is where the full pipeline's strengths — decomposition into a task graph, parallel waves, and the two gates — have room to pay off, and where issue-fixing tasks cannot reach. Two design constraints make it trustworthy:

1. **Private and novel.** Tasks are authored fresh and kept out of public channels, so `authored-private` means absent from training data at campaign time. This is the contamination defence the `public` suite cannot offer.
2. **Multi-component by construction.** Each spec names several components with dependencies between them, so the task graph has width (for the parallel arms) and depth (for the reviewability ordering). Single-file tasks would not exercise the workflow.

---

## Suite: `local-fixture`

**Kind:** `local-fixture`. **Oracle convention:** `local`.

A self-contained verification instance that needs no Docker and no network: a small repository at a fixed commit, a hidden `pytest` suite, and a known `goldPatch` that makes the hidden tests pass. It exists to exercise the run → score → aggregate pipeline deterministically — running the fixture solver (which emits the `goldPatch`) yields `resolved: true`, and a no-op patch yields `resolved: false` — so the driver, the scorer, and the statistics are verifiable end to end without the production stack.

| `TaskInstance` field | `local-fixture` source |
|---|---|
| `problemStatement` | a short prose description of the fixture task |
| `repo` / `baseCommit` | the bundled fixture repo at its fixed commit |
| `goldPatch` | the patch that makes the hidden suite pass |
| `failToPass` | the bundled hidden `pytest` selectors |
| `passToPass` | any smoke tests that must keep passing |
| `dockerImage` | `null` — the `local` backend uses no image |
| `contaminationTier` | `authored-private` |

The suite is not part of the ablation result; it is harness infrastructure. Real arms (A0–A4) and the comparative metrics still run on the `greenfield-features` suite under the `container` backend.

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
    greenfield-features/
      instances.jsonl        # TaskInstance records, validated against canonical-types.schema.json
      <slug>/                # per-instance skeleton repo + withheld test suite
    local-fixture/           # bundled fixture repo + hidden tests + goldPatch (Docker-free)
```

Instance records conform to the `TaskInstance` `$def` in [`canonical-types.schema.json`](canonical-types.schema.json). The withheld test suites live beside the instances but are injected only into the *scoring* container, never the run container ([05-harness-architecture.md](05-harness-architecture.md)).

---

## Assumptions and open questions

**Assumptions**

- Greenfield tasks can be authored with hidden test suites strong enough that passing them is good evidence of a correct implementation, not just of hitting a thin happy path.

**Decisions**

- *Greenfield is the ablation suite.* **Build-from-spec, newly authored.** Issue-fixing benchmarks leave the spec-authoring and planning stages idle; greenfield exercises them, which is what the benchmark exists to measure.
- *Greenfield is `authored-private`.* **Newly authored, kept private.** It is the only contamination defence available; reusing public greenfield tasks would reintroduce the exposure the suite exists to avoid.
- *Within-suite paired deltas are the primary readout.* **Arms compared on shared instances.** Pairing cancels shared task difficulty and any training-data exposure, since every arm faces the same instances.

**Open questions**

- *Suite sizes.* How many instances per suite are needed for the paired confidence intervals in [06-scoring-and-statistics.md](06-scoring-and-statistics.md) to separate the arms? Pending a power analysis.
- *Greenfield authoring cost.* Authoring novel multi-component tasks with strong hidden suites is expensive; how many can realistically be produced for the first campaign, and does that number give usable intervals?
