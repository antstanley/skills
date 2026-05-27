# Task 11 — Arm A4 unstructured

**Plan:** [plan.md](plan.md) · **Status:** Todo · **Certificate:** [certificates/11-arm_a4_unstructured.md](certificates/11-arm_a4_unstructured.md)

**Implements:** [02-arms.md](../../benchmark/specs/02-arms.md) §A4 — Parallel but unstructured
**Depends on:** 07
**Produces:** A4 — a budget-matched naive N-way parallel split with no plugins, no DAG, no DoD, no gates — scored on SWE-bench Pro
**Pointers:** `benchmark/harness/arms/` (A4 recipe; its own orchestration, not the `spec-*` plugins)

## Steps

- [ ] Implement a naive N-way decomposition that splits the problem across parallel agents with no dependency ordering, definition of done, or gates.
- [ ] Set `N` to match A1's typical task count on the same instance so the parallelism budget is comparable.
- [ ] Pin the decomposition policy (fixed partition vs a single "split N ways" prompt) so A4 is reproducible (resolve the A4 policy Open question).
- [ ] Merge the parallel outputs into one `candidatePatch` and run through the driver and oracle.
- [ ] Add a test that A4 runs with the configured `N` and produces a scored patch, recording any merge conflicts.

## Definition of done

- [ ] A4 runs to completion on the seed instances with `N` matched to A1's task count and yields a scored patch.
- [ ] The decomposition policy is pinned and documented so the arm is reproducible.
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer runs A4 on one instance, sees `N` parallel agents and a merged scored patch, and reads the pinned policy.

## Open questions

- What counts as a fair "naive split" — fixed file/region partition or a single unstructured prompt — must be decided here for A1−A4 to be a clean structure-vs-concurrency test.
