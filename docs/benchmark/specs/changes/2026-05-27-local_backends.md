# Change: Pluggable run/scoring backends and a local-fixture suite

**Status:** Accepted · **Date:** 2026-05-27 · **Owner:** Ant Stanley · **Target:** apps/benchmark

Generalise the run side and scoring side of the harness into pluggable **backends** — a `RunBackend` and a `ScoringBackend`, each with a `container` implementation (the existing Docker/SWE-bench-Pro path, still the default) and a `local` implementation that needs no Docker (run in a temp working directory, score by applying the candidate patch to a temp checkout and running the hidden tests as a local subprocess). Add a `local-fixture` suite — a tiny self-contained instance with a gold patch — so the run → score → aggregate pipeline can be built and verified deterministically without Docker, a network, or an LLM-agent budget. The production architecture is unchanged: `container` stays the default, the canonical pages still describe it, and the run/scoring integrity rule holds in both backends.

---

## Motivation

The canonical architecture fixes Docker as the execution substrate — "Docker per trial", a run container and a separate scoring container ([`05-harness-architecture.md`](../05-harness-architecture.md)). That is right for production but makes the harness unbuildable and unverifiable anywhere Docker, the SWE-bench Pro images, or an agent/API budget are absent — including ordinary development machines and the first milestone of the build plan. With no Docker-free path, even the pure-logic components (the driver lifecycle, the statistics, the score-report flow) cannot be exercised end to end until the entire container stack is standing.

A backend seam fixes this without weakening the production design. The driver, the scorer's resolution rule, the statistics, and the report all become backend-agnostic; `container` and `local` are two implementations of the same contracts. A `local-fixture` suite with a known gold patch lets the whole pipeline run deterministically in-process, so the harness has a fast, hermetic test path and the build plan has a Docker-free first milestone. The integrity rule that keeps the workflow's gates from seeing the hidden tests is preserved by construction in both backends.

---

## Affected spec pages

| Canonical page | Nature of change |
|---|---|
| [`05-harness-architecture.md`](../05-harness-architecture.md) | Add a **Backends** section (`RunBackend` / `ScoringBackend`, `container` + `local`); generalise §Run container and §Scoring isolation to be backend-neutral while keeping the integrity rule |
| [`06-scoring-and-statistics.md`](../06-scoring-and-statistics.md) | §The test oracle: add the `local` oracle convention alongside `swe-bench-pro` and `greenfield-hidden-tests` |
| [`03-task-suites.md`](../03-task-suites.md) | Add §Suite: `local-fixture` — a self-contained, Docker-free verification instance |
| [`01-domain-model.md`](../01-domain-model.md) | Extend `Suite.kind` and `Suite.oracleConvention` enums; add `backend` and `solver` to `Campaign` |
| [`canonical-types.schema.json`](../canonical-types.schema.json) | Enum additions on `Suite`; new `backend` / `solver` properties on `Campaign` |

No new canonical page is added; the change extends existing pages.

---

## Proposed changes

Each block is the prose as it should read in the canonical page after merge.

### `05-harness-architecture.md` → new section **Backends** (Add)

> ## Backends
>
> The run side and the scoring side are each a **pluggable backend** behind a fixed interface, so the driver, the scorer's resolution rule, and the statistics are agnostic to how a trial is actually run and scored.
>
> - **`RunBackend`** — provisions an environment, runs an arm (or a fixture solver) against a `TaskInstance`, and returns a `candidatePatch` plus an `ArtifactBundle`. Implementations: `container` (provision from the instance's `dockerImage`, install the arm's plugins, run in the container — the production default) and `local` (run in an isolated temp working directory / subprocess, no Docker).
> - **`ScoringBackend`** — applies a `candidatePatch` to a clean copy of the instance base, injects the hidden tests, runs them, and returns a `ScoreReport`. Implementations: `container` (a fresh scoring container, reusing the SWE-bench Pro evaluation flow) and `local` (a fresh temp checkout, hidden tests run as a local subprocess).
>
> A `Campaign` selects the backend (`backend: container | local`, default `container`). The `local` backend requires only Python, `uv`, and the repo under test; the `container` backend requires Docker and the prebuilt images. The two backends honour the **same** integrity rule (below): the run side never sees the hidden tests, whichever backend runs.

### `05-harness-architecture.md` → §Run container (Modify)

