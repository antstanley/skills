# Task 10 — Arms A2 / A3

**Plan:** [plan.md](plan.md) · **Status:** Todo · **Certificate:** [certificates/10-arms_a2_a3.md](certificates/10-arms_a2_a3.md)

**Implements:** [02-arms.md](../../benchmark/specs/02-arms.md) §A2 — Plan + build (spec handed in), §A3 — Build without gates
**Depends on:** 08
**Produces:** A2 (spec given, gates on) and A3 (spec given, gates off) provisioning recipes, both scored on the greenfield suite
**Pointers:** `benchmark/harness/arms/` (A2, A3 recipes as config variants of the A1 recipe)

## Steps

- [ ] Implement A2: skip `spec-creator`, hand in a ready-made spec, run `spec-planner` + `spec-builder` with both gates.
- [ ] Implement A3: identical to A2 but with `spec-builder`'s two gates disabled (the implementer's self-report decides completion).
- [ ] Source the handed-in spec to a fixed quality bar so spec variance does not leak into A2/A3 (resolve the given-spec provenance Open question before this lands).
- [ ] Run both arms through the driver and oracle on the seed instances.
- [ ] Add a test that A2 emits `GateEvent`s and A3 emits none, and both produce scored patches.

## Definition of done

- [ ] A2 and A3 run to completion and are scored on the seed instances; A2 records gate events, A3 records none.
- [ ] The handed-in spec is produced to a fixed, documented bar shared by both arms.
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer runs A2 and A3 on one instance and confirms the only behavioural difference is the presence/absence of the gates.

## Open questions

- Given-spec provenance (separate `spec-creator` pass, human-authored, or greenfield materials) must be fixed here, since it sets what the A1−A2 delta measures.
