# Docs

Design specifications and plans for the `antstanley/skills` marketplace repo.

## Global specs (`docs/specs/`)

Repo-wide, cross-cutting design.

- [Plugin Marketplace Design](specs/spec.md) — how the repo is structured as a Claude Code plugin marketplace.
- [Development Guidelines](specs/development-guidelines.md) — rules of the road for writing code (Clean Code style; Python conventions; jj version control; definition of done).

## Per-app specs

App- or component-specific design, layered on the global specs.

| App | Specs | Topic |
|---|---|---|
| benchmark | [docs/benchmark/specs/](benchmark/specs/) | Harness for benchmarking the `spec-*` development workflow against a single-agent baseline. |

## Change specs

Proposed deltas to canonical specs (`Proposed → Accepted → Implemented → Merged`); merged ones move to a `changes/merged/` area.

Pending:

- [benchmark/specs/changes/2026-05-27-add_swe_bench_pro_suite.md](benchmark/specs/changes/2026-05-27-add_swe_bench_pro_suite.md) — *Proposed.* Add the `swe-bench-pro-public` issue-fixing suite (reusing SWE-bench Pro's instances, `jefzda/sweap-images`, and oracle) back to the benchmark, on the `container` backend. Re-adds the suite the minimal canonical deferred; touches benchmark specs 00/01/02/03/04/05/06 and the canonical schema.

Merged ([benchmark/specs/changes/merged/](benchmark/specs/changes/merged/)):

- [benchmark/specs/changes/merged/2026-05-27-local_backends.md](benchmark/specs/changes/merged/2026-05-27-local_backends.md) — *Merged 2026-05-27.* Pluggable run/scoring backends (`container` + `local`) and a `local-fixture` suite, so the harness builds and runs without Docker. Folded into benchmark specs 01/03/05/06 and the canonical schema.
- [benchmark/specs/changes/merged/2026-05-27-trim_deferred_swe_bench_pro_code.md](benchmark/specs/changes/merged/2026-05-27-trim_deferred_swe_bench_pro_code.md) — *Merged 2026-05-27.* Removed the leftover `issue-fixing` / `swe-bench-pro` enum values, a `resolution.py` docstring attribution, and the SWE-bench Pro test fixtures so the code matches the minimal canonical. Code-only; no canonical or schema delta.
- [benchmark/specs/changes/merged/2026-05-28-promote_built_state_and_resolved_decisions.md](benchmark/specs/changes/merged/2026-05-28-promote_built_state_and_resolved_decisions.md) — *Merged 2026-05-28.* Caught the canonical pages up to the built reality (integration tip `4184092d`): `Status: Draft → Built` and the matching framing rewrites on 00; promoted five resolved Open questions to Decisions across 02/04/06; rewrote §Substrate and §Implementation layout on 05 and 06; fixed the `dockerImage` row wording on 03; fixed the fictional example slug on 01. Prose-only.
- [benchmark/specs/changes/merged/2026-05-28-document_shipped_surfaces.md](benchmark/specs/changes/merged/2026-05-28-document_shipped_surfaces.md) — *Merged 2026-05-28.* Added canonical body for ten shipped public surfaces: §Persistence + §Runtime aggregates on 01; A4 dollar-budget matching, naive-merge policy, and gate observability on 02; per-instance `given_spec/`, `reference/solution.patch`, `testTags`, and agent-image surfaces on 03; GateEvent threading and the `ArmOrSolver` alias on 05; pairing-reduction rule, defect taxonomy, and live-probe verdict mapping on 06. Body-only.

## Plans

Implementation plans (forward-looking; sequence work by dependency and reviewability).

- [docs/plans/2026-05-27-spec_workflow_benchmark/](plans/2026-05-27-spec_workflow_benchmark/plan.md) — build plan for the spec-workflow benchmark harness (*In progress*; 22 tasks, 5 milestones M0–M4 with a Docker-free local M0, done certificates per task). M0 built; M1–M4 re-planned 2026-05-27 to drop SWE-bench Pro and run the ablation on the greenfield suite only.
- [docs/plans/2026-05-28-close_group_a_spec_code_gaps/](plans/2026-05-28-close_group_a_spec_code_gaps/plan.md) — *Draft.* Close the five Group A spec-vs-code gaps the R2 conformance review surfaced on the benchmark harness: populate `ScoreReport.gateEscape` (01), capture intra-trial workflow timing so parallel speedup matches the spec definition (02), emit a `MetricResult` for every ablation column (03), compute the cost-matched paired delta (04), add a `spec-reviewer`-backed conformance judge (05). Two milestones (M1 scoring/stats closure, M2 judge alternative). No done certificates authored (skipped at user request).
- [docs/superpowers/plans/2026-05-18-plugin-marketplace.md](superpowers/plans/2026-05-18-plugin-marketplace.md) — plugin-marketplace migration plan.
