# Task 12 — Greenfield suite

**Plan:** [plan.md](plan.md) · **Status:** Todo · **Certificate:** [certificates/12-greenfield_suite.md](certificates/12-greenfield_suite.md)

**Implements:** [03-task-suites.md](../../benchmark/specs/03-task-suites.md) §Suite: `greenfield-features`, §Instance selection and fairness; [05-harness-architecture.md](../../benchmark/specs/05-harness-architecture.md) §Run container (greenfield image build)
**Depends on:** 02, 04
**Produces:** greenfield instances that run through an arm and are scored by their hidden suites, with the hidden tests baked only into the scoring image
**Pointers:** `benchmark/suites/greenfield-features/`; the `greenfield-hidden-tests` oracle convention in the scorer (task 04)

## Steps

- [ ] Define the two-image build: a run image from the skeleton repo with hidden tests **excluded**, and a scoring image from the same base with hidden tests **included**.
- [ ] Author a seed set of multi-component greenfield instances — a prose spec seed, a skeleton repo at a fixed commit, a hidden acceptance suite (`failToPass`), skeleton smoke tests (`passToPass`), `contaminationTier: authored-private`.
- [ ] Populate `testTags` mapping hidden tests to spec sections/components, to enable per-task escape attribution (task 14).
- [ ] Wire the `greenfield-hidden-tests` oracle convention into the scorer so a candidate is scored against the withheld suite.
- [ ] Add a test that the run image contains no hidden test files while the scoring image does, and that an arm's output is scorable against the hidden suite.

## Definition of done

- [ ] A greenfield instance runs through an arm and is scored by its hidden suite; a test asserts the hidden tests are absent from the run image and present in the scoring image.
- [ ] Seed instances are multi-component (the graph has width and depth) and carry `testTags`.
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer runs one arm on a greenfield instance, sees it scored by the withheld suite, and confirms the run image carries no hidden tests. **(M3 capstone.)**

## Open questions

- How many seed instances are authorable for the first campaign, and is that enough for usable intervals (shared with plan.md suite-size question).
