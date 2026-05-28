# Change: Add live in-container runtime verification

**Status:** Accepted · **Date:** 2026-05-28 · **Owner:** Ant Stanley · **Target:** apps/benchmark

> Planned for build at [`docs/plans/2026-05-28-add_live_container_verification/`](../../../plans/2026-05-28-add_live_container_verification/plan.md).

Add an opt-in **live runtime verification** path that exercises the `container` backends end to end against a real Docker image — provisioning a run container, running a bounded real arm, capturing the patch + bundle, then scoring in a *separate* clean container with the hidden tests injected only there — and that drives the live `claude -p` gate probe to confirm its verdict mapping on an actual model call. Today the `container` backend, the two-container scoring split, and the live gate probe are covered only by unit tests with injected fakes and by the captured `benchmark/tests/_a*_live_evidence/` fixtures; nothing in the repo *executes* the Docker path or a real `claude -p` call and asserts the result. The benchmark's `Status: Built` therefore rests on code review plus replayed evidence, not on a runtime check. This change closes that gap with a self-contained, default-skipped verification suite — no change to the domain model, the arms, the metrics, or the scoring rule, only the prose that commits to the check and the harness that performs it.

---

## Motivation

The R2 spec-vs-code conformance review (2026-05-28) confirmed the implementation matches the spec across the domain model, arms, suites, statistics, and scoring core. Its one standing caveat was scope, not correctness: the `container` `RunBackend` / `ScoringBackend`, the integrity rule (run container never sees the hidden suite), the A4 naive-merge path, the A1/A2 gate-event emission, and the live `claude -p` gate probe (`benchmark/harness/scoring/probes/live.py`) were all verified *statically* — read, unit-tested with injected reviewers and fakes, and cross-checked against replayed `_a*_live_evidence/` bundles — but never executed against Docker or a real model in a test that asserts the outcome.

Two specific behaviors are unverified at runtime:

1. **The two-container split on real Docker.** That the `container` `RunBackend` provisions from the instance `dockerImage`, that the run image genuinely carries no hidden test content, that the `container` `ScoringBackend` stands up a *fresh* image with the hidden suite overlaid, and that the shared resolution rule produces the same `resolved` verdict the `local` backend does on the same patch — these are the integrity backbone of the whole benchmark ([05-harness-architecture.md](../05-harness-architecture.md) → §Scoring isolation), and they are exactly what a fake-backed unit test cannot prove.
2. **The live `claude -p` gate-probe behavior.** `run_gate_probe` with the real `cli_review_gate` reviewer (not an injected callable) actually invoking `claude -p`, emitting a parseable `VERDICT:` line, and mapping a known-bad diff to `caughtBy = "semi-formal-review"`. The unit tests drive the mapping with a stub; the real call path (CLI present, JSON envelope shape, verdict line) is only documented, never run.

A campaign is expensive and Docker-bound, so this verification must be **opt-in and bounded**, mirroring the existing `BENCHMARK_RUN_GATE_PROBE_LIVE` opt-in: skipped by default (CI, `check.sh`), runnable on demand by an operator who has Docker and accepts the cost. The output is a pass/fail self-test plus refreshed evidence, not a new metric.

---

## Affected spec pages

| Canonical page | Nature of change |
|---|---|
| [`00-overview.md`](../00-overview.md) | §Scope summary: note that the built state is backed by an opt-in live runtime verification, and that automated live verification is the remaining gap closed here |
| [`05-harness-architecture.md`](../05-harness-architecture.md) | Add a **§Runtime verification** subsection describing the opt-in end-to-end container self-test and its env gate; add a row to §Concurrency and reproducibility; add the verification entrypoint to §Implementation layout; resolve the *Greenfield image build* open question now that the two-image build is exercised live |
| [`06-scoring-and-statistics.md`](../06-scoring-and-statistics.md) | §Gate-efficacy probes: note the live `claude -p` probe is part of the runtime-verification suite and that the live container scoring check reuses the same opt-in discipline |

No new canonical page is added; the schema (`canonical-types.schema.json`) is unchanged — this change introduces no entity, field, or enum.

---

## Proposed changes

Each block is the prose as it should read in the canonical page after merge.

### `00-overview.md` → §Scope summary (Modify the `Implementation` row)

> | Implementation | Built and tested; live runtime verification opt-in | The whole pipeline ships under `benchmark/`; live arms verified end to end on the greenfield seed (`benchmark/tests/_a*_live_evidence/`). An opt-in self-test (`BENCHMARK_RUN_CONTAINER_LIVE=1`) executes the `container` backends and the live `claude -p` gate probe against real Docker on demand ([05-harness-architecture.md](05-harness-architecture.md) → §Runtime verification). See [`benchmark/README.md`](../../../benchmark/README.md) for how to run a campaign. |

### `05-harness-architecture.md` → new subsection **§Runtime verification** (Add)

