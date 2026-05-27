# Docs

Design specifications and plans for the `antstanley/skills` marketplace repo.

## Global specs (`docs/specs/`)

Repo-wide, cross-cutting design.

- [Plugin Marketplace Design](specs/spec.md) — how the repo is structured as a Claude Code plugin marketplace.

## Per-app specs

App- or component-specific design, layered on the global specs.

| App | Specs | Topic |
|---|---|---|
| benchmark | [docs/benchmark/specs/](benchmark/specs/) | Harness for benchmarking the `spec-*` development workflow against a single-agent baseline. |

## Change specs

Proposed deltas to canonical specs (`Proposed → Accepted → Implemented → Merged`); merged ones move to a `changes/merged/` area.

- [benchmark/specs/changes/2026-05-27-local_backends.md](benchmark/specs/changes/2026-05-27-local_backends.md) — *Accepted.* Pluggable run/scoring backends (`container` + `local`) and a `local-fixture` suite, so the harness builds and runs without Docker.

## Plans

Implementation plans (forward-looking; sequence work by dependency and reviewability).

- [docs/plans/2026-05-27-spec_workflow_benchmark/](plans/2026-05-27-spec_workflow_benchmark/plan.md) — build plan for the spec-workflow benchmark harness (*Accepted*; 23 tasks, 5 milestones M0–M4 with a Docker-free local M0, done certificates per task).
- [docs/superpowers/plans/2026-05-18-plugin-marketplace.md](superpowers/plans/2026-05-18-plugin-marketplace.md) — plugin-marketplace migration plan.
