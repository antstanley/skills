# 04 — Report and CLI

How a sweep is invoked, how its [`EvalResult`](01-domain-model.md#evalresult)s aggregate into an [`EvalReport`](01-domain-model.md#evalreport), and how the harness sits relative to the repo's check gate. This is the harness's outermost layer — the part an operator or CI actually calls.

---

## Responsibilities

1. **Drive a sweep** — discover the selected `EvalCase`s, run each through the run stage ([02-run-stage.md](02-run-stage.md)) then the judge stage ([03-judge-stage.md](03-judge-stage.md)), and collect one `EvalResult` per case.
2. **Aggregate** the results into an `EvalReport` with an overall and per-skill pass rate.
3. **Emit** the report as a structured artifact and a human-readable summary.
4. **Set exit status** so CI or an operator can gate on the outcome.

---

## The driver

The sweep driver is the eval-judge analogue of the benchmark's driver/scheduler ([`docs/benchmark/specs/05-harness-architecture.md`](../../benchmark/specs/05-harness-architecture.md)). It expands a selection into cases and walks each through the two stages:

```
select cases (all, or filtered by skill / (skill,id))
   for each EvalCase:
       EvalRun     ← run stage   (redacted case; never sees expected_output)
       if EvalRun.status == completed:
           EvalJudgment ← judge stage (expected_output vs behavior)
           verdict      ← PASS | FAIL   (score vs PASS_THRESHOLD)
       else:
           verdict      ← NOT_RUN
       EvalResult ← { case, run, judgment?, band, verdict }
   EvalReport ← aggregate(EvalResults)
```

Independent cases may run **concurrently up to a configured pool size** (`DEFAULT_POOL_SIZE`, mirroring the benchmark driver) — each case is independent by construction (its own temp working directory, its own bounded calls). A **sweep-level cap** (`MAX_EVALS_PER_SWEEP`, a named constant) bounds how many eval runs one invocation will launch, the backstop against an accidental full-marketplace sweep draining budget; when discovery exceeds it the driver reports what it dropped rather than silently truncating (the no-silent-cap rule).

A run-stage or judge-stage error on one case **degrades that case**, not the sweep: the case records a `NOT_RUN` (run failure) or a surfaced judge error, and the sweep continues. One skill's broken eval never aborts the others.

---

## The EvalReport artifact

The report is a structured record (validating against the schema sidecar) plus a rendered summary.

- **Structured form** — the `EvalReport` serialized to JSON: `id`, `created`, the `results` array (each a full `EvalResult` with its score, band, verdict, and rationale), `pass_rate`, and `by_skill`. This is the machine-readable, diffable artifact; a later sweep's report diffs against an earlier one case-by-case on the `(skill, id)` key.
- **Rendered summary** — a compact human table: one row per case (`skill · id · name · score · band · verdict`), grouped by skill with a per-skill pass rate, and an overall pass rate line. Failures and `NOT_RUN`s sort to the top so a regression is the first thing read.

The `pass_rate` counts `PASS` over all judged-or-run cases; a `NOT_RUN` counts against it (an eval that could not run is not passing), while an `excluded` malformed fixture is reported separately and is **not** in the denominator ([01-domain-model.md](01-domain-model.md#lifecycle--state-machine)).

A sweep that runs live also **saves its report** under a known evidence path, the way the benchmark saves its live evidence bundles (`benchmark/tests/_*_live_evidence/`), so a green sweep's judgments can be inspected offline without paying to re-run.

---

## The entrypoint and gate posture

The harness is **opt-in and live**, never part of the default hermetic gate. Invoking skills and the judge spends model budget and needs an authenticated `claude` CLI — the same reason the benchmark's container and conformance self-tests are gated behind `BENCHMARK_RUN_*_LIVE=1` and skipped by `scripts/check.sh`.

- **Entrypoint** — a module entrypoint under the package (e.g. `benchmark/evaljudge/run_sweep.py`), runnable via `uv run`, mirroring `benchmark/harness/run_container_check.py`. It takes the selection (all / by skill / by case) and the caps, runs the sweep, writes the report, and sets exit status.
- **Default test path is hermetic.** The pytest suite exercises discovery, the pipeline wiring, aggregation, verdict derivation, and the report shape using an **injected fake `RunBackend` and fake `JudgeCallable`** — no `claude` call, fully deterministic, runs inside `scripts/check.sh` like every other test.
- **Opt-in live path.** A default-skipped pytest wrapper gated on `EVALJUDGE_RUN_LIVE=1` (the eval-judge counterpart of `BENCHMARK_RUN_CONTAINER_LIVE`) runs a real bounded sweep over a small selection, asserts the report shape and a `[0, 1]` score with a non-empty rationale, and refreshes the saved evidence. CI never pays its cost.
- **Exit status** — the entrypoint exits non-zero when any case is `FAIL` or `NOT_RUN` (configurable: a `--allow-not-run` posture treats environment-caused `NOT_RUN`s as non-fatal while still failing on a real `FAIL`), so the live path can gate a release when an operator chooses to run it.

---

## Flow

```
uv run -m benchmark.evaljudge.run_sweep  [--skill S | --case S:ID]  [--caps]
   │  (live; needs EVALJUDGE_RUN_LIVE + an authenticated claude CLI)
   ▼
driver: discover → (run → judge)* → aggregate
   ▼
EvalReport ──┬─ JSON artifact (saved under the evidence path)
             ├─ rendered summary table (failures first)
             └─ exit status (non-zero on FAIL / NOT_RUN per posture)
```

---

## Implementation layout

```
benchmark/
  evaljudge/
    driver.py        # sweep over selected cases: run → judge → aggregate, pool + caps
    report.py        # EvalReport assembly + JSON serialization + summary rendering
    run_sweep.py     # the opt-in live entrypoint (EVALJUDGE_RUN_LIVE), exit status
```

(The full package tree is in [05-architecture.md](05-architecture.md).)

---

## Assumptions and open questions

**Assumptions**

- CI runs `scripts/check.sh`, which stays hermetic; the live sweep is an operator- or release-time step, not a per-push gate — matching how the benchmark's live verification is positioned.
- A saved report under the evidence path is an acceptable zero-cost regression surface for review between live runs (the benchmark already relies on saved live evidence the same way).

**Decisions**

- *Opt-in and live, never in the default gate.* **Gated behind `EVALJUDGE_RUN_LIVE=1`; the hermetic tests use injected fakes.** Skill invocation and judging cost money and need a live CLI; forcing that into `scripts/check.sh` would make the gate slow, flaky, and expensive. The benchmark's `BENCHMARK_RUN_*_LIVE` split is the precedent.
- *One case's failure degrades that case, not the sweep.* **Run/judge errors are recorded and the sweep continues.** A full sweep is valuable precisely when something regressed; aborting on the first failure would hide every other result.
- *`NOT_RUN` fails the gate by default, with an opt-out.* **An eval that could not run is not a pass.** The default exit status treats it as a failure so an environment problem is visible, but `--allow-not-run` lets an operator distinguish "the skill misbehaved" from "the CLI was down" when gating a release.
- *Save the report as evidence.* **A live sweep writes its report under a known path.** Mirrors the benchmark's saved live-evidence bundles so judgments are inspectable offline and a sweep need not be re-run to review what it found.

**Open questions**

- *Sweep budget ceiling.* What `MAX_EVALS_PER_SWEEP` and per-eval caps keep a full marketplace sweep affordable, and should the driver support a sampled subset by default (shared with [00-overview.md](00-overview.md))?
- *Report diffing.* Whether the harness should ship a report-vs-report differ (case-by-case verdict deltas across two sweeps) or leave that to an external tool is open until there is a second saved report to diff against.
- *Trend storage.* Whether saved reports accumulate as a time series (to watch a skill's pass rate over edits) or each sweep overwrites the last is deferred until the harness has run often enough to want a trend.
