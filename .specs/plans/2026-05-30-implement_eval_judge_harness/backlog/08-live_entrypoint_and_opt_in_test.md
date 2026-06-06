# Task 08 — Live entrypoint and opt-in test

**Plan:** [plan.md](../plan.md)

**Implements:** [04-report-and-cli.md](../../../evaljudge/specs/04-report-and-cli.md) §The entrypoint and gate posture, §Flow
**Depends on:** 04, 07
**Produces:** `uv run -m benchmark.evaljudge.run_sweep` — the opt-in live entrypoint that runs a real bounded sweep (the `local` run backend + the live judge) under `EVALJUDGE_RUN_LIVE=1`, writes the report, and sets exit status; plus a default-skipped `benchmark/tests/test_evaljudge_live.py` that SKIPs cleanly without the env var, and README documentation of the opt-in
**Pointers:** new `benchmark/evaljudge/run_sweep.py`; opt-in/skip + entrypoint pattern from `benchmark/harness/run_container_check.py` + `benchmark/tests/test_live_container.py` (`BENCHMARK_RUN_CONTAINER_LIVE` precedent); wires the `LocalRunBackend` (04) into the driver (07); docs in `benchmark/README.md` and [.specs/evaljudge/README.md](../../../evaljudge/README.md)

## Steps

- [ ] Implement `run_sweep.py` as a module entrypoint: parse the selection (all / `--skill S` / `--case S:ID`) and caps, build the driver with the `local` `RunBackend` and the live `JudgeCallable`, run the sweep, write the report to the evidence path, and render the summary.
- [ ] Gate the live path behind `EVALJUDGE_RUN_LIVE=1` (the eval-judge counterpart of `BENCHMARK_RUN_CONTAINER_LIVE`); without it, the entrypoint and the test SKIP with a clear message naming the env var and the `claude` CLI prerequisite.
- [ ] Set exit status: non-zero when any case is `FAIL` or `NOT_RUN`, with a `--allow-not-run` flag that treats environment-caused `NOT_RUN`s as non-fatal while still failing on a real `FAIL`.
- [ ] Add `benchmark/tests/test_evaljudge_live.py`: a `skipif(not EVALJUDGE_RUN_LIVE)` wrapper that, when enabled, runs one real bounded eval and asserts the report shape and a `[0,1]` score with a non-empty rationale; when disabled (CI default), SKIPs cleanly.
- [ ] Document the opt-in in `benchmark/README.md` and [.specs/evaljudge/README.md](../../../evaljudge/README.md): the env var, the `claude` CLI + plugin prerequisite, the budget caps, and how to run a single-skill sweep.
- [ ] Confirm `uv run pytest benchmark/tests` stays green with the live test SKIPping (no Docker, no `claude` CLI, no env var).

## Definition of done

- [ ] `uv run -m benchmark.evaljudge.run_sweep` runs a real bounded sweep under `EVALJUDGE_RUN_LIVE=1` and sets exit status per the FAIL/NOT_RUN posture (reviewed by reading; the live path needs an authenticated `claude` CLI not present in CI).
- [ ] `benchmark/tests/test_evaljudge_live.py` SKIPs cleanly without the env var, so `uv run pytest benchmark/tests` stays green and Docker-free.
- [ ] Exit status fails on `FAIL`/`NOT_RUN` by default; `--allow-not-run` distinguishes an environment `NOT_RUN` from a real `FAIL`.
- [ ] Negative space: the no-env, no-CLI path SKIPs (the verified path), exactly as the benchmark's `*_LIVE` tests do.
- [ ] `benchmark/README.md` and `.specs/evaljudge/README.md` document the opt-in, prerequisites, and caps.
- [ ] Meets the repo definition of done (tests green with the live test skipped, ruff, pyright — see plan.md baseline).
- [ ] Reviewable: a non-operator runs `uv run pytest benchmark/tests` and sees the live test SKIP cleanly; a reviewer reads the entrypoint's gate, exit-status logic, and README opt-in.

## Open questions

- The plugin-install mechanism for the live run (carried from task 04 / [02-run-stage.md](../../../evaljudge/specs/02-run-stage.md)) must be pinned before an operator runs the live sweep; it does not block the skip-path build.
- Whether a green live sweep auto-overwrites the saved evidence report or writes to a scratch path an operator promotes (carried from [04-report-and-cli.md](../../../evaljudge/specs/04-report-and-cli.md) Open questions).
