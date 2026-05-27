# Task 03 — SWE-bench Pro suite

**Plan:** [plan.md](plan.md) · **Status:** Todo · **Certificate:** [certificates/03-swe_pro_suite.md](certificates/03-swe_pro_suite.md)

**Implements:** [03-task-suites.md](../../benchmark/specs/03-task-suites.md) §Suite: `swe-bench-pro-public`
**Depends on:** 02
**Produces:** the SWE-bench Pro public instances ingested as validated `TaskInstance` records in `suites/swe-bench-pro-public/instances.jsonl`
**Pointers:** `benchmark/suites/swe-bench-pro-public/`; SWE-bench Pro dataset (`ScaleAI/SWE-bench_Pro`) and `jefzda/sweap-images` tags

## Steps

- [ ] Load the SWE-bench Pro public set and map each instance's fields to a `TaskInstance` per the spec's field table (`problemStatement`, `repo`/`baseCommit`, `goldPatch`, `failToPass`/`passToPass`, `dockerImage`, `contaminationTier: public`).
- [ ] Set `headlessVerifiable` per instance; record `testTags: null` (issue-fixing computes escape at instance granularity).
- [ ] Write `instances.jsonl` and confirm every row validates against the canonical schema (task 02).
- [ ] Select the small early-milestone seed (≈5 instances) and tag it so M1/M2 can run against a fixed subset.
- [ ] Add a test that the seed images are referenced (not vendored) and every selector field is populated.

## Definition of done

- [ ] `instances.jsonl` loads as validated `TaskInstance` records; the ≈5-instance seed subset is identifiable.
- [ ] No hidden test content is materialised into the run-side records — only selectors and image tags.
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer loads the suite, lists the seed instances, and confirms each carries a `dockerImage` tag and `failToPass`/`passToPass` selectors.
