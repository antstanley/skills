# Task 01 — BenchFlow scaffold

**Plan:** [plan.md](plan.md) · **Status:** Todo · **Certificate:** [certificates/01-benchflow_scaffold.md](certificates/01-benchflow_scaffold.md)

**Implements:** [05-harness-architecture.md](../../benchmark/specs/05-harness-architecture.md) §Substrate — BenchFlow, §Implementation layout
**Depends on:** 17
**Produces:** the BenchFlow `bench` SDK layered onto the existing package skeleton (task 17) — a trivial task passes `bench tasks check`, dependencies stay uv-locked, and `pytest` + `ruff` run clean
**Pointers:** the task 17 skeleton (`benchmark/` tree, `pyproject.toml`); `.python-version` = 3.13

## Steps

- [ ] Add the BenchFlow `bench` SDK as a uv-managed dependency and lock it.
- [ ] Create the `benchmark/` package skeleton — `harness/` (driver, arms, scoring, telemetry, stats) and `suites/` — as empty, importable modules matching the spec's layout.
- [ ] Wire `pytest` and `ruff` (lint + format) with config in `pyproject.toml`.
- [ ] Add one trivial throwaway BenchFlow task and confirm `bench tasks init` / `bench tasks check` succeed against it.
- [ ] Confirm the BenchFlow SDK can express a custom task schema and a two-step (run, then score) eval; record any limitation that blocks the two-container split as an Open question.

## Definition of done

- [ ] `bench tasks check` passes on the trivial task and the project imports cleanly.
- [ ] BenchFlow's ability to host a custom schema + per-arm provisioning + a separate scoring step is confirmed, or the gap is recorded in plan.md's Open questions.
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer runs `uv run bench tasks check` and the test suite, and both pass on a clean checkout.

## Open questions

- Whether the two-container run/scoring split is expressible within BenchFlow's eval model or needs a thin wrapper around it — resolve here so tasks 04/05/07 build on a known substrate.
