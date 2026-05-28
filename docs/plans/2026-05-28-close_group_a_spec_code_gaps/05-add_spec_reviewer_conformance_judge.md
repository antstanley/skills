# Task 05 — Add a `spec-reviewer`-backed conformance judge

**Plan:** [plan.md](plan.md) · **Status:** Todo

**Implements:** [06-scoring-and-statistics.md](../../benchmark/specs/06-scoring-and-statistics.md) §The conformance judge — "Where spec-creator's `spec-reviewer` is available, it serves as the judge's procedure; otherwise the rubric applied directly."
**Depends on:** —
**Produces:** a new `spec_reviewer_judge` `JudgeCallable` in `benchmark/harness/scoring/conformance/judge.py` that invokes the `spec-creator:spec-reviewer` skill in R2 mode against the captured `specArtifacts`, normalises the verdict into a `[0,1]` score plus rationale, is selectable per campaign, and is bounded by a named `--max-budget-usd` cap matching the rubric-direct judge's structure. A saved live-judgment evidence file under `benchmark/tests/_conformance_live_evidence/spec_reviewer_judgment.json` demonstrates the path end to end.
**Pointers:** `benchmark/harness/scoring/conformance/judge.py:9` (module docstring naming the rubric-direct path); `benchmark/harness/scoring/conformance/judge.py:83` (`CONFORMANCE_RUBRIC`); `benchmark/harness/scoring/conformance/judge.py:190` (`cli_judge`, the rubric-direct `JudgeCallable`); `benchmark/harness/scoring/conformance/judge.py:268` (`score_arm_conformance`, the per-arm entry point — `JudgeCallable` is its `judge=` keyword); `~/.claude/plugins/marketplaces/skills/plugins/spec-creator/skills/spec-reviewer/SKILL.md` (the skill's invocation surface — R2 mode reviews a canonical spec against implemented code).

## Steps

- [ ] Add a new `spec_reviewer_judge(spec_text, final_code_or_patch, *, max_budget_usd=…) -> ConformanceResult` function in `benchmark/harness/scoring/conformance/judge.py`, structured identically to `cli_judge` (same return type, same parse-and-clamp pipeline). The body invokes the `spec-creator:spec-reviewer` skill in R2 mode as a subprocess: the spec is the `spec_text` argument (handed to the skill as the canonical-spec input), and the code-under-review is the `final_code_or_patch` argument (the agent's captured patch or merged tree).
- [ ] Normalise the R2 verdict line into a `[0,1]` score using a documented mapping: `CONFORMS → 1.0`, `LIKELY_CONFORMS → 0.85`, `CONCERNS → 0.5`, `DIVERGES → 0.1` (the four R2 verdict values). Carry the verdict label and the R2 confidence level into `ConformanceResult.rationale` so a reviewer can see *why* the score landed where it did. Document the mapping as a named-constant table (`_R2_VERDICT_TO_SCORE`) so it is auditable and overridable for calibration.
- [ ] Add a `SPEC_REVIEWER_JUDGE_MAX_BUDGET_USD` named constant mirroring `CONFORMANCE_MAX_BUDGET_USD` (the rubric-direct cap). Pass it to the subprocess as a hard budget cap; on overspend, the function raises with context — the same shape `cli_judge` uses.
- [ ] Make the judge selectable per campaign. Lighter-touch option: thread a `judge: JudgeCallable | str` parameter through `score_arm_conformance` and accept a name string (`"rubric"` / `"spec-reviewer"`) that the helper resolves to the matching `JudgeCallable`. Heavier option: add a `conformanceJudge: str` field on `Campaign` (schema delta). Pick the lighter touch — the runtime parameter — and document the choice; a `Campaign` field can come later via a focused schema change spec.
- [ ] Gate the live test as the other live conformance tests are gated: a new `BENCHMARK_RUN_SPEC_REVIEWER_JUDGE_LIVE=1` opt-in env var, mirroring `BENCHMARK_RUN_CONFORMANCE_LIVE`. The test invokes `spec_reviewer_judge` on a saved A2 patch + the captured `specArtifacts` from `benchmark/tests/_a2_a3_live_evidence/a2/artifact_bundle.json`, asserts a `[0,1]` score is returned with non-empty rationale, and saves the judgment evidence to `benchmark/tests/_conformance_live_evidence/spec_reviewer_judgment.json` — durable evidence a reviewer reads without re-spending budget.
- [ ] Non-live tests: parse-and-clamp behaviour on a synthetic R2 verdict line, the verdict-to-score mapping returns the right value for each of the four labels, the budget-cap raise fires on a simulated overspend, the `judge=` parameter wiring resolves the name strings correctly. All deterministic; no API call.

## Definition of done

- [ ] `spec_reviewer_judge` invokes the `spec-creator:spec-reviewer` skill in R2 mode and returns a `ConformanceResult` with a `[0,1]` score and a rationale carrying the verdict label and R2 confidence.
- [ ] The judge is selectable per campaign via the `judge=` parameter on `score_arm_conformance`, accepting the name strings `"rubric"` and `"spec-reviewer"` plus a callable injectable for tests.
- [ ] Budget cap is a named constant (`SPEC_REVIEWER_JUDGE_MAX_BUDGET_USD`); an overspend raises a typed exception with context rather than returning a partial score.
- [ ] Negative-space: an R2 verdict line the parser does not recognise raises `ConformanceJudgeError` rather than silently returning a default score (the same behaviour `cli_judge` provides for malformed rubric responses).
- [ ] Live test gated on `BENCHMARK_RUN_SPEC_REVIEWER_JUDGE_LIVE=1`, mirrors the rubric-direct live test's saved-evidence pattern (`benchmark/tests/_conformance_live_evidence/`), and skips cleanly on CI.
- [ ] Meets the repo definition of done (uv-locked deps, ruff format + lint clean, pyright clean, pytest clean — see `plan.md` baseline). No schema delta (the runtime-parameter selection avoids touching `Campaign`).
- [ ] Reviewable: a reviewer runs the non-live tests, opts in to the live test once on a saved A2 patch, reads the resulting `spec_reviewer_judgment.json`, and confirms the score and rationale make sense against the canonical spec the patch was judged against.

## Open questions

- *Verdict-to-score mapping.* The proposed mapping (`CONFORMS → 1.0`, `LIKELY_CONFORMS → 0.85`, `CONCERNS → 0.5`, `DIVERGES → 0.1`) is one defensible reading; an alternative weights the R2 confidence (`high`/`medium`/`low`) into the score so a `LIKELY_CONFORMS / low` lands lower than a `LIKELY_CONFORMS / high`. Pin the chosen mapping during implementation and record it as a `Decision` in `06-scoring-and-statistics.md` so it is comparable across campaigns.
