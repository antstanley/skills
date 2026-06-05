# 02 — Run Stage

The run stage turns an [`EvalCase`](01-domain-model.md#evalcase) into an [`EvalRun`](01-domain-model.md#evalrun): it discovers the fixtures, invokes the skill live against a fixture's `prompt` in an isolated working directory, and captures what the skill actually did. It is the eval-judge analogue of the benchmark's `RunBackend` ([`.specs/benchmark/specs/05-harness-architecture.md`](../../benchmark/specs/05-harness-architecture.md) → Backends), and it honours the same isolation discipline: **the run stage never receives the case's `expected_output`.**

---

## Responsibilities

1. **Discover fixtures.** Find every `plugins/*/skills/*/evals/evals.json`, parse each, and yield validated `EvalCase` records.
2. **Provision an isolated working directory** per case, seeded with the case's `files`, with the target plugin installed on the path.
3. **Invoke the skill live** — one bounded `claude -p` call carrying the fixture `prompt`, with the plugin available so the skill triggers.
4. **Capture the behavior** — the final response text and the file-system diff — into an `EvalRun`.
5. **Classify the run outcome** — `completed`, or one of the non-completed statuses that short-circuit to `NOT_RUN`.

The run stage does **not** judge. It produces evidence; scoring is [03-judge-stage.md](03-judge-stage.md).

---

## Fixture discovery

Fixtures live at `plugins/<plugin>/skills/<skill>/evals/evals.json`. Discovery globs that path, reads each file, and validates it against the fixture shape:

```json
{
  "skill_name": "<slug>",
  "evals": [
    { "id": 1, "name": "<slug>", "prompt": "...", "expected_output": "...", "files": [] }
  ]
}
```

Each `evals[]` entry becomes one `EvalCase` with `source_path` set to the file. Validation is strict at this boundary (the inbound-record rule, [`.specs/development-guidelines.md`](../../development-guidelines.md) → Error handling): a file missing `skill_name`, an entry missing `prompt` or `expected_output`, or a non-integer `id` raises a typed `FixtureValidationError` naming the file and the offending entry — it is a **fixture defect** (the `excluded` state in [01-domain-model.md](01-domain-model.md#lifecycle--state-machine)), reported and excluded from the pass-rate denominator, never silently scored as a FAIL.

Discovery is filterable: a sweep may select a subset by skill or by `(skill, id)`, so a single eval can be re-run in isolation while iterating.

---

## The run backend

The run side is a **`RunBackend`** — an injectable Protocol, exactly as the benchmark separates its driver from how a trial is actually executed. This is the harness's first injectable seam (the second is the judge, [03-judge-stage.md](03-judge-stage.md)).

```
RunBackend.run(case_without_expected_output, *, budget, timeout) -> EvalRun
```

- The argument is a **redacted view** of the EvalCase — `skill`, `prompt`, and `files` only. `expected_output` is structurally absent from what the backend receives, so the isolation rule is enforced by construction, not by convention. (The benchmark enforces its run/scoring split the same way: the hidden tests are simply never mounted on the run side.)
- `budget` and `timeout` are named-constant caps (below), passed in so tests can override them.
- The return is an `EvalRun` with its `status` set from the outcome.

This spec defines one implementation:

- **`local` backend** — runs the skill in an isolated temp working directory, Docker-free, as a bounded `claude -p` subprocess. This is the benchmark's `local`-backend posture: the run needs only Python, `uv`, the `claude` CLI, and the plugin under test. It is the default and the only backend this spec requires.

A **container** backend (stronger isolation, parity with the benchmark's two-backend design) is an Open question, not specified here. The Protocol exists so it can be added without touching the judge or report stages.

For hermetic tests, a **fake `RunBackend`** returns a canned `EvalRun` for a given case — the test seam that lets the whole pipeline run with no `claude` call, exactly as the benchmark's tests inject a deterministic judge.

---

## Live invocation

The `local` backend invokes the skill with one bounded host call, mirroring the conformance judge's `cli_judge` shape ([`benchmark/harness/scoring/conformance/judge.py`](../../../benchmark/harness/scoring/conformance/judge.py)):

```
claude -p <prompt> --model <RUN_MODEL> --max-budget-usd <RUN_MAX_BUDGET_USD> --output-format json
```

run with `cwd` set to the seeded temp directory and the target plugin installed so the skill triggers. The call:

- runs **non-interactively to completion** under a wall-clock `RUN_TIMEOUT_SECONDS` cap;
- is bounded by `RUN_MAX_BUDGET_USD` (`--max-budget-usd`), so a runaway skill cannot drain budget;
- on a non-zero exit, a timeout, or a budget overspend, yields an `EvalRun` whose `status` is `run_failed` / `timed_out` / `budget_exceeded` respectively, carrying stderr context for the report — never a silent partial.

The prompt is the fixture `prompt` **verbatim**, with nothing from `expected_output` added.

### Safety / reproducibility — everything a named constant

Per the limits rule ([`.specs/development-guidelines.md`](../../development-guidelines.md) → Limits and bounds), every bound is a named constant, mirroring the conformance judge's rails:

| Constant | Meaning |
|---|---|
| `RUN_MODEL` | The fixed model alias the skill runs on (a campaign-stable choice, like `CONFORMANCE_MODEL`). |
| `RUN_MAX_BUDGET_USD` | Hard per-eval `--max-budget-usd` cap on the run call. |
| `RUN_TIMEOUT_SECONDS` | Wall-clock ceiling for one run invocation. |
| `RUN_TEMP_BASE` | Base directory for the per-case isolated working dirs (mirrors the benchmark's `RUN_TEMP_BASE`). |

A sweep-level cap on the number of eval runs is part of [04-report-and-cli.md](04-report-and-cli.md) (the cost-ceiling Open question).

---

## Capturing behavior

A `completed` run captures two things, because `expected_output` blocks assert on both:

1. **`response`** — the final assistant message, read from the `claude --output-format json` envelope's `result` field (the same envelope the conformance judge parses). Used for evals whose expectation is about what the skill *says* or the structure it emits (e.g. "ends with a `VERDICT:` block", "states which template it is applying").
2. **`file_changes`** — the file-system effect, computed by snapshotting the working directory after seeding and again after the run, then diffing: each changed path becomes a `{path, change_kind, contents}` record (`created | modified | deleted`). Used for evals whose expectation is about what the skill *produces* (e.g. "a new directory `.specs/website/specs/` with numbered markdown files plus a `canonical-types.schema.json` sidecar").

Both are carried on the `EvalRun` and handed to the judge together, so the judge can check a fixture that asserts on response *and* files (most `spec-creator` evals do).

The cleanup of the temp working directory happens in a `finally`, per the resource-handling rule — a crashed run never leaks a working directory.

---

## Flow

```
for each EvalCase (expected_output withheld):
    seed temp dir ← case.files
    EvalRun ← RunBackend.run({skill, prompt, files}, budget, timeout)
        ├─ exit 0      → status=completed,  capture response + file_changes
        ├─ exit ≠ 0    → status=run_failed       (stderr retained)
        ├─ over time   → status=timed_out
        └─ over budget → status=budget_exceeded
    (cleanup temp dir in finally)
    yield EvalRun  →  judge stage
```

---

## Implementation layout

```
benchmark/
  evaljudge/
    discovery.py     # glob + parse + validate evals.json → EvalCase records
    run/
      backend.py     # RunBackend Protocol + the redacted-case view
      local.py       # the local (Docker-free) claude -p run backend
    domain.py        # EvalCase, EvalRun, … (see 01-domain-model.md)
```

(The full package layout, including the judge and report stages, is in [05-architecture.md](05-architecture.md).)

---

## Assumptions and open questions

**Assumptions**

- The target plugin can be made available to a `claude -p` call so the skill triggers on the fixture prompt — the same install-the-plugin step the benchmark's arms perform in-container, done here in a local working directory.
- The skill's file-system effects land inside the working directory the run is given, so a before/after diff captures them faithfully.

**Decisions**

- *The backend receives a redacted case.* **`expected_output` is structurally absent from the run input.** Enforcing the isolation rule by the shape of the argument — not by a "please don't peek" convention — is the benchmark's lesson: the run side cannot leak what it never holds.
- *One bounded `claude -p` call per run, every bound named.* **Mirror the conformance judge's `cli_*` shape.** The pattern (bounded subprocess, JSON envelope, typed error on non-zero exit) is already proven in the repo; the run stage reuses it rather than inventing a second invocation style.
- *Capture response and file changes both.* **The judge needs both because fixtures assert on both.** Capturing only the transcript would fail every `spec-creator` eval whose expectation is a produced directory tree; capturing only files would fail a `semi-formal-review` eval whose expectation is a verdict block in the response.
- *`local` backend only, Protocol for more.* **Docker-free by default; a container backend is deferred behind the Protocol.** The repo's development posture is Docker-free for everything but the benchmark's `container` path; a skill-behavior check does not obviously need a container, so the cost is deferred to the Open question.

**Open questions**

- *Container backend.* Is stronger per-eval isolation (a container with the plugin baked in) worth the Docker cost, or is a temp-dir subprocess sufficient for behavior capture? (Shared with [00-overview.md](00-overview.md).)
- *Plugin install mechanics.* The exact non-interactive way to make a local plugin available to `claude -p` (a `--plugin-dir`-style flag, a marketplace install, or a config shim) is an implementation detail to pin at build time in the target environment.
- *Large file outputs.* When a skill writes many or large files, whether to hand the judge the full `file_changes` contents or a summarised tree + selected excerpts is a prompt-sizing decision settled during judge calibration ([03-judge-stage.md](03-judge-stage.md)).
