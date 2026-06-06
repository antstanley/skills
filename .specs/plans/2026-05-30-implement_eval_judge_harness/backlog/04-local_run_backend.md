# Task 04 — Local run backend

**Plan:** [plan.md](../plan.md)

**Implements:** [02-run-stage.md](../../../evaljudge/specs/02-run-stage.md) §The run backend (`local`), §Live invocation, §Safety / reproducibility
**Depends on:** 02, 03
**Produces:** the `local` Docker-free `RunBackend` — invokes a skill via one bounded `claude -p` in an isolated temp working directory seeded with the case's `files`, captures behavior via task 03, and classifies the outcome `completed`/`run_failed`/`timed_out`/`budget_exceeded`; every bound a named constant
**Pointers:** new `benchmark/evaljudge/run/local.py`; bounded-`claude -p` shape **mirrored from** `benchmark/harness/scoring/conformance/judge.py` `cli_judge` (`subprocess.run`, the `--output-format json` envelope parse, typed error on non-zero exit). Note `cli_judge`'s shell-quoting helper `_shell_quote` is module-private — do not import it; re-implement the one-line POSIX single-quote locally (or build the argv list without a shell). Temp-dir + `finally` cleanup pattern from the benchmark `local` backend.

## Steps

- [ ] Define the named constants: `RUN_MODEL`, `RUN_MAX_BUDGET_USD`, `RUN_TIMEOUT_SECONDS`, `RUN_TEMP_BASE` (all `SCREAMING_SNAKE_CASE`, documented).
- [ ] Implement `LocalRunBackend.run(redacted_case, *, budget, timeout)`: create a temp working dir under `RUN_TEMP_BASE`, seed `redacted_case.files`, invoke `claude -p <prompt> --model RUN_MODEL --max-budget-usd <cap> --output-format json` with `cwd` set there and the plugin available; clean the temp dir in `finally`.
- [ ] Parse the `claude --output-format json` envelope for the `result` text (reuse the conformance judge's envelope-parsing approach); capture file changes via task 03's capture helper.
- [ ] Classify the outcome: exit 0 → `completed`; non-zero → `run_failed` (retain stderr context); over wall-clock → `timed_out`; over budget → `budget_exceeded`. Never a silent partial; a non-`completed` `EvalRun` carries the diagnostic context.
- [ ] Make the `claude` invocation injectable (a callable seam, mirroring `JudgeCallable`) so the backend's classification logic is tested with a stubbed subprocess and no real CLI call.
- [ ] Add `benchmark/tests/test_evaljudge_local_backend.py` (hermetic): a stubbed invocation returning a JSON envelope yields a `completed` `EvalRun` with captured response + file changes; stubbed non-zero / timeout / budget-overspend each classify correctly; the temp dir is cleaned even when the run raises.

## Definition of done

- [ ] `LocalRunBackend` invokes the skill in an isolated temp dir and returns a `completed` `EvalRun` (response + file_changes) on success, with the invocation behind an injectable seam for hermetic testing.
- [ ] All four statuses classify correctly from stubbed subprocess outcomes; the redacted case (not the full `EvalCase`) is what the backend receives.
- [ ] Negative space: non-zero exit, timeout, and budget overspend each produce the right non-`completed` status with retained context; the temp dir is cleaned in `finally` on the error path.
- [ ] Every limit (model, budget, timeout, temp base) is a named constant.
- [ ] Meets the repo definition of done (tests, ruff, pyright, no `None`-as-error — see plan.md baseline). The live (real-`claude`) path is reviewed by reading; the hermetic stubbed path is what CI runs.
- [ ] Reviewable: `uv run pytest benchmark/tests/test_evaljudge_local_backend.py` is green; a reviewer reads the four classification branches and the `finally` cleanup.

## Open questions

- The non-interactive plugin-install mechanism for the live `claude -p` call (a `--plugin-dir`-style flag vs. a marketplace install vs. a config shim) must be pinned in the build environment ([02-run-stage.md](../../../evaljudge/specs/02-run-stage.md) Open questions). It blocks the live path only; the stubbed classification tests do not need it.
