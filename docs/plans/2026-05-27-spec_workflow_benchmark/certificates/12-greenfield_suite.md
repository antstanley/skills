# Done Certificate — Task 12: Greenfield suite

**Task:** [12-greenfield_suite.md](../12-greenfield_suite.md) · **Plan:** [plan.md](../plan.md)
**State:** Validated 2026-05-27

> This certificate is a verification protocol for Task 12. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 12) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** The greenfield instances and the two-image build (run image with hidden tests excluded, scoring image with them included), plus a private reference solution for a self-test instance — the data and images the container backends (Tasks 04, 05) provision against. Greenfield is the sole ablation suite.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Uses Task 02 `TaskInstance`; the container scorer (Task 04) and runner (Task 05) depend on this task, not the reverse; the integrity rule (hidden tests off the run side) must hold by construction in the two-image split.

## Obligations

- **O1 — Greenfield instances validate; hidden tests absent from run image, present in scoring image.**
  - *Claim:* the greenfield instances load as validated `TaskInstance` records (`goldPatch: null`, `contaminationTier: authored-private`), and a test asserts the run image has no hidden tests while the scoring image does.
  - *Evidence to collect:* load the suite → expect validated `TaskInstance` records; run the two-image test → expect run image clean, scoring image carries the hidden suite.
  - *Checks:* confirm the run image build excludes the test layer; confirm each row validates against the Task 02 canonical schema.
  - *Status:* SATISFIED — `load_instances()` returns both instances as validated `TaskInstance` records with `goldPatch=None` and `contaminationTier="authored-private"` (`test_instance_loads_and_validates` PASS for both slugs; `TaskInstance.from_dict(inst.to_dict()) == inst` round-trip holds). Two-image test `test_run_image_excludes_hidden_scoring_image_includes` ran LIVE against Docker (PASSED, not skipped): the run image (`greenfield-…:run`) build context copies `repo/base/` only — `find /workspace/hidden` returns no files — while the scoring image overlays `repo/hidden/` and carries the full withheld suite. Schema validation is by construction (`TaskInstance(...)` validates on build).

- **O2 — Seed instances are multi-component, carry `testTags`, and one ships a private reference solution.**
  - *Claim:* each seed instance's spec names several dependent components and `testTags` maps hidden tests to spec sections; at least one self-test instance ships a private reference solution in the suite directory, not in the arms-visible `goldPatch` field.
  - *Evidence to collect:* read a seed instance's spec seed → expect ≥2 dependent components; read its `testTags` → expect a test→section mapping; locate the self-test instance's reference solution and confirm it is outside the `goldPatch` field (which stays `null`).
  - *Status:* SATISFIED — both seed instances are 4-component (`text_toolkit`: tokenizer→normalizer→frequency→pipeline, a dependency chain with width+depth; `scheduler`: graph→topo/validators→scheduler). Each instance's `testTags` maps every one of its 15 hidden `failToPass` selectors to a component, with `set(testTags) == set(failToPass)` and `set(testTags.values()) == set(components)` (`test_instances_are_multi_component`, `test_testTags_cover_every_hidden_selector` PASS). The self-test instance `greenfield__text_toolkit__0001` ships `reference/solution.patch` — a genuine multi-file diff replacing the four `NotImplementedError` stubs (`patch.count("diff --git") == 4`) — loaded only via `load_reference_solution()`; `goldPatch` stays `None` and the patch is never in any arms-visible field (`test_self_test_instance_ships_private_reference_outside_arms_fields` PASS).

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline); instances validate against the schema.
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean; confirm greenfield instances validate as `TaskInstance` records.
  - *Status:* SATISFIED — `bash scripts/check.sh` is fully green on the committed (clean) tree: `uv sync --frozen` clean (33 packages), `ruff format --check` (57 files formatted), `ruff check` (All checks passed), `pyright` (0 errors), `pytest -q` (84 passed, incl. both Docker-gated tests live). Named constants used throughout (`MIN_COMPONENTS`, `BASE_COMMIT`, `CONTAMINATION_TIER`, `RUN_IMAGE_TAG_TEMPLATE`, `IMAGE_WORKDIR`, etc.); no magic literals. Note: the working tree initially carried stray `cpython-39` `.pyc` artifacts under `…/text_toolkit/__pycache__/` (NOT jj-tracked — absent from `jj status`/`jj file list`; from an external Python 3.9 run), which made `test_repo_layout_splits_base_and_hidden` raise `UnicodeDecodeError` on first invocation. These are not part of the committed implementation; with them removed the suite is green and pytest does not regenerate `.pyc` in the source tree (LocalScoringBackend copies to a tempdir). Latent fragility flagged in summary, not an obligation failure.

- **O4 — Reviewable: load the suite; confirm run image hidden-test-free and scoring image with them; locate the self-test reference solution.**
  - *Claim:* a reviewer loads the suite, lists the seed instances, confirms the run image carries no hidden tests while the scoring image does, and locates the self-test instance's private reference solution.
  - *Evidence to collect:* list the instances; inspect the run and scoring images for the hidden suite; open the self-test instance's reference solution.
  - *Status:* SATISFIED — exercised, not assumed. Listed the suite (`load_instances()` → `greenfield__text_toolkit__0001`, `greenfield__scheduler__0001`). Built and inspected both Docker images live: `find /workspace/hidden` in the run image returns nothing while the scoring image carries every hidden test file (`test_run_image_excludes_hidden_scoring_image_includes` PASS). Confirmed the round-trip oracle live in the scoring image — the reference patch applied + hidden suite passes, the unpatched no-op fails (`test_reference_resolves_in_scoring_image_and_noop_does_not` PASS); and Docker-free via `LocalScoringBackend` (`test_reference_solution_resolves_locally_and_noop_does_not` PASS). Opened `…/greenfield__text_toolkit__0001/reference/solution.patch` — a real 4-module diff outside `goldPatch`.

## Regression check

- No existing callers — the suite's data and images are consumed by the container backends (Tasks 04, 05), built later. Confirm the new greenfield instances validate against the Task 02 schema without changing it : PRESERVED — the Task 02 `TaskInstance` schema is unchanged (the only non-suite edit is a `pyright` `exclude` glob for the suite repo dirs in `pyproject.toml`); both instances validate on build and survive a `to_dict()`/`from_dict()` round-trip. The full 84-test repo suite (Tasks 01/02 included) stays green.

## Residue

- Seed count vs usable interval width is a task Open question (shared with plan.md suite sizing); not an obligation here.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: DONE
CONFIDENCE: high
SUMMARY: O1–O4 all SATISFIED with collected evidence (two validated instances, multi-component testTags, private reference outside goldPatch, full check.sh green incl. both Docker-gated image tests run LIVE) and the Task 02 schema is PRESERVED; the one wrinkle — a UnicodeDecodeError from stray, non-jj-tracked cpython-39 `.pyc` artifacts left in the working tree — is environmental contamination, not a defect in the committed implementation, so it does not lower the verdict (but the loader test's unfiltered UTF-8 read of every base/ file is a latent fragility worth hardening later).
