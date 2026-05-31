# 05 — Architecture

> **Read first:** [`docs/specs/development-guidelines.md`](../../specs/development-guidelines.md) (the repo-wide rules of the road) and [`docs/benchmark/specs/05-harness-architecture.md`](../../benchmark/specs/05-harness-architecture.md) (the benchmark harness this one reuses). This page covers only the eval-judge-specific shape under those rules — the package layout, the two injectable seams, what it reuses from the benchmark, and the schema.

This page records how the eval-judge harness is organised: where it lives, the two seams that make it testable, and the line between what it reuses and what it adds.

---

## Package home

The harness lives **under `benchmark/`**, as a sibling subpackage `benchmark/evaljudge/`. It is not a fork of the benchmark and does not extend its arms/suites; it lives there to **reuse the benchmark's conformance-judge machinery directly** ([`benchmark/harness/scoring/conformance/`](../../../benchmark/harness/scoring/conformance/), an in-process import, not a cross-package copy) and to inherit one toolchain, one test suite, and one `scripts/check.sh` gate. The two harnesses answer different questions ([00-overview.md](00-overview.md) → Non-goals) but share the LLM-judge plumbing.

```
benchmark/
  harness/                 # the existing benchmark harness (unchanged)
    scoring/conformance/   # ← REUSED: judge.py, calibration.py
  evaljudge/               # the eval-judge harness (this spec)
    __init__.py            # package surface + module→spec-section docstring
    domain.py              # EvalCase, EvalRun, EvalJudgment, EvalResult, EvalReport (01)
    discovery.py           # glob + parse + validate evals.json → EvalCase (02)
    run/
      backend.py           # RunBackend Protocol + redacted-case view (02)
      local.py             # local Docker-free claude -p run backend (02)
    judge/
      rubric.py            # eval-conformance rubric + prompt builder (03)
      judge.py             # score_eval → EvalJudgment; verdict derivation (03)
      calibration.py       # human-labelled sample + agreement (03)
    driver.py              # sweep: run → judge → aggregate, pool + caps (04)
    report.py              # EvalReport assembly + serialization + rendering (04)
    run_sweep.py           # opt-in live entrypoint (EVALJUDGE_RUN_LIVE) (04)
  tests/
    test_evaljudge_*.py    # hermetic tests (injected fakes) + opt-in live wrapper
```

The test files sit in the existing `benchmark/tests/` tree so `testpaths` and the pyright exclusions already cover them.

---

## The two injectable seams

The harness has exactly two places it touches the outside world, and both are injectable Protocols — the same dependency-inversion discipline the benchmark applies to its backends ([development guidelines](../../specs/development-guidelines.md) → Single responsibility: *"depend on abstractions, not concretions"*).

