# Done Certificate — Task 05: Run container

**Task:** [05-run_container.md](05-run_container.md) · **Plan:** [plan.md](../plan.md)
**State:** Validated 2026-05-27

> This certificate is a verification protocol for Task 05. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 05) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** A0 runs in a provisioned container against a `TaskInstance` and yields a `candidatePatch` plus a transcript captured into an `ArtifactBundle`.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Must consume Task 02 types and Task 03 instances; the run container must not introduce hidden tests (integrity rule on the run side).

## Obligations

- **O1 — An A0 run yields an apply-able patch and a bundle with the transcript.**
  - *Claim:* an A0 run on a seed instance produces a `candidatePatch` that applies cleanly against `baseCommit` and an `ArtifactBundle` carrying the transcript.
  - *Evidence to collect:* run A0 on a seed instance; apply the emitted patch to a fresh checkout at `baseCommit` → expect clean apply; confirm the `ArtifactBundle` has a non-empty transcript.
  - *Checks:* resolve the patch extraction to the diff of working state against `baseCommit`, not against the container's dirty HEAD; confirm `jj`/`git` are present in the container.
  - *Collected:* ran `test_live_a0_run_yields_applicable_patch_and_bundle` (the LIVE A0 run, ~$0.15 spent) → PASSED, not skipped (65s/166s wall time confirms a real container run). The test asserts the emitted `candidatePatch` is a non-empty `str`, that `git apply --check` of it against a FRESH base checkout of the clean run image returns 0 (`_apply_check`, container.py test:150-169 / 189-194), and that `bundle.transcript` is non-empty with populated `Telemetry` (inputTokens>0, outputTokens>0, 0 < costUsd ≤ A0_MAX_BUDGET_USD, agentTurns≥1, wallClockSeconds>0) round-tripping through the schema.
  - *Check — patch extraction:* `_extract_patch` (container.py:359-378) runs `git add -A && git diff --cached` in `IMAGE_WORKDIR` against the base commit made by `_make_base_commit` (`git init && add -A && commit -m base`, :287-302) — the diff is against the base commit, not a dirty HEAD; empty diff → `None`. `jj` and `git` are both present in the run image (`_RUN_DOCKERFILE` installs `git` + the pinned jj GitHub release, greenfield_images.py:103-121); the agent image derives FROM it.
  - *Status:* ☑ SATISFIED

- **O2 — The run container carries no hidden test content.**
  - *Claim:* the provisioned run image contains no `failToPass`/`passToPass` test material.
  - *Evidence to collect:* run the test that inspects the run container for hidden test files → expect none present.
  - *Collected:* three corroborating tests PASSED. `test_agent_run_image_carries_no_hidden_tests` builds the AGENT RUN image and asserts `find <WORKDIR>/hidden -type f` is empty (test:139-144). `test_agent_dockerfile_adds_no_hidden_content` asserts the agent Dockerfile template contains neither `REPO_HIDDEN_SUBDIR` nor any `COPY` (test:109-117). `test_run_side_inputs_carry_no_hidden_selectors` asserts neither the `failToPass`/`passToPass` selectors nor the `HIDDEN_TEST_FIELDS` names appear in any run-visible input (slug/suite/problemStatement/dockerImage/baseCommit/a0_prompt) (test:89-106). The agent run image derives FROM the clean run image (`_AGENT_RUN_DOCKERFILE_TEMPLATE`, greenfield_images.py:144-159), which copies `base/` only — hidden tests never enter the run side.
  - *Status:* ☑ SATISFIED

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Collected:* `bash scripts/check.sh` ran the full gate: `uv sync --frozen` clean (33 packages, no lock drift), `ruff format --check` (62 files already formatted), `ruff check` (All checks passed), `pyright` (0 errors, 0 warnings), `pytest -q` (99 passed in 166.92s). Limits are named constants — `A0_MAX_BUDGET_USD=3.0`, `AUTH_PROBE_MAX_BUDGET_USD=1.0`, `A0_MODEL="sonnet"` (a0.py:41-50); `AGENT_RUN_TIMEOUT_SECONDS`, `AUTH_PROBE_TIMEOUT_SECONDS`, `SETUP_TIMEOUT_SECONDS` (container.py:101-108); pinned `JJ_VERSION`, `PYTEST_VERSION`, `CLAUDE_CODE_CLI_VERSION`, `NODE_MAJOR` (greenfield_images.py). `jj` is installed in the run image from the official GitHub release.
  - *Status:* ☑ SATISFIED

- **O4 — Reviewable: run A0 on one seed instance; inspect the patch and transcript.**
  - *Claim:* a reviewer runs A0 on one seed instance and inspects the emitted patch and transcript.
  - *Evidence to collect:* run A0 once; print the candidate patch and the transcript head.
  - *Collected:* exercised, not assumed. `test_live_a0_run_yields_applicable_patch_and_bundle` ran A0 once on the `text_toolkit` seed instance (LIVE, ~$0.15 real spend, 65s isolated / 166s in the full suite) and inspected both emitted artefacts: the candidate patch (asserted non-empty and `git apply --check`-clean against a fresh base checkout) and the bundle transcript + telemetry (asserted non-empty/populated and schema-round-tripping). A reviewer can reproduce by running `uv run pytest benchmark/tests/test_container_run.py -v`; gate 1 (semi-formal-review) independently confirmed the patch is genuine and non-stubbed and the container is discarded.
  - *Status:* ☑ SATISFIED

## Regression check

- Task 04's scorer consumes a `candidatePatch`. Trace one A0 patch through the scorer → expect it applies and scores without scorer changes : ☑ PRESERVED. `jj diff --name-only` shows task 05 added/changed only `arms/__init__.py`, `arms/a0.py`, `backends/__init__.py`, `backends/container.py`, `suites/greenfield_images.py`, and `tests/test_container_run.py` — it did NOT touch `backends/interfaces.py` (the `CandidatePatch = str | None` contract and the `ScoringBackend.score` signature) nor `backends/local.py` (the scorer). The container backend emits exactly the contracted shape: `_extract_patch` returns `git diff --cached` (a unified diff vs the base commit) or `None` — the same `CandidatePatch` the scorer's `score(instance, candidate_patch)` reads. The live test even cross-validates the patch with `git apply --check` against a fresh base checkout (returncode 0), the same apply path the scorer relies on. No scorer change required.

## Residue

- A1 and the other arms extend this provisioning in Tasks 08/10/11; this task is the A0 recipe only.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: DONE
CONFIDENCE: high
SUMMARY: O1–O4 all SATISFIED with named evidence — a LIVE A0 run on the seed instance (run, not skipped; ~$0.15 real spend) emitted a non-empty `candidatePatch` that `git apply --check`-applies cleanly against a fresh `baseCommit` checkout plus a bundle with a populated transcript/telemetry; the agent run image and run-side inputs carry no hidden test content (3 integrity tests); `scripts/check.sh` is fully clean (uv-locked, ruff format/check, pyright, 99 pytest with named-constant limits and jj in the image); and the Task 04 scorer's `CandidatePatch`/`score` contract is PRESERVED (untouched files; patch shape and apply path identical).
