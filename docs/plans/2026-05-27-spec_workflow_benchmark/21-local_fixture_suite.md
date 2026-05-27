# Task 21 — Local-fixture suite

**Plan:** [plan.md](plan.md) · **Status:** Done · **Certificate:** [certificates/21-local_fixture_suite.md](certificates/21-local_fixture_suite.md)

**Implements:** [changes/2026-05-27-local_backends.md](../../benchmark/specs/changes/2026-05-27-local_backends.md) §Proposed changes (`03-task-suites.md` → Suite: `local-fixture`)
**Depends on:** 18, 20
**Produces:** the bundled `local-fixture` instance — a small repo, a hidden `pytest` suite, and a gold patch — as a validated `TaskInstance` scorable by the local `ScoringBackend`
**Pointers:** `benchmark/suites/local-fixture/`; the local `ScoringBackend` from task 20

## Steps

- [x] Author a tiny repo at a fixed commit with a hidden `pytest` suite and a `goldPatch` that makes the suite pass.
- [x] Create the `TaskInstance`: `kind: local-fixture`, `oracleConvention: local`, `dockerImage: null`, `contaminationTier: authored-private`, with `failToPass` selectors and any `passToPass` smoke tests. (kind/oracleConvention carried on the Suite per schema; instance carries `suite: local-fixture`.)
- [x] Confirm the local `ScoringBackend` (task 20) scores the `goldPatch` as resolved and a no-op patch as not resolved.
- [x] Add a test that the fixture loads and validates and needs no Docker or network.

## Definition of done

- [ ] The fixture `TaskInstance` validates, and the local `ScoringBackend` scores its `goldPatch` resolved and a no-op not resolved.
- [ ] The suite runs with no Docker and no network access.
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer loads the fixture and scores its gold patch through the local backend and sees `resolved: true`.

## Open questions

- Whether one fixture instance suffices, or a few are needed to exercise the scorer's branches (resolvable, not-resolvable, regression) — shared with the change spec's *Fixture suite breadth* question.
