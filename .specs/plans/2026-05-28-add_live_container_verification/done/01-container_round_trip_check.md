# Task 01 — Container round-trip check (the integrity witness)

**Plan:** [plan.md](../plan.md)

> **Built 2026-05-28.** Gate 1 (semi-formal-review): LIKELY_CORRECT — one host-side fault found and fixed (a doubled `REPO_SUBDIR` in `hidden_test_fingerprints` that had silently disabled the content-integrity half), re-reviewed clean; live Docker path judged by reading. Gate 2 (validate-done-certificate): DONE — all five obligations satisfied, skip path verified (exit 0), ruff/pyright/pytest green.

**Implements:** [changes/2026-05-28-add_live_container_verification.md](../../../benchmark/specs/changes/merged/2026-05-28-add_live_container_verification.md) → §Proposed changes → `05-harness-architecture.md` §Runtime verification (the *provisioning + capture*, *integrity rule observed*, and *two-container scoring* bullets); Implementation notes steps 1–3.
**Depends on:** —
**Produces:** `BENCHMARK_RUN_CONTAINER_LIVE=1 uv run python -m benchmark.harness.run_container_check` provisions the greenfield `text_toolkit` run container, runs the A0 arm, scores it in a *separate* scoring container, and asserts the `resolved` verdict equals the `local` backend's verdict on the same patch and that the run image carries no hidden-test content. Without the env var or Docker the module exits cleanly with a clear message.
**Pointers:** mirror `benchmark/harness/run_local_demo.py` (sibling entrypoint shape); `ContainerRunBackend.run` (`benchmark/harness/backends/container.py:363`); `ContainerScoringBackend` (`container.py`); `LocalScoringBackend` + `benchmark/harness/scoring/resolution.py` (single-sourced resolved rule); `benchmark.suites.greenfield` (`load_instance`, `load_reference_solution`, `text_toolkit` slug); `benchmark.suites.greenfield_images.docker_available` / `build_images`; arm A0 record (`benchmark/harness/arms/a0.py`); skip pattern from `benchmark/tests/test_gate_probes.py:391`.

## Steps

- [x] Create `benchmark/harness/run_container_check.py` with a module docstring tracing it to the change spec's §Runtime verification, alongside `run_local_demo.py`.
- [x] Add the opt-in guard: a named `LIVE_CONTAINER_ENV = "BENCHMARK_RUN_CONTAINER_LIVE"` constant; when it is unset / `!= "1"`, or `greenfield_images.docker_available()` is false, or the `claude` CLI is absent, return/exit cleanly with a single clear message (no exception, no partial run) — the same opt-in discipline as the live gate probe.
- [x] Implement the A0 container round-trip: load the `text_toolkit` instance, run `ContainerRunBackend().run(instance, A0_arm)` to get `(bundle, patch)`, then `ContainerScoringBackend().score(instance, patch)` to get a `ScoreReport`.
- [x] Assert resolved-parity: score the *same* `patch` through `LocalScoringBackend` and assert both backends agree on `resolved` (single-source the rule via `resolution.py`; do not re-implement it). Use the instance `reference/solution.patch` for a known-good run and `None`/no-op for the known-`false` run so the witness has both poles.
- [x] Add the integrity assertion: inspect the provisioned **run** image (e.g. a `docker run` listing `/workspace`) and assert no path under `hidden/` exists and none of `instance.failToPass` / `instance.passToPass` test bodies are present — observed at runtime, not inferred from the Dockerfile. Reuse `HIDDEN_TEST_FIELDS` (`benchmark/harness/backends/interfaces.py:51`).
- [x] Name every limit a constant: the env-var name, any budget cap, and any docker/exec timeout are `SCREAMING_SNAKE_CASE` module constants, not literals.

## Definition of done

- [x] Running the module **without** `BENCHMARK_RUN_CONTAINER_LIVE=1` (or without Docker) skips cleanly: a clear printed message, exit 0, no traceback, no container started.
- [x] When run live (operator, reviewed by reading here), the A0 round-trip asserts `container` and `local` backends agree on `resolved`, and the run-image integrity check asserts no hidden-test path/content is present.
- [x] Negative space: the no-op / no-reference patch yields `resolved: false` on both backends (the known-`false` pole), proving the witness is not trivially always-true.
- [x] Meets the repo definition of done (ruff lint+format, pyright standard, `uv run pytest benchmark/tests` green; named-constant limits — see plan.md baseline).
- [x] Reviewable: a reviewer runs `uv run python -m benchmark.harness.run_container_check` with the env unset and sees a clean skip, and reads the module to confirm the round-trip + parity + integrity assertions are correct for the live path.
