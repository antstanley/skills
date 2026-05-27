# Task 12 — Greenfield suite

**Plan:** [plan.md](plan.md) · **Status:** Todo · **Certificate:** [certificates/12-greenfield_suite.md](certificates/12-greenfield_suite.md)

**Implements:** [03-task-suites.md](../../benchmark/specs/03-task-suites.md) §Suite: `greenfield-features`, §Instance selection and fairness; [05-harness-architecture.md](../../benchmark/specs/05-harness-architecture.md) §Run container (greenfield image build)
**Depends on:** 02
**Produces:** the greenfield instances and the two-image build (run image with hidden tests excluded, scoring image with them included) that the container backends (tasks 04, 05) provision against; the sole ablation suite
**Pointers:** `benchmark/suites/greenfield-features/`; the `TaskInstance` schema (task 02); the private reference solution mirrors the `local-fixture` `goldPatch` self-test pattern (task 21)

## Steps

- [ ] Define the two-image build: a run image from the skeleton repo with hidden tests **excluded**, and a scoring image from the same base with hidden tests **included**.
- [ ] Author a seed set of multi-component greenfield instances — a prose spec seed, a skeleton repo at a fixed commit, a hidden acceptance suite (`failToPass`), skeleton smoke tests (`passToPass`), `goldPatch: null`, `contaminationTier: authored-private`.
- [ ] Populate `testTags` mapping hidden tests to spec sections/components, to enable per-task escape attribution (task 14).
- [ ] Ship a **private reference solution** for at least one instance (a self-test instance) in the suite directory — *not* in the arms-visible `goldPatch` field — so the container scorer (task 04) can prove a known-good patch resolves and a no-op does not.
- [ ] Add a test that the run image contains no hidden test files while the scoring image does, and that every instance row validates against the canonical schema (task 02).

## Definition of done

- [ ] The greenfield instances load as validated `TaskInstance` records (`goldPatch: null`, `contaminationTier: authored-private`); a test asserts the hidden tests are absent from the run image and present in the scoring image.
- [ ] Seed instances are multi-component (the graph has width and depth) and carry `testTags`; the self-test instance ships a private reference solution outside the arms-visible fields.
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer loads the suite, lists the seed instances, confirms the run image carries no hidden tests while the scoring image does, and locates the self-test instance's private reference solution.

## Open questions

- How many seed instances are authorable for the first campaign, and is that enough for usable intervals (shared with plan.md suite-size question).