> The `container` `RunBackend` provisions a run container per trial from the instance's `dockerImage` with `jj` and `git` available, installs the arm's plugin set, runs the arm to completion, and extracts the `candidatePatch` (the diff of the working state against `baseCommit`) and the `ArtifactBundle`. The `local` `RunBackend` does the same in an isolated temp working directory checked out at `baseCommit` — no container — for arms whose execution does not require one and for the fixture solver. Neither backend's run environment carries any hidden test content.

### `05-harness-architecture.md` → §Scoring isolation — the integrity rule (Modify)

> The rule holds across both backends: the workflow's gates operate only on each task's definition of done and never see the hidden `failToPass` / `passToPass` suite, which is introduced only on the scoring side.
>
> - The `container` `ScoringBackend` injects the hidden tests into a fresh scoring container, separate from the run container.
> - The `local` `ScoringBackend` injects them into a fresh temp checkout in a directory distinct from the run working directory, run as a separate process.
>
> In both cases the run side and the scoring side are different filesystems/processes, and the hidden suite exists only on the scoring side.

### `06-scoring-and-statistics.md` → §The test oracle (Modify)

> The oracle runs under one of three conventions, selected by the suite and the active `ScoringBackend`:
>
> - **`swe-bench-pro`** — reuse SWE-bench Pro's evaluation harness in a scoring container (the `container` backend, issue-fixing suite).
> - **`greenfield-hidden-tests`** — run the instance's withheld suite in a scoring container built with the hidden tests included (the `container` backend, greenfield suite).
> - **`local`** — apply the candidate patch to a fresh temp checkout and run the hidden tests as a local subprocess (the `local` backend). Resolution is the same in every case: every `failToPass` test passes and every `passToPass` test still holds.

### `03-task-suites.md` → new section **Suite: `local-fixture`** (Add)

> ## Suite: `local-fixture`
>
> **Kind:** `local-fixture`. **Oracle convention:** `local`.
>
> A self-contained verification instance that needs no Docker and no network: a small repository at a fixed commit, a hidden `pytest` suite, and a known `goldPatch` that makes the hidden tests pass. It exists to exercise the run → score → aggregate pipeline deterministically — running the fixture solver (which emits the `goldPatch`) yields `resolved: true`, and a no-op patch yields `resolved: false` — so the driver, the scorer, and the statistics are verifiable end to end without the production stack.
>
> | `TaskInstance` field | `local-fixture` source |
> |---|---|
> | `problemStatement` | a short prose description of the fixture task |
> | `repo` / `baseCommit` | the bundled fixture repo at its fixed commit |
> | `goldPatch` | the patch that makes the hidden suite pass |
> | `failToPass` | the bundled hidden `pytest` selectors |
> | `passToPass` | any smoke tests that must keep passing |
> | `dockerImage` | `null` — the `local` backend uses no image |
> | `contaminationTier` | `authored-private` |
>
> The suite is not part of the ablation result; it is harness infrastructure. Real arms (A0–A4) and the comparative metrics still run on the `swe-bench-pro` and `greenfield-features` suites under the `container` backend.

### `01-domain-model.md` → §Entities → Suite (Modify)

> - `kind` — `issue-fixing`, `greenfield`, or `local-fixture`.
> - `oracleConvention` — `swe-bench-pro`, `greenfield-hidden-tests`, or `local`.

### `01-domain-model.md` → §Entities → Campaign (Modify)

> Add two fields:
> - `backend` — `container` (default) or `local`; the run/scoring backend the campaign uses.
> - `solver` — `agent` (default) or `fixture`; `fixture` runs the scripted solver that emits the instance `goldPatch`, for deterministic pipeline verification on the `local-fixture` suite without an LLM agent. Real arms use `agent`.

---

## Type changes

```json
{
  "$comment": "Fragment for 2026-05-27-local_backends. Folds into apps/benchmark canonical-types.schema.json on merge. Shows the modified Suite and Campaign $defs; changed members are the kind/oracleConvention enums and the new backend/solver properties.",
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
    },
    "Campaign": {
      "type": "object",
      "required": ["id", "createdAt", "model", "arms", "suites", "trialsPerInstance"],
      "additionalProperties": false,
      "properties": {
        "id": { "$ref": "#/$defs/RecordId" },
        "createdAt": { "$ref": "#/$defs/Timestamp" },
        "model": { "type": "string", "minLength": 1 },
        "arms": { "type": "array", "items": { "$ref": "#/$defs/ArmSlug" }, "minItems": 1 },
        "suites": { "type": "array", "items": { "$ref": "#/$defs/Slug" }, "minItems": 1 },
        "trialsPerInstance": { "type": "integer", "minimum": 1 },
        "backend": { "type": "string", "enum": ["container", "local"], "default": "container" },
        "solver": { "type": "string", "enum": ["agent", "fixture"], "default": "agent" }
      }
    }
  }
}
```

