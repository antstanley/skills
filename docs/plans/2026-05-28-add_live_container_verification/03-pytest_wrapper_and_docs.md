# Task 03 — Pytest wrapper, README opt-in docs, evidence refresh

**Plan:** [plan.md](plan.md) · **Status:** Done

> **Built 2026-05-28.** Gate 1 (semi-formal-review): CORRECT — three CI guard tests (`evaluate_skip`/`main` skip cleanly) pass, the live test skips by default, README opt-in subsection complete. Gate 2 (validate-done-certificate): DONE — `pytest benchmark/tests` green (332 passed, 7 skipped).

**Implements:** [changes/2026-05-28-add_live_container_verification.md](../../benchmark/specs/changes/merged/2026-05-28-add_live_container_verification.md) → §Proposed changes → `05-harness-architecture.md` §Runtime verification (the default-skipped test surface) and §Implementation layout (the `run_container_check.py` entrypoint row); Implementation notes steps 6–7.
**Depends on:** 01, 02
**Produces:** `uv run pytest benchmark/tests/test_live_container.py` SKIPs cleanly without `BENCHMARK_RUN_CONTAINER_LIVE=1`; `benchmark/README.md` documents the opt-in and its Docker + `claude`-CLI + budget prerequisites.
**Pointers:** skip pattern `@pytest.mark.skipif(os.environ.get(...) != "1", ...)` (`benchmark/tests/test_gate_probes.py:391`); the `run_container_check.py` functions from tasks 01–02; `benchmark/README.md` "how to run a campaign" section; `_a*_live_evidence/` bundle dirs under `benchmark/tests/`.

## Steps

- [x] Add `benchmark/tests/test_live_container.py`: a thin pytest wrapper that calls the `run_container_check.py` verification functions, each test guarded by `@pytest.mark.skipif(os.environ.get(LIVE_CONTAINER_ENV) != "1", reason=...)` mirroring the live-gate-probe test.
- [x] Add a test that the **skip path** is clean: with the env unset, the wrapper test reports SKIPPED (not error, not pass), so the default `uv run pytest benchmark/tests` run stays green without Docker.
- [x] Extend `benchmark/README.md` "how to run a campaign" with a short subsection on the `BENCHMARK_RUN_CONTAINER_LIVE=1` opt-in: what it runs (the container round-trip + gate emission + live `claude -p` probe), and its prerequisites (Docker ≥ 25, an authenticated `claude` CLI, a small real budget).
- [x] Document the evidence-refresh step as conditional: a green live run may regenerate the `benchmark/tests/_a*_live_evidence/` bundles, but this is an operator action, not a CI step (auto-vs-manual promotion is an open question — see plan.md).

## Definition of done

- [x] `uv run pytest benchmark/tests/test_live_container.py` with the env unset reports the live tests as **SKIPPED** with a clear reason; `uv run pytest benchmark/tests` stays green overall (no new failures, no collection error).
- [x] `benchmark/README.md` names the `BENCHMARK_RUN_CONTAINER_LIVE` opt-in and its Docker / `claude`-CLI / budget prerequisites, consistent with the `Status: Built` framing the README already carries.
- [x] Negative space: the wrapper does not import-time-fail or run a container when the env is unset (the skip happens at collection/guard time, not after provisioning).
- [x] Meets the repo definition of done (ruff, pyright on library code, `uv run pytest benchmark/tests` green; the new test SKIPs rather than errors — see plan.md baseline).
- [x] Reviewable: a reviewer runs `uv run pytest benchmark/tests/test_live_container.py` with no env set and sees SKIPPED, and reads the README subsection to confirm the opt-in and prerequisites are documented.
