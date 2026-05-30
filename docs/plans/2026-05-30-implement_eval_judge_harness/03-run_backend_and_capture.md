# Task 03 — Run backend and behavior capture

**Plan:** [plan.md](plan.md) · **Status:** Todo

**Implements:** [02-run-stage.md](../../evaljudge/specs/02-run-stage.md) §The run backend, §Capturing behavior; [05-architecture.md](../../evaljudge/specs/05-architecture.md) §The two injectable seams, §Isolation
**Depends on:** 01
**Produces:** the `RunBackend` Protocol, the **redacted-case** view that structurally omits `expected_output`, and the behavior-capture logic (final response + working-directory file diff → `EvalRun`); plus a fake `RunBackend` that returns a canned `EvalRun` so the pipeline runs hermetically
**Pointers:** new `benchmark/evaljudge/run/backend.py`, `benchmark/evaljudge/run/__init__.py`; Protocol/injection pattern from `benchmark/harness/backends/interfaces.py`; constructs `EvalRun`/`FileChange` from task 01

## Steps

- [ ] Define the `RunBackend` Protocol: `run(redacted_case, *, budget, timeout) -> EvalRun`.
- [ ] Define the **redacted-case** view — a value object carrying only `skill`, `prompt`, and `files` — and a function that derives it from an `EvalCase`, so `expected_output` is structurally absent from what any backend receives (the isolation rule enforced by shape, not convention).
- [ ] Implement working-directory capture: snapshot the seeded directory, run, snapshot again, diff into `FileChange` records (`created`/`modified`/`deleted`); pair with the response text to build the `EvalRun`.
- [ ] Implement a `FakeRunBackend` returning a configured `EvalRun` for a given case (the hermetic test seam), including configurable non-`completed` statuses.
- [ ] Add `benchmark/tests/test_evaljudge_run_backend.py`: assert the redacted-case view has no `expected_output` attribute/key (the isolation guard); the file-diff capture classifies created/modified/deleted correctly against a temp dir; the fake backend drives an `EvalRun` end to end.

## Definition of done

- [ ] The `RunBackend` Protocol and redacted-case view exist; the view structurally omits `expected_output` (asserted by a test that would fail if the field leaked in).
- [ ] Behavior capture turns a working-directory before/after into `FileChange` records plus the response into a `completed` `EvalRun`.
- [ ] The `FakeRunBackend` produces both `completed` and non-`completed` `EvalRun`s for tests downstream.
- [ ] Negative space: a non-`completed` status is representable and carries no judgeable response (the path 07 turns into `NOT_RUN`).
- [ ] Meets the repo definition of done (tests, ruff, pyright, Protocol over concretion — see plan.md baseline).
- [ ] Reviewable: `uv run pytest benchmark/tests/test_evaljudge_run_backend.py` is green; a reviewer confirms the isolation guard test fails if `expected_output` is added to the redacted view.

## Open questions

- Exactly how `file_changes` contents are bounded for very large outputs is a judge-prompt-sizing concern settled in task 05/06, not here; this task captures faithfully and leaves rendering to the judge.
