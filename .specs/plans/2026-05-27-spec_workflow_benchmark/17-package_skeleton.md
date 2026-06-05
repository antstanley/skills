# Task 17 — Python package skeleton (no BenchFlow)

**Plan:** [plan.md](plan.md) · **Status:** Done · **Certificate:** [certificates/17-package_skeleton.md](certificates/17-package_skeleton.md)

**Implements:** [05-harness-architecture.md](../../benchmark/specs/05-harness-architecture.md) §Implementation layout (the Docker-free core, minus the BenchFlow substrate); [changes/merged/2026-05-27-local_backends.md](../../benchmark/specs/changes/merged/2026-05-27-local_backends.md)
**Depends on:** —
**Produces:** a uv-managed Python package — the `benchmark/` tree with `pytest` + `ruff` wired and dependencies locked — that imports and tests clean **without** BenchFlow
**Pointers:** repo root (`pyproject.toml`, `.python-version` = 3.13); new `benchmark/` package per the spec's layout

## Steps

- [x] Create the `benchmark/` package tree: `harness/{driver,arms,scoring,backends,telemetry,stats}` and `suites/`, as empty importable modules.
- [x] Wire `pytest` and `ruff` (lint + format) in `pyproject.toml`; add one trivial smoke test.
- [x] Add and lock the minimal runtime deps (a JSON Schema validator for task 02); do **not** add BenchFlow — it is deferred to task 01.
- [x] Confirm `uv run pytest` passes and `import benchmark.harness` resolves.

## Definition of done

- [ ] `uv run pytest` passes the smoke test and `import benchmark.harness` (and the sub-packages) resolves.
- [ ] No BenchFlow dependency is present — the skeleton is the Docker-free root, with BenchFlow split out to task 01.
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: on a clean checkout a reviewer runs `uv sync` and `uv run pytest` and both pass with no BenchFlow installed.
