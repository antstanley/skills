# Task 11 — Arm A4 unstructured

**Plan:** [plan.md](plan.md) · **Status:** Done · **Certificate:** [certificates/11-arm_a4_unstructured.md](certificates/11-arm_a4_unstructured.md)

**Implements:** [02-arms.md](../../benchmark/specs/02-arms.md) §A4 — Parallel but unstructured
**Depends on:** 07
**Produces:** A4 — a budget-matched naive N-way parallel split with no plugins, no DAG, no DoD, no gates — scored on the greenfield suite
**Pointers:** `benchmark/harness/arms/` (A4 recipe; its own orchestration, not the `spec-*` plugins)

## Steps

- [x] Implement a naive N-way decomposition that splits the problem across parallel agents with no dependency ordering, definition of done, or gates. *(`arms/a4.py` + container `_run_a4`: N plain `claude -p` agents, no plugins, run concurrently via a thread pool.)*
- [x] Set `N` to match A1's typical task count on the same instance so the parallelism budget is comparable. *(`A4_N = 4`, matching A1's 4-task `text_toolkit` plan.)*
- [x] Pin the decomposition policy (fixed partition vs a single "split N ways" prompt) so A4 is reproducible (resolve the A4 policy Open question). *(Pinned: fixed identical-full-statement coordination-free split, no planning — see Open questions.)*
- [x] Merge the parallel outputs into one `candidatePatch` and run through the driver and oracle. *(Naive merge: plain `git apply --index` in agent order, first-applier-wins, conflicts recorded not resolved; merged patch = `git diff base..HEAD`.)*
- [x] Add a test that A4 runs with the configured `N` and produces a scored patch, recording any merge conflicts. *(`test_a4_arm.py`: 15 non-live + 1 opt-in live (`BENCHMARK_RUN_A4_LIVE=1`). Live: 4 agents, $0.65, 3 conflicts recorded, resolved=true.)*

## Definition of done

- [ ] A4 runs to completion on the seed instances with `N` matched to A1's task count and yields a scored patch.
- [ ] The decomposition policy is pinned and documented so the arm is reproducible.
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer runs A4 on one instance, sees `N` parallel agents and a merged scored patch, and reads the pinned policy.

## Open questions

- ~~What counts as a fair "naive split" — fixed file/region partition or a single unstructured prompt — must be decided here for A1−A4 to be a clean structure-vs-concurrency test.~~ **RESOLVED (Task 11):** A **fixed, prompt-only N-way split with no intelligent planning** — all `N` agents receive the IDENTICAL full `problemStatement` plus a fixed coordination-free framing ("you are agent _i_ of _N_ working concurrently with no coordination and no shared plan; implement your share of this feature in this shared repository"). No dependency-ordered DAG, no per-task definition of done, no gates, and no `spec-*` plugin (no planner decides the slices). A *component partition* was rejected because producing a sensible partition IS planning and would smuggle (un-gated) planning value into the `A1−A4` delta; the identical-statement prompt-only split adds zero planning, so the only thing A4 adds over A0 is raw concurrency and the only thing A1 adds over A4 is the spec-driven structure — exactly the variable `A1−A4` isolates. The pinned policy lives in `benchmark/harness/arms/a4.py` (module docstring + `A4_SLICE_INSTRUCTION`); `N = A4_N = 4`, matched to A1's task count on the `text_toolkit` seed; the naive merge applies each agent diff in turn and RECORDS (does not resolve) conflicts.