The `local-fixture` suite sets `dockerImage: null`, already permitted by the existing `TaskInstance` schema (`dockerImage` is `["string", "null"]`).

---

## Implementation notes

Pointers for the implementing agent; the code does not exist yet, so these name planned modules in [`05-harness-architecture.md`](../05-harness-architecture.md)'s layout.

```
1. Define the backend interfaces in benchmark/harness/backends/ — RunBackend and ScoringBackend
   protocols, each with the method the driver calls (run → ArtifactBundle + candidatePatch;
   score → ScoreReport).
2. container implementations wrap the planned plan tasks 04 (scoring oracle) and 05 (run
   container); local implementations are new (temp checkout + subprocess), no Docker.
3. The local ScoringBackend reuses the resolution rule from task 04 (all failToPass pass and
   passToPass hold) over a local pytest run; keep the rule in one place, backend-agnostic.
4. Add the fixture instance under benchmark/suites/local-fixture/ (bundled repo + hidden tests
   + goldPatch) and the fixture solver in the local RunBackend.
5. The driver (plan task 07) selects the backend from Campaign.backend; it is otherwise
   unchanged. The statistics (task 09) are already backend-agnostic.
```

This change unblocks a Docker-free first milestone: spec-planner re-plans M1 to build the package skeleton, the domain types, the backend interfaces, the local backends, and the local-fixture suite, then run the driver and statistics over the fixture — all locally verifiable — deferring the `container` backend and the real suites to a later infrastructure milestone.

---

## Merge plan

1. Apply each `Proposed changes` block to its canonical page; bump that page's `**Date:**` to the merge date. (Add the **Backends** section to `05`; modify §Run container and §Scoring isolation in `05`; modify §The test oracle in `06`; add §Suite: `local-fixture` to `03`; modify the Suite and Campaign entities in `01`.)
2. Fold the `Type changes` `$defs` into `canonical-types.schema.json` — update the `Suite.kind` and `Suite.oracleConvention` enums and add `backend` / `solver` to `Campaign`.
3. No new canonical page; nothing to index beyond existing entries.
4. Flip this file's `**Status:**` to `Merged`, add `**Merged:** YYYY-MM-DD`, and move it to `docs/benchmark/specs/changes/merged/`.
5. Update `docs/README.md`: remove this file from the pending change-specs list, leave the merged-area pointer.

---

## Assumptions and open questions

**Assumptions**

- The `local` `ScoringBackend` can reproduce the resolution verdict the `container` backend would give for the same patch on suites whose tests run under plain `pytest`; suites needing the production image's system dependencies remain `container`-only.
- The fixture repo and its hidden suite can be kept small enough to run in well under a second, so the local pipeline test stays hermetic and fast.

**Decisions**

- *A seam, not a fork.* **`RunBackend` / `ScoringBackend` interfaces with `container` and `local` implementations.** A backend abstraction keeps the driver, scorer rule, and statistics single-sourced; forking a separate local harness would drift from the production path it is meant to de-risk.
- *`container` stays the default.* **Production runs on Docker; `local` is opt-in via `Campaign.backend`.** The canonical architecture is unchanged for real campaigns; the local backend is an additional, first-class path for development, CI, and the fixture suite.
- *Fixture solver is a backend mode, not a sixth arm.* **`Campaign.solver: fixture` on the `local` backend.** The arm set stays closed at five (A0–A4); the scripted solver is a property of how the local run backend produces a patch, used only for pipeline verification, never reported as an ablation arm.
- *Integrity rule preserved in both backends.* **Run dir/container and scoring dir/container are always separate, hidden tests on the scoring side only.** The whole benchmark rests on the gates not seeing the oracle; the local backend must not weaken it for convenience.

**Open questions**

- *Local–container verdict parity.* How is it confirmed that the `local` and `container` backends agree on resolution for the same patch — a shared conformance test over a common instance, or accepted as backend-specific? Blocks treating `local` results as comparable to `container` results beyond pipeline verification.
- *Fixture suite breadth.* Does a single fixture instance suffice for M1, or are a few (one resolvable, one not, one with a regression) needed to exercise the scorer's branches? Affects the re-plan's local-fixture task scope.
