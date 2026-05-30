# Task 02 — Fixture discovery

**Plan:** [plan.md](plan.md) · **Status:** Todo

**Implements:** [02-run-stage.md](../../evaljudge/specs/02-run-stage.md) §Fixture discovery
**Depends on:** 01
**Produces:** `discover_cases()` globs every `plugins/*/skills/*/evals/evals.json` in the repo, parses each, and yields validated `EvalCase` records; a malformed fixture raises a typed `FixtureValidationError` naming the file and offending entry, is reported as a fixture defect, and is excluded from scoring — not silently treated as a FAIL
**Pointers:** new `benchmark/evaljudge/discovery.py`; reads the eight real `plugins/*/skills/*/evals/evals.json`; constructs `EvalCase` from task 01; validation-at-boundary pattern from [development-guidelines.md](../../specs/development-guidelines.md) §Error handling

## Steps

- [ ] Implement `discover_cases(root, *, select=None)` that globs the fixture path under `root`, reads each `evals.json`, and yields `EvalCase` records with `source_path` set.
- [ ] Validate each file against the fixture shape `{skill_name, evals:[{id, name, prompt, expected_output, files}]}` strictly at read; raise `FixtureValidationError` (rooted in the package base exception) naming the file and the offending entry on the first malformed record, rather than best-effort parsing.
- [ ] Support the `select` filter: all, by `skill`, or by `(skill, id)`, so a single eval can be re-run in isolation.
- [ ] Distinguish a **fixture defect** (malformed → reported + excluded) from a valid case; surface defects to the caller as a separate collection, never as scored cases.
- [ ] Add `benchmark/tests/test_evaljudge_discovery.py`: discover against the real repo tree and assert all eight skills' fixtures load into `EvalCase`s; a temp fixtures tree with a malformed entry (missing `prompt`, non-integer `id`) raises `FixtureValidationError`; the `select` filter narrows correctly.

## Definition of done

- [ ] Discovery reads every real `plugins/*/skills/*/evals/evals.json` in the repo into validated `EvalCase` records (asserted against the eight known fixtures).
- [ ] Negative space: a malformed fixture raises a typed `FixtureValidationError` with file + entry context and is reported as a defect, not scored.
- [ ] The `select` filter (all / by skill / by `(skill, id)`) returns the expected subset.
- [ ] Meets the repo definition of done (tests, ruff, pyright, typed errors with context — see plan.md baseline).
- [ ] Reviewable: `uv run pytest benchmark/tests/test_evaljudge_discovery.py` is green; a reviewer runs discovery over the repo and sees the eight fixtures' cases enumerated and a planted malformed file rejected.
