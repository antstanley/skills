# Done Certificate — Task 04: Scoring oracle

**Task:** [04-scoring_oracle.md](04-scoring_oracle.md) · **Plan:** [plan.md](../plan.md)
**State:** Validated 2026-05-27

> This certificate is a verification protocol for Task 04. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 04) ≡ every obligation O1…O5 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** A clean-container `ScoringBackend` that applies a candidate patch, injects hidden tests, and returns a `ScoreReport` (`resolved`, `regressed`) under the `greenfield-hidden-tests` convention, proven on a greenfield reference solution and proven to keep hidden tests off the run side.
- **P2 — Obligations.** Done iff O1…O5 all hold; O5 is the Reviewable item.
- **P3 — Invariants.** Must consume Task 02 types and Task 12 greenfield instances (including the self-test instance's private reference solution); the integrity rule (hidden tests only in scoring) is the spec's central invariant and must hold; the resolved/regressed verdict comes from the shared `resolution.py` rule, not a re-implementation.

## Obligations

- **O1 — Reference solution resolves; no-op patch does not.**
  - *Claim:* feeding the greenfield self-test instance's private reference solution yields `resolved: true`; an empty patch yields `resolved: false` without crashing.
  - *Evidence to collect:* run the oracle on the self-test instance with the reference solution → expect `resolved: true`; run with a no-op patch → expect `resolved: false`. Read the resolution rule: all `failToPass` pass AND all `passToPass` hold.
  - *Checks:* resolve the test-run invocation to the `greenfield-hidden-tests` oracle convention against the scoring image (hidden tests included, from Task 12); the reference solution is read from the suite directory, never from the arms-visible `goldPatch` field.
  - *Status:* SATISFIED — Ran `test_reference_resolves_and_noop_does_not` live (Docker rebuilt after `docker rmi greenfield-*`) → PASS: `reference.resolved is True`, `reference.regressed is False`, all fail/passToPass results True; `noop = score(instance, None)` → `resolved is False`, not all failToPass pass, `regressed is False`, no crash. The test feeds `load_reference_solution(TEXT_TOOLKIT_SLUG)` which reads `reference/solution.patch` from the suite dir (`greenfield.py:384-399`); `goldPatch=None` (`greenfield.py:368`), never read. The container runs each selector via the `greenfield-hidden-tests` convention against `scoring_image_tag` (hidden suite baked at `<WORKDIR>/hidden`, built by `build_scoring_image`, Task 12). `derive_resolved` (`resolution.py:20-24`) = all failToPass pass AND all passToPass hold.

- **O2 — Scoring runs in a separate container and hidden tests are absent from the run side.**
  - *Claim:* the scoring container is distinct from any run container, and run-side inputs carry no hidden test selectors/bodies.
  - *Evidence to collect:* read the scorer's container provisioning — confirm a fresh container per scoring; run the test asserting run-side inputs contain no `failToPass`/`passToPass` content.
  - *Status:* SATISFIED — Read `container.py:174-202`: `_selector_passes` starts a FRESH `docker run --rm -i <scoring-image> sh -c ...` per selector — a distinct ephemeral container, not any run container; the hidden suite is baked into the scoring image, never fetched from a run side. Ran `test_run_side_inputs_carry_no_hidden_selectors` → PASS: none of `instance.failToPass`/`passToPass` selectors, nor the `HIDDEN_TEST_FIELDS` names, appear in the run-visible blob (slug/suite/problemStatement/dockerImage/baseCommit). Also ran the Docker-gated `test_run_image_carries_no_hidden_tests` live → PASS: the rebuilt RUN image has zero files under `<WORKDIR>/hidden` (`_RUN_DOCKERFILE` copies `base/` only; only `_SCORING_DOCKERFILE` overlays `hidden/`).

- **O3 — Verdict is single-sourced through `resolution.py`.**
  - *Claim:* the container scorer derives `resolved`/`regressed` from the same `benchmark/harness/scoring/resolution.py` rule the `local` backend uses, so the definition is not duplicated per backend.
  - *Evidence to collect:* resolve the scorer's verdict derivation to a call into `resolution.py` (the M0 module), not an inline re-implementation; confirm by reading the call site.
  - *Status:* SATISFIED — `container.py:45-48` imports `derive_resolved`/`derive_regressed` from `benchmark.harness.scoring.resolution`; `score` (`container.py:141-142`) sets `resolved=derive_resolved(...)`, `regressed=derive_regressed(...)` — no inline rule. `local.py:57-60,138-139` imports and calls the SAME two functions. Resolution via function-resolution: both names resolve (step-4 import) to `resolution.py:20,27`, the single M0 definition — no shadow, no duplication. `test_container_backend_uses_shared_resolution_rule` asserts `container_mod.derive_resolved is scoring_resolution.derive_resolved` (and regressed) → PASS, confirming object identity.

- **O4 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* SATISFIED — `bash scripts/check.sh` clean: `uv sync` ok, `ruff format --check` 59 files formatted, `ruff check` all passed, `pyright` 0 errors, `pytest` 91 passed (89s). `uv sync --frozen` → exit 0 (lockfile in sync, no resolution drift). Named-constant limits present in `container.py`: `SCORE_CONTAINER_TIMEOUT_SECONDS = 300`, `_PYTEST_EXIT_OK = 0`, command templates — no magic numbers.

- **O5 — Reviewable: score the reference solution (resolved) and a no-op (not resolved); inspect run-side has no hidden tests.**
  - *Claim:* a reviewer scores both patches on the greenfield self-test instance and inspects that run-side inputs carry no hidden tests.
  - *Evidence to collect:* run the two scorings on the self-test instance and print the `ScoreReport`s; inspect the run-side input bundle for absence of hidden tests.
  - *Status:* SATISFIED — Exercised, not assumed: the reference and no-op scorings both ran live in `test_reference_resolves_and_noop_does_not` (reference `ScoreReport` resolved/not-regressed; no-op `ScoreReport` not-resolved/not-regressed) on the self-test instance (`TEXT_TOOLKIT_SLUG`). Run-side absence of hidden tests inspected via `test_run_side_inputs_carry_no_hidden_selectors` (input fields) and the Docker-gated `test_run_image_carries_no_hidden_tests` (rebuilt run image has no `hidden/` files) — both PASS. Bonus: `test_container_and_local_agree_on_reference_solution` PASS confirms container/local verdict parity (the carried-over open question resolves to "parity holds").

## Regression check

No existing callers yet — the scorer is consumed by the driver in Task 07. Confirm Task 12's greenfield instances load unchanged into the scorer, and the shared `resolution.py` rule still passes its M0 tests after this task wires the container scorer to it : PRESERVED — `uv run pytest -k "resolution or greenfield"` → 15 passed, 0 failed. The diff adds `container.py` and its tests, extends `scoring/__init__.py` exports (additive), and adds a baked `pytest` to the SCORING Dockerfile only (the RUN Dockerfile stays pytest-free, verified by `test_scoring_image_bakes_a_pinned_pytest` and the rebuilt-image test). No edit to `resolution.py`, `local.py`, the `TaskInstance` builder, or the run image. Greenfield instances load unchanged into the new scorer; the M0 resolution rule is reused by identity, not re-implemented.

## Residue

- This task implements the `greenfield-hidden-tests` oracle convention only. The `swe-bench-pro` convention was removed from the canonical spec (2026-05-27) and is out of scope; re-adding it is a separate change spec.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: DONE
CONFIDENCE: high
SUMMARY: O1–O5 all SATISFIED with live evidence — reference resolves and no-op does not on the rebuilt self-test scoring image, scoring runs in a fresh per-selector container with hidden tests provably off the run side (input fields and rebuilt run image), the verdict is single-sourced through `resolution.py` by object identity, the repo DoD is clean (`uv sync --frozen` ok, 91 tests pass, ruff/pyright/format clean, named limits), and the reviewable two-scoring + run-side inspection (plus container/local parity) was exercised live; regression surface PRESERVED.
