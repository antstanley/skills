# 01 — Domain Model

The entities the eval-judge harness operates on, their IDs, and the lifecycle a single eval moves through. The harness architecture that produces and consumes these records is in [05-architecture.md](05-architecture.md); the JSON Schema for every entity is the sidecar [`canonical-types.schema.json`](canonical-types.schema.json).

These records follow the repo-wide conventions: frozen dataclasses validated against the canonical schema on construction and on load, closed string sets over free strings, and named-constant ID prefixes ([`docs/specs/development-guidelines.md`](../../specs/development-guidelines.md) → Code style). They mirror the benchmark's domain-record discipline ([`docs/benchmark/specs/01-domain-model.md`](../../benchmark/specs/01-domain-model.md)).

---

## ID scheme

Generated records use a `<prefix>_<uuid7>` id, the same scheme as the benchmark (`RecordId` in the benchmark schema). The prefixes:

| Prefix | Entity |
|---|---|
| `run_` | EvalRun |
| `judg_` | EvalJudgment |
| `res_` | EvalResult |
| `rep_` | EvalReport |

An **EvalCase** is *not* generated — it is identified by its natural key `(skill, id)`, where `skill` is the fixture's `skill_name` and `id` is the integer `id` within that fixture. This key is stable across runs, so a report can be diffed case-by-case over time.

The harness reuses the benchmark's `Slug` shape for `skill` (lowercase, kebab-or-underscore) and its `RecordId` pattern for the generated ids; both are re-declared in this app's schema rather than `$ref`-ing across app boundaries, per the layering rule (a type goes to the global schema only when two apps share it — see [05-architecture.md](05-architecture.md) → §Schema).

---

## Entities

### EvalCase

One fixture read from a skill's `evals.json`. The unit of work: one case is run once and judged once, producing one `EvalResult`.