Insert after §Scoring isolation — the integrity rule, before §Concurrency and reproducibility.

> ## Runtime verification
>
> The integrity rule and the two-container split are enforced in code and covered by unit tests with injected backends; a separate **opt-in live self-test** proves they hold against real Docker and a real model, so `Status: Built` is runtime-checkable rather than review-only. It is gated behind `BENCHMARK_RUN_CONTAINER_LIVE=1` (mirroring the gate probe's `BENCHMARK_RUN_GATE_PROBE_LIVE`) and is skipped by default — CI and `check.sh` never pay its Docker or token cost.
>
> When enabled, the self-test runs one greenfield instance end to end on the `container` backends and asserts, with known answers:
>
> - **Provisioning + capture.** The `container` `RunBackend` builds/loads the instance run image, runs a bounded real arm (A0 by default; A1/A2/A3 when a budget is supplied), and returns a `candidatePatch` plus an `ArtifactBundle`.
> - **The integrity rule, observed not assumed.** The run image carries no file from the instance's `hidden/` tree and no `failToPass` / `passToPass` selector content — checked by inspecting the provisioned image, not by trusting the build.
> - **Two-container scoring.** The `container` `ScoringBackend` stands up a *fresh* scoring image (hidden suite overlaid) distinct from the run container and produces a `ScoreReport` whose `resolved` verdict matches the `local` backend's verdict on the same patch — the shared resolution rule, proven identical across backends.
> - **Gate emission.** On A2 the captured certificates yield ≥ 1 `GateEvent` and on A3 zero, threaded onto the `TrialResult` exactly as the metrics consume them.
> - **The live `claude -p` gate probe.** `run_gate_probe` with the real `cli_review_gate` reviewer issues one bounded `claude -p` review of a known-bad diff and maps the returned verdict to `caughtBy` ([06-scoring-and-statistics.md](06-scoring-and-statistics.md) → §Gate-efficacy probes).
>
> A green run refreshes the `benchmark/tests/_a*_live_evidence/` bundles; the captured evidence remains the default, zero-cost regression surface for everything downstream.

### `05-harness-architecture.md` → §Concurrency and reproducibility (Add a row)

> | **Live verification** | The opt-in container self-test (`BENCHMARK_RUN_CONTAINER_LIVE=1`) runs serially against real Docker, bounded by a per-call budget cap; default-skipped so routine runs stay Docker-free and deterministic. |

### `05-harness-architecture.md` → §Implementation layout (Modify)

> ```
> benchmark/
>   harness/
>     ...
>     run_local_demo.py  # Docker-free pipeline demo entrypoint
>     run_container_check.py  # opt-in live container + claude -p self-test (BENCHMARK_RUN_CONTAINER_LIVE)
>   suites/              # TaskInstance records + greenfield skeletons + local-fixture + benchflow-probe (see 03)
> ```

### `05-harness-architecture.md` → §Open questions (Modify — resolve *Greenfield image build*)

> - *Greenfield image build.* **Resolved.** The two-image build (`benchmark/suites/greenfield_images.py`) builds a run image that copies only `base/` and a scoring image that overlays `hidden/`; the live runtime verification (§Runtime verification) confirms at runtime that the run image carries no hidden-test content. The build-arg-vs-two-Dockerfiles question is settled in favour of two Dockerfiles from a shared base.

### `06-scoring-and-statistics.md` → §Gate-efficacy probes (Modify the live-probe paragraph's lead)

> **Live-probe verdict mapping.** The opt-in live gate probe (`benchmark/harness/scoring/probes/live.py`, gated by `BENCHMARK_RUN_GATE_PROBE_LIVE=1`, and also driven as part of the live runtime-verification self-test, [05-harness-architecture.md](05-harness-architecture.md) → §Runtime verification) injects one classified mutation, runs the `semi-formal-review` gate as a bounded `claude -p` call, and maps the gate's verdict line …

*(the remainder of the paragraph is unchanged)*

---

## Type changes

None. This change adds no entity, field, or enum; `canonical-types.schema.json` and `benchmark/harness/domain.py` are untouched. The verification reuses the existing `Campaign` / `Trial` / `ArtifactBundle` / `ScoreReport` / `GateEvent` / `InjectedDefect` records and the existing `RunBackend` / `ScoringBackend` protocols.

---

## Implementation notes

Pointers for the implementing agent. The verification is test/harness infrastructure layered on already-shipped code; it adds an entrypoint and a default-skipped test module, nothing in the domain or metrics layer.

```
1. Entrypoint: add benchmark/harness/run_container_check.py — an opt-in self-test runner,
   gated on os.environ.get("BENCHMARK_RUN_CONTAINER_LIVE") == "1". Skip cleanly (and loudly)
   when unset, when Docker is absent (reuse benchmark.suites.greenfield_images.docker_available),
   or when the claude CLI is missing.
2. Container round-trip: drive ContainerRunBackend.run(instance, A0_ARM) then
   ContainerScoringBackend.score(instance, patch) on greenfield__text_toolkit__0001 (it carries a
   reference/solution.patch, so a known-good and a no-op patch give resolved True / False).
   Assert the ScoreReport.resolved verdict equals the local backend's verdict on the same patch
   (single-source the resolution rule via benchmark.harness.scoring.resolution).
3. Integrity assertion: inspect the provisioned RUN image (e.g. a docker run that lists the
   workspace) and assert no path under hidden/ and none of instance.failToPass / passToPass test
   bodies are present — the integrity rule observed at runtime, not assumed.
4. Gate emission: run A2 and A3 on the instance (bounded --max-budget-usd) and assert
   ContainerRunBackend.last_gate_events is non-empty for A2 and empty for A3, then that the driver
   threads them onto TrialResult.gate_events.
5. Live claude -p probe: call run_gate_probe(..., reviewer=cli_review_gate) on a DEFECT_MUTATIONS
   entry (the off-by-one mutation of the text_toolkit reference) and assert the returned
   InjectedDefect.caughtBy is "semi-formal-review" (a correctness gate should catch a real fault).
   Keep it under PROBE_MAX_BUDGET_USD / PROBE_TIMEOUT_SECONDS; reuse the existing live-probe wiring.
6. Tests: add benchmark/tests/test_live_container.py with pytest.mark.skipif on the env var (mirror
   test_gate_probes.py's BENCHMARK_RUN_GATE_PROBE_LIVE skip). On a green live run, regenerate the
   _a*_live_evidence/ bundles so the default zero-cost regression surface stays current.
7. Docs: extend benchmark/README.md "how to run a campaign" with the BENCHMARK_RUN_CONTAINER_LIVE
   opt-in and its Docker + claude-CLI + budget prerequisites.
```

This change depends on Docker and the prebuilt greenfield images (a peer dependency already documented for the `container` backend) and on the `claude` CLI being present and authenticated for step 5; it does not touch the Docker-free `local` pipeline, which stays the default test path.

---

## Merge plan

1. Apply each `Proposed changes` block to its canonical page; bump that page's `**Date:**` to the merge date. (Modify the §Scope summary `Implementation` row in `00`; add §Runtime verification, the §Concurrency row, the §Implementation-layout entrypoint, and resolve the *Greenfield image build* open question in `05`; modify the live-probe paragraph lead in `06`.)
2. No `Type changes` to fold — `canonical-types.schema.json` is unchanged.
3. No new canonical page; nothing to index beyond existing entries.
4. Flip this file's `**Status:**` to `Merged`, add `**Merged:** YYYY-MM-DD`, and move it to `docs/benchmark/specs/changes/merged/`.
5. Update `docs/benchmark/README.md`: the Status line already references this change spec — once merged, change "proposed as a change spec" to "verified by the live self-test" and point at `05-harness-architecture.md` → §Runtime verification instead of the change file.

---

## Assumptions and open questions

**Assumptions**

- Docker and the prebuilt greenfield run/scoring images are available on the operator's host when the live verification is enabled; the `local` backend cannot stand in, since the whole point is to exercise the container path.
- The `claude` CLI is installed and authenticated for the live `claude -p` gate-probe step, and a bounded review call returns a parseable `VERDICT:` line within the existing probe budget/timeout.
- Running one greenfield instance through A0 (and optionally A1/A2/A3) is a sufficient runtime witness for the container backends; exhaustive multi-instance live runs are a campaign concern, not a verification concern.

**Decisions**

- *Opt-in, not default.* **Gated behind `BENCHMARK_RUN_CONTAINER_LIVE=1`.** The Docker and token cost cannot sit in CI; the verification mirrors the existing live gate-probe opt-in so the default test surface stays Docker-free and deterministic.
- *Verification, not a metric.* **A pass/fail self-test plus refreshed evidence.** It proves the shipped backends behave; it does not add a `MetricResult` or change any reported number.
- *Integrity observed, not assumed.* **Inspect the provisioned run image for hidden-test content at runtime.** The integrity rule is the benchmark's backbone; a runtime check that the run image is clean is worth more than re-reading the Dockerfile.

**Open questions**

- *Arm coverage.* Does the live self-test need to drive all of A1/A2/A3/A4, or is A0 (round-trip) + A2/A3 (gate emission) + the live probe a sufficient runtime witness, with A1/A4 left to a full campaign?
- *Evidence freshness.* Should a green live run *automatically* overwrite the committed `_a*_live_evidence/` bundles, or write to a scratch location an operator promotes deliberately, to avoid noisy diffs from nondeterministic transcripts?
- *Authenticated CLI in headless runs.* The live `claude -p` step needs an authenticated CLI; how is that provisioned in an unattended operator run without leaking credentials into the container or the captured bundle?
