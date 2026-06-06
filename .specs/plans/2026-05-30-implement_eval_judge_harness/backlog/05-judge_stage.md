# Task 05 — Judge stage

**Plan:** [plan.md](../plan.md)

**Implements:** [03-judge-stage.md](../../../evaljudge/specs/03-judge-stage.md) §The rubric, §The bounded judge call, §Score → band → verdict
**Depends on:** 01
**Produces:** `score_eval(expected_output, EvalRun, *, judge) -> EvalJudgment` plus verdict derivation — builds the eval-conformance rubric prompt (expected behavior vs actual behavior), runs an injectable `JudgeCallable`, parses+clamps via the conformance judge's helpers, and maps the score to a `band` and `PASS`/`FAIL` through a named `PASS_THRESHOLD`
**Pointers:** new `benchmark/evaljudge/judge/rubric.py`, `benchmark/evaljudge/judge/judge.py`, `benchmark/evaljudge/judge/__init__.py`; **import** from `benchmark.harness.scoring.conformance`: `JudgeCallable`, `clamp_score`, `SCORE_MIN`/`SCORE_MAX`, `parse_judge_response`, `bucket_of` (all re-exported by the package `__init__`). The band-boundary constants `BANDS`/`LOW_BAND_MAX`/`HIGH_BAND_MIN` are **not** in the package `__all__` — import them from the submodule `benchmark.harness.scoring.conformance.calibration` if needed (or rely on the re-exported `bucket_of`, which already encapsulates the bands). Pattern source `judge.py` (`build_rubric_prompt`, `cli_judge`).

## Steps

- [ ] Author the eval-conformance rubric constant (the four axes from [03-judge-stage.md](../../../evaljudge/specs/03-judge-stage.md): behavioral coverage, output-structure fidelity, correct refusals/constraints, no unexpected divergence), instructing the judge to score fidelity to `expected_output` only and return strict `{score, rationale}` JSON.
- [ ] Implement the prompt builder: rubric text + a delimited `EXPECTED BEHAVIOR` block (`expected_output`) + a delimited `ACTUAL BEHAVIOR` block (the `EvalRun` response and a rendering of its `file_changes`); section headers are named constants.
- [ ] Implement `score_eval(expected_output, run, *, judge=<cli default>)`: build the prompt, call the injectable `JudgeCallable`, parse with the imported `parse_judge_response`, clamp with the imported `clamp_score`, return an `EvalJudgment` (`score`, `raw_score`, `rationale`).
- [ ] Define `JUDGE_MODEL`, `JUDGE_MAX_BUDGET_USD`, `JUDGE_TIMEOUT_SECONDS`, and `PASS_THRESHOLD` as named constants; implement the live `claude -p` judge call in the `cli_judge` shape (reused/mirrored), kept behind the injectable seam.
- [ ] Implement verdict derivation: `band = bucket_of(score)`; `PASS` iff `score >= PASS_THRESHOLD`, else `FAIL` (derived, never asked of the judge). A non-`completed` run never reaches here.
- [ ] Add `benchmark/tests/test_evaljudge_judge.py` (hermetic): an injected deterministic judge yields a clamped score from over/under-range raw scores; the prompt builder embeds both the expected and actual blocks; band + PASS/FAIL derive correctly around the threshold; a malformed judge response raises the typed judge error (reused `ConformanceJudgeError`), never an uncaught parse crash.

## Definition of done

- [ ] `score_eval` turns `(expected_output, EvalRun)` into an `EvalJudgment` with a clamped `[0,1]` score and rationale via an injectable `JudgeCallable`.
- [ ] The conformance judge's primitives (`clamp_score`, `parse_judge_response`, `JudgeCallable`, `SCORE_MIN`/`SCORE_MAX`, the bands) are **imported**, not re-implemented (a reviewer confirms no forked copy).
- [ ] Verdict derives from the score via the named `PASS_THRESHOLD`; the judge is never asked for a boolean.
- [ ] Negative space: an over-range and under-range raw score clamp; a malformed judge response raises the typed error.
- [ ] Every limit (model, budget, timeout, threshold) is a named constant.
- [ ] Meets the repo definition of done (tests, ruff, pyright — see plan.md baseline). The live judge call is reviewed by reading; the injected-judge path is what CI runs.
- [ ] Reviewable: `uv run pytest benchmark/tests/test_evaljudge_judge.py` is green; a reviewer sees a deterministic judge drive a score→band→verdict with no model call.

## Open questions

- `PASS_THRESHOLD`'s value is a documented placeholder until task 06 calibrates it; this task ships the derivation mechanism and a provisional constant.
- How a large `file_changes` set is rendered into the prompt (full vs. tree+excerpts) is settled during task 06 calibration; this task renders straightforwardly and leaves tuning to calibration.