- `skill` — the fixture file's `skill_name` (a `Slug`). The skill under test.
- `id` — the integer `id` within the fixture's `evals` array. Unique within `skill`.
- `name` — the fixture's human-readable `name` (e.g. `spec-website-app`).
- `prompt` — the user-message text the run stage sends to the skill verbatim.
- `expected_output` — the prose description of correct behavior. The **judge's authority**; the run stage never receives it.
- `files` — the seed files the case needs in the working directory before the skill runs (the fixture's `files` array; empty in every current fixture, but part of the shape). Each is a `{path, contents}` pair.
- `source_path` — the `evals.json` file this case was read from, retained for provenance and error messages.

### EvalRun

What the skill actually did, captured by the run stage. The *actual behavior* the judge scores. Carries no score — it is the evidence, not the verdict.

- `id` — `run_<uuid7>`.
- `case` — the `(skill, id)` key of the EvalCase this run executed.
- `response` — the skill's final assistant message (the `result` text from the `claude -p` JSON envelope).
- `file_changes` — the observed file-system effect: a list of `{path, change_kind, contents}` where `change_kind` is one of `created | modified | deleted`. Captured by diffing the working directory after the run against its seeded state.
- `status` — `completed | run_failed | timed_out | budget_exceeded`. Only a `completed` run is judged; the others short-circuit to a `NOT_RUN` verdict in the EvalResult (see [Lifecycle](#lifecycle)).
- `telemetry` — optional cost / wall-clock / turn counts for the run, when the backend exposes them (mirrors the benchmark's `ArtifactBundle.telemetry`; optional because not every backend surfaces it).

### EvalJudgment

The judge's verdict for one `(EvalCase.expected_output, EvalRun)` pair. The same shape as the benchmark's `ConformanceResult`, by deliberate reuse.

- `id` — `judg_<uuid7>`.
- `run` — the `run_` id of the EvalRun judged.
- `score` — the conformance score in `[0, 1]`, **clamped** to the bounds. How well the actual behavior satisfies `expected_output`.
- `raw_score` — the pre-clamp value the judge returned, kept for auditing (a judge returning `1.2` is recorded, then clamped).
- `rationale` — the judge's free-text justification (may be empty if the model omitted one).

### EvalResult

The full outcome for one case: the run, the judgment, and the derived verdict. One per EvalCase.

- `id` — `res_<uuid7>`.
- `case` — the `(skill, id)` key.
- `run` — the `run_` id (or null when the run never produced a judgeable behavior).
- `judgment` — the `judg_` id (or null when not judged).
- `band` — the score's conformance band: `low | partial | high` (the benchmark's calibration bands, reused).
- `verdict` — `PASS | FAIL | NOT_RUN`. Derived, never declared: `PASS` when `score >= PASS_THRESHOLD`, `FAIL` when a `completed` run scored below it, `NOT_RUN` when the run did not complete (a `run_failed` / `timed_out` / `budget_exceeded` EvalRun, so there was no behavior to judge).

### EvalReport

The aggregate over a set of EvalResults — one sweep's output. The artifact a reviewer or CI reads.

- `id` — `rep_<uuid7>`.
- `created` — RFC3339 timestamp (passed in, never read from a wall clock inside a pure function — the determinism rule).
- `results` — the EvalResults in the sweep.
- `pass_rate` — fraction of `PASS` over all `results` (a `NOT_RUN` counts against the rate — an eval that could not run is not a pass).
- `by_skill` — pass rate broken down per `skill`, so a regression is attributable to one skill.

---

## Relationships

```
EvalCase (skill, id)              ← read from evals.json, never generated
   │ 1
   │   run stage (never sees expected_output)
   ▼ 1
EvalRun (run_)                    ← the actual behavior: response + file_changes
   │ 1
   │   judge stage (scores against EvalCase.expected_output)
   ▼ 0..1                          (absent when the run did not complete)
EvalJudgment (judg_)              ← score + rationale
   │
   ▼
EvalResult (res_)  ── 1 per EvalCase ──  { case, run?, judgment?, band, verdict }
   │ N
   ▼ 1
EvalReport (rep_)                ← results + pass_rate + by_skill
```

One EvalCase yields exactly one EvalResult. The EvalRun is always produced (even a failed run is recorded, with a non-`completed` status); the EvalJudgment exists only when the run completed and was scored. The EvalReport gathers many EvalResults.

---

## Lifecycle / state machine

A single eval moves through these states:

```
discovered ──run──▶ run_completed ──judge──▶ judged ──derive──▶ PASS | FAIL
     │                    │
     │                    └─(run_failed | timed_out | budget_exceeded)─▶ NOT_RUN
     │
     └─(malformed fixture)─▶ excluded (reported as a fixture defect, not a FAIL)
```

- **discovered** — the EvalCase was read and validated from an `evals.json`.
- **run_completed** — the run stage produced a `completed` EvalRun (response + file_changes captured).
- **judged** — the judge produced an EvalJudgment with a clamped score.
- **PASS / FAIL** — derived from `score` vs `PASS_THRESHOLD` ([03-judge-stage.md](03-judge-stage.md)).
- **NOT_RUN** — the run stage could not produce a judgeable behavior (the skill invocation failed, hit the wall-clock cap, or exceeded the budget). Distinct from `FAIL`: `FAIL` means the skill ran and behaved wrongly; `NOT_RUN` means it never ran cleanly. This mirrors the benchmark's distinction between an infra-failed Trial and a legitimate `resolved: false`.
- **excluded** — a fixture that does not validate against the eval-fixture shape (missing `prompt`, non-integer `id`, …) is a **fixture defect**, reported as such and excluded from the pass-rate denominator — not silently counted as a FAIL. The harness raises on the first malformed record on read, per the boundary-validation rule.

---

## Assumptions and open questions

**Assumptions**

- Every current `evals.json` validates against the fixture shape `{skill_name, evals: [{id, name, prompt, expected_output, files}]}`; a fixture that does not is a defect to surface, not a case to score.
- A run's file-system effect is observable by diffing the working directory against its seeded state — the skill does not write outside the working directory it is given.

**Decisions**

- *EvalCase is keyed naturally, not generated.* **`(skill, id)`.** The key must be stable across sweeps so a report diffs case-by-case; a generated id would change every run and defeat regression tracking.
- *A non-completed run is `NOT_RUN`, not `FAIL`.* **Run failure is distinct from behavioral failure.** Conflating "the skill misbehaved" with "the skill never ran" would make a CLI outage look like a skill regression. The benchmark draws the same line between an infra fault and `resolved: false`.
- *`NOT_RUN` counts against the pass rate; a malformed fixture does not.* **A skill that cannot be exercised is not passing; a broken fixture is a separate defect class.** The first is a real signal about the skill or environment; the second is a problem with the test material itself and would distort the skill's score.
- *EvalJudgment mirrors `ConformanceResult`.* **Same `score / raw_score / rationale` shape.** Reusing the benchmark judge's result record keeps the calibration tooling and the parse/clamp logic shared rather than forked. See [05-architecture.md](05-architecture.md).

**Open questions**

- *Telemetry fidelity.* Whether the `local` run backend can expose per-run token/cost counts at the same granularity as the benchmark's arms is unconfirmed — hence `EvalRun.telemetry` is optional. (The benchmark's identical open question for A0.)
- *Multi-file expected behavior.* Some `expected_output` blocks describe a whole directory tree (e.g. "numbered markdown files plus a schema sidecar"). Whether `file_changes` should be summarised (a tree listing) or passed to the judge in full when large is a judge-prompt-sizing question deferred to [03-judge-stage.md](03-judge-stage.md)'s calibration.