| Seam | Protocol | Live default | Test double |
|---|---|---|---|
| **Run** | `RunBackend.run(redacted_case, …) → EvalRun` | `local` backend (bounded `claude -p`, temp dir) | fake returning a canned `EvalRun` |
| **Judge** | `JudgeCallable(prompt) → str` | bounded `claude -p` (the conformance judge's `cli_judge` shape) | deterministic mock returning canned JSON |

With both seams faked, the entire pipeline — discovery, run, judge, verdict derivation, aggregation, report — runs hermetically with no model call, inside `scripts/check.sh`. With both live, it exercises real skills and a real judge under `EVALJUDGE_RUN_LIVE=1`. Nothing between the seams knows or cares which is in use. `JudgeCallable` is **the benchmark's own type**, imported, so the judge seam is literally the conformance judge's seam.

---

## Reuse — what comes from the benchmark

The judge stage is a reuse, not a rebuild. Imported from `benchmark.harness.scoring.conformance`:

- `JudgeCallable` — the injectable judge-backend type.
- `clamp_score`, `SCORE_MIN`, `SCORE_MAX` — the `[0, 1]` clamp and its bounds.
- `parse_judge_response` — the tolerant `{score, rationale}` JSON parser (first-`{` to last-`}`, typed error on garbage).
- the calibration shape — `bucket_of`, the `low/partial/high` bands, `cohens_kappa`, `compute_agreement` — reused for the eval-judge calibration sample.
- the `cli_judge` invocation pattern — bounded `claude -p --output-format json`, copied in shape (not necessarily called directly) for both the judge call and the run call.

What the eval-judge harness **adds** (its bespoke surface):

- the **run stage** — there is no analogue in the conformance judge, which scores an already-produced `(spec, code)` pair; capturing *actual skill behavior* (response + file diff) by invoking the skill live is new.
- the **eval-conformance rubric** — `expected_output` vs behavior, rather than spec vs code.
- the **fixture discovery + EvalCase shape** — reading `evals.json` across the plugin tree.
- the **report layer** — per-skill aggregation and the sweep driver.

This keeps the bespoke code to what is genuinely new and routes all the LLM-judge primitives through one home, honouring the no-duplication rule ([development guidelines](../../specs/development-guidelines.md) → No duplication).

> **Reuse boundary note.** Importing from `benchmark.harness.scoring.conformance` makes the benchmark harness a dependency of the eval-judge harness. That is acceptable because both ship in the same package under one `pyproject.toml`. If the eval-judge harness is ever extracted to its own distribution, the shared primitives move to a small shared module both import — recorded here so the coupling is a deliberate, revisitable decision, not an accident.

---

## Isolation — the run never sees the expectation

The harness inherits the benchmark's defining invariant in a new form: **the run side and the scoring side are separated, and the answer key exists only on the scoring side.** In the benchmark, the answer key is the hidden test suite; here it is the case's `expected_output`. The `RunBackend` receives a *redacted* EvalCase with `expected_output` structurally absent ([02-run-stage.md](02-run-stage.md) → The run backend), so a skill cannot be coached toward the expected answer. Without this, a skill invoked with foreknowledge of `expected_output` would overfit the check and the pass rate would mean nothing — the same overfitting the benchmark's scoring isolation exists to prevent.

---

## Conventions inherited from the repo

Nothing on this page overrides the global rules; the harness follows them:

- **Frozen dataclasses** for every entity, validated against [`canonical-types.schema.json`](canonical-types.schema.json) on construction and on load.
- **Named constants** for every limit — models, budgets, timeouts, pool size, sweep cap, the pass threshold, the calibration bars.
- **Typed exceptions** rooted in a small hierarchy (`FixtureValidationError`, a run error, the reused `ConformanceJudgeError` for judge failures); no bare `except`, no `None`-as-error.
- **Closed string sets** for `EvalRun.status`, `EvalResult.verdict`, `file_changes[].change_kind`, and `band`.
- **Determinism in tests** — clock and id generators injected; the report's `created` timestamp is passed in, never read from a wall clock inside a pure function.
- **`uv run` only**, Clean Code style, ruff + pyright + pytest green via `scripts/check.sh`.

---

## Schema

The sidecar [`canonical-types.schema.json`](canonical-types.schema.json) is the hand-authored authority every record validates against (the schema-is-authority rule). It defines `EvalCase`, `EvalRun`, `EvalJudgment`, `EvalResult`, and `EvalReport`, plus the small shared shapes they use (`Slug`, `RecordId`, `Timestamp`, the closed enums).

**Field naming — camelCase, matching the benchmark.** The schema keys are camelCase (`fileChanges`, `expectedOutput`, `rawScore`, `passRate`, `bySkill`, `changeKind`), and the dataclass field names are **identical** to them. This is not a free choice: the benchmark's `Record.to_dict` serializes each field under its own name (`out[f.name] = …`) with no snake↔camel translation layer, so reusing that discipline (which [01-domain-model.md](01-domain-model.md) commits to) requires the dataclass fields to *be* the camelCase schema keys — exactly as the benchmark's own records do (`ScoreReport.conformanceScore`, `TaskInstance.failToPass`). The snake_case names in [01-domain-model.md](01-domain-model.md)'s field bullets are a readability gloss, not the literal attribute names. A builder who named fields snake_case while reusing the `f.name`-based `to_dict` would emit snake_case keys that fail schema validation — the schema-equality and round-trip tests in the build's first task catch this, but it is called out here so it never reaches a test.

Per the layering rule ([`docs/spec-creator` §Layered structure] and [development guidelines](../../specs/development-guidelines.md)), `Slug`/`RecordId`/`Timestamp` are **re-declared** in this app's schema rather than `$ref`-ed from the benchmark's schema: a type is promoted to a global `docs/specs/canonical-types.schema.json` only once two apps genuinely share it. The eval-judge and benchmark schemas independently using a `RecordId` shape is **duplication to watch**, not yet duplication to promote — flagged in Open questions so a future editor can decide whether to lift the shared primitives to the global schema.

---

## Assumptions and open questions

**Assumptions**

- In-process import from `benchmark.harness.scoring.conformance` is the right reuse mechanism while both harnesses live in one package — no need for a separately versioned shared library yet.
- The repo's existing `pyproject.toml`, `testpaths`, and pyright config extend to `benchmark/evaljudge/` without structural change (a new subpackage under an already-included tree).

**Decisions**

- *Live under `benchmark/`, reuse in-process.* **`benchmark/evaljudge/` importing `benchmark.harness.scoring.conformance`.** The whole point is to reuse the conformance judge; a separate top-level package would put a package boundary between the harness and the machinery it exists to reuse. The extraction path is recorded in the reuse-boundary note above.
- *Two injectable seams, faked together for a hermetic suite.* **`RunBackend` and `JudgeCallable`.** Both outside-world touchpoints are Protocols so the default test path is deterministic and free, and the live path is the same code with real backends — the benchmark's proven backend-injection pattern.
- *Re-declare shared primitives, do not `$ref` across apps.* **`Slug`/`RecordId`/`Timestamp` live in this app's schema.** The layering rule promotes a type to the global schema only when two apps share it; pre-emptively coupling the two app schemas would invert that rule. The duplication is flagged for a deliberate later call.

**Open questions**

- *Promote shared schema primitives?* `RecordId`, `Slug`, and `Timestamp` now appear in both the benchmark and eval-judge schemas. Is that the two-app trigger to lift them into a global `docs/specs/canonical-types.schema.json`, or is the duplication cheaper than the coupling for now?
- *Extraction to its own distribution.* If the eval-judge harness is ever shipped independently of the benchmark, the shared conformance primitives need a home both can import. Worth doing pre-emptively, or deferred until there is a real second consumer?
