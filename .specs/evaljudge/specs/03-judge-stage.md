# 03 — Judge Stage

The judge stage turns an [`EvalRun`](01-domain-model.md#evalrun) — the skill's actual behavior — into an [`EvalJudgment`](01-domain-model.md#evaljudgment) and then a verdict, by scoring that behavior against the case's `expected_output`. It is a near-direct reuse of the benchmark's conformance judge ([`benchmark/harness/scoring/conformance/judge.py`](../../../benchmark/harness/scoring/conformance/judge.py)) pointed at a different pair: where the conformance judge scores `(spec, code)`, this judge scores `(expected_output, actual behavior)`.

> **Read first:** the conformance judge's design is documented in [`.specs/benchmark/specs/06-scoring-and-statistics.md`](../../benchmark/specs/06-scoring-and-statistics.md) → §The conformance judge. This page describes only how the eval-judge stage differs from it. The shared machinery — the injectable `JudgeCallable`, the bounded `claude -p` call, tolerant JSON parsing, `[0, 1]` clamping, the calibration harness — is the conformance judge's and is not re-specified here.

---

## Responsibilities

1. **Build a rubric prompt** embedding the case's `expected_output` (the authority) and the EvalRun's captured behavior (response + file changes).
2. **Run one bounded judge call** — the injectable `JudgeCallable`, defaulting to a live `claude -p`, returning `{score, rationale}` as strict JSON.
3. **Parse, clamp, and record** the score into an `EvalJudgment` (`score`, `raw_score`, `rationale`).
4. **Derive the verdict** — map the clamped score through a named threshold to a `band` and a `PASS | FAIL`.

The judge runs **host-side** and is the scorer, never the system under test — it needs no working directory and never re-invokes the skill. The same posture as the conformance judge.

---

## The rubric

The judge applies a structured rubric, the eval-judge counterpart of `CONFORMANCE_RUBRIC`. It frames `expected_output` as the authority and the captured behavior as the thing under test, and asks for a single `[0, 1]` score plus a one-paragraph rationale returned as strict JSON. The rubric weighs these axes:

1. **Behavioral coverage** — does the actual behavior do everything `expected_output` says it should (every produced artifact, every stated step, every required section)?
2. **Output-structure fidelity** — where `expected_output` prescribes a shape (a numbered file set, a `VERDICT:` block, a "Read first" pointer, a header with `Status/Date/Owner`), does the behavior exhibit it?
3. **Correct refusals and constraints** — where `expected_output` says the skill should *not* do something (no MVP framing, do not edit the change spec unprompted, skip a trivial change), did the behavior honour that?
4. **No unexpected divergence** — the behavior does not add actions that contradict `expected_output` or violate the skill's stated discipline.

The rubric instructs the judge to score against `expected_output` **only** — not against the judge's own opinion of what the skill should ideally do. `expected_output` is the contract; the judge measures fidelity to it, exactly as the conformance rubric measures fidelity to the spec and explicitly excludes hidden-test resolution from the judgment.

The prompt is built the same way as `build_rubric_prompt`: the rubric text, then a delimited `EXPECTED BEHAVIOR` block (the `expected_output`), then a delimited `ACTUAL BEHAVIOR` block (the run's response and a rendering of its `file_changes`). Section headers are named constants so the builder and its test agree.

---

## The bounded judge call

One `claude -p` call per eval, identical in shape to `cli_judge`:

```
claude -p <rubric_prompt> --model <JUDGE_MODEL> --max-budget-usd <JUDGE_MAX_BUDGET_USD> --output-format json
```

The backend is an injectable `JudgeCallable` (given the built prompt, return the raw model text). Tests pass a deterministic mock; the live default is the bounded CLI call. Response parsing reuses the conformance judge's tolerant `parse_judge_response`: scan for the first `{` and last `}`, parse that span, require a numeric `score`, default `rationale` to empty — raising a typed judge error (never an uncaught `JSONDecodeError`) when no judgeable object can be recovered.

Named-constant rails, mirroring the conformance judge:

| Constant | Meaning |
|---|---|
| `JUDGE_MODEL` | Fixed model alias the judge runs on. |
| `JUDGE_MAX_BUDGET_USD` | Hard per-judgment `--max-budget-usd` cap (one focused scoring call — a small cap). |
| `JUDGE_TIMEOUT_SECONDS` | Wall-clock ceiling for the single call. |
| `SCORE_MIN` / `SCORE_MAX` | The `[0, 1]` clamp bounds. |

Reuse note: `SCORE_MIN`, `SCORE_MAX`, `clamp_score`, `parse_judge_response`, and the `JudgeCallable` type are the conformance judge's; the eval-judge stage imports them rather than redefining (see [05-architecture.md](05-architecture.md) → §Reuse).

---

## Score → band → verdict

The continuous score is mapped to a `band` and a `PASS | FAIL`, reusing the calibration bands from [`benchmark/harness/scoring/conformance/calibration.py`](../../../benchmark/harness/scoring/conformance/calibration.py):

| Band | Range | |
|---|---|---|
| `low` | `[0, LOW_BAND_MAX)` | |
| `partial` | `[LOW_BAND_MAX, HIGH_BAND_MIN)` | |
| `high` | `[HIGH_BAND_MIN, 1.0]` | |

The verdict derives from a single named threshold:

- `PASS` when `score >= PASS_THRESHOLD`.
- `FAIL` when a `completed` run scored below `PASS_THRESHOLD`.

`PASS_THRESHOLD` is a named constant set at — and justified by — calibration (below). The verdict is **derived, never declared**: the judge returns a score, and the threshold turns it into a verdict; the judge is never asked for a PASS/FAIL directly. This is the conformance judge's discipline (score first, map second) and it keeps the threshold tunable without re-running the judge.

A `NOT_RUN` verdict comes from the run stage, not here — the judge stage only ever produces `PASS` or `FAIL`, and only for a `completed` EvalRun.

---

## Calibration

The threshold and the judge are **not taken on faith**, exactly as the conformance judge is calibrated against human labels. The eval-judge stage reuses the calibration harness pattern from `calibration.py`:

- A small, hand-authored **human-labelled sample** of `(expected_output, actual behavior) → human score` items, each label authored to the same rubric the judge applies.
- An **agreement computation** — exact-bucket agreement over the three bands, reported alongside **Cohen's kappa** (the chance-corrected figure honest for a small sample).
- A **resolved bar**: the threshold is trustworthy only when the sample has at least `MIN_CALIBRATION_SAMPLE_SIZE` labelled items and the judge's band agreement is at least `MIN_CALIBRATION_AGREEMENT`.

The seed sample is honestly small — a handful of eval judgments across a couple of skills, enough to prove the mechanism and report a real (if modest) agreement figure, not a publishable statistic. `PASS_THRESHOLD` is set against this sample and revised as the sample grows. The size needed to trust it is the calibration Open question in [00-overview.md](00-overview.md).

---

## Flow

```
EvalRun (status=completed)
   │  build rubric prompt: rubric + EXPECTED(expected_output) + ACTUAL(response, file_changes)
   ▼
JudgeCallable(prompt)  ──▶  raw model text
   │  parse_judge_response → (raw_score, rationale)   [tolerant, typed error on garbage]
   │  clamp_score(raw_score) → score
   ▼
EvalJudgment{ score, raw_score, rationale }
   │  band ← bucket_of(score)
   │  verdict ← PASS if score ≥ PASS_THRESHOLD else FAIL
   ▼
(carried into EvalResult by the report stage — see 04-report-and-cli.md)
```

A non-`completed` EvalRun never reaches the judge: its EvalResult is `NOT_RUN` with no judgment.

---

## Implementation layout

```
benchmark/
  evaljudge/
    judge/
      rubric.py      # the eval-conformance rubric + prompt builder (named headers)
      judge.py       # score_eval(expected, run, *, judge=cli) → EvalJudgment; verdict derivation
      calibration.py # human-labelled sample + agreement (reuses conformance calibration shape)
```

Shared primitives (`clamp_score`, `parse_judge_response`, `JudgeCallable`, `SCORE_MIN/MAX`, the bands) are imported from `benchmark.harness.scoring.conformance` rather than re-implemented — see [05-architecture.md](05-architecture.md).

---

## Assumptions and open questions

**Assumptions**

- An LLM judge can score behavioral fidelity to a prose `expected_output` as reliably as it scores code fidelity to a spec — the same assumption the conformance judge already rests on, applied to a behavior/expectation pair rather than a code/spec pair.
- `expected_output` blocks are specific enough to judge against (the current fixtures are — they name files, sections, verdict shapes, and refusals concretely).

**Decisions**

- *Reuse the conformance judge's primitives.* **Import `clamp_score`, `parse_judge_response`, `JudgeCallable`, the score bounds, and the bands.** They are general-purpose LLM-judge plumbing already proven and tested in the repo; forking them would create two parse/clamp implementations to keep in sync.
- *Score first, derive the verdict.* **The judge returns `[0, 1]`; a named `PASS_THRESHOLD` maps it to PASS/FAIL.** Asking the judge for a boolean throws away the gradient calibration needs and makes a borderline result unauditable. This is the conformance judge's score-then-map discipline.
- *Calibrate the threshold against human labels.* **`PASS_THRESHOLD` is justified by an agreement figure, not picked by feel.** An uncalibrated threshold is a magic number masquerading as a decision; the conformance judge's calibration harness already shows how to report the honest figure.
- *Judge the behavior, not the ideal.* **The rubric scores fidelity to `expected_output`, not the judge's own taste.** The fixture is the contract under test; a judge scoring against its own preferences would measure the wrong thing.

**Open questions**

- *Threshold value and sample size.* What `PASS_THRESHOLD` and what calibration-sample size give a trustworthy verdict (shared with [00-overview.md](00-overview.md))? Until calibrated, the threshold is a documented placeholder.
- *Rendering `file_changes` into the prompt.* How to present a large produced file tree to the judge (full contents vs. tree + excerpts) without blowing the prompt budget — settled during calibration ([02-run-stage.md](02-run-stage.md) raises the capture side of this).
- *Per-skill rubrics.* Whether one shared rubric scores every skill well, or whether some skills (a reviewer skill vs. a generator skill) warrant a tailored rubric, is open until the first calibration run shows where one rubric mis-scores.
