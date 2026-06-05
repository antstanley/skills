# Task 10 — Arms A2 / A3

**Plan:** [plan.md](plan.md) · **Status:** Done · **Certificate:** [certificates/10-arms_a2_a3.md](certificates/10-arms_a2_a3.md)

**Implements:** [02-arms.md](../../benchmark/specs/02-arms.md) §A2 — Plan + build (spec handed in), §A3 — Build without gates
**Depends on:** 08
**Produces:** A2 (spec given, gates on) and A3 (spec given, gates off) provisioning recipes, both scored on the greenfield suite
**Pointers:** `benchmark/harness/arms/` (A2, A3 recipes as config variants of the A1 recipe)

## Steps

- [x] Implement A2: skip `spec-creator`, hand in a ready-made spec, run `spec-planner` + `spec-builder` with both gates. *(`arms/a2_a3.py`; container `_run_workflow_arm` with `specProvided=True`.)*
- [x] Implement A3: identical to A2 but with `spec-builder`'s two gates disabled (the implementer's self-report decides completion). *(Same config but `gatesEnabled=False`; the only behavioural difference.)*
- [x] Source the handed-in spec to a fixed quality bar so spec variance does not leak into A2/A3 (resolve the given-spec provenance Open question before this lands). *(Resolved — see Open questions: a frozen per-instance authored `given_spec.md` asset, `GIVEN_SPEC_QUALITY_BAR` documented, consumed identically by both arms via `load_given_spec`.)*
- [x] Run both arms through the driver and oracle on the seed instances. *(Live on `text_toolkit`: A2 resolved=true $4.18 / 4 GateEvents; A3 resolved=true $1.60 / 0 GateEvents. Evidence in `benchmark/tests/_a2_a3_live_evidence/`.)*
- [x] Add a test that A2 emits `GateEvent`s and A3 emits none, and both produce scored patches. *(`test_a2_a3_arms.py`; `extract_gate_events` parses discharged certificates → 4 for gates-on, 0 for gates-off.)*

## Definition of done

- [ ] A2 and A3 run to completion and are scored on the seed instances; A2 records gate events, A3 records none.
- [ ] The handed-in spec is produced to a fixed, documented bar shared by both arms.
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer runs A2 and A3 on one instance and confirms the only behavioural difference is the presence/absence of the gates.

## Open questions

- ~~Given-spec provenance (separate `spec-creator` pass, human-authored, or greenfield materials) must be fixed here, since it sets what the A1−A2 delta measures.~~

  **RESOLVED (task 10).** Provenance: a **frozen, human-authored spec asset, one per instance**, checked into the suite at `benchmark/suites/greenfield-features/<slug>/given_spec/given_spec.md` and consumed **identically** by A2 and A3 (same bytes, loaded by `benchmark.suites.greenfield.load_given_spec`). It is authored ONCE to the fixed, documented quality bar `benchmark.harness.arms.a2_a3.GIVEN_SPEC_QUALITY_BAR` (overview → domain model + invariants → one contract section per component with ≥2 worked examples → definition of done), and is NOT regenerated per run. Rationale: a per-run `spec-creator` pass would make A2 partly re-measure spec-creator (defeating A1−A2) and inject run-to-run spec variance that confounds the A2−A3 gate delta; a human-frozen shared asset removes both confounds. The full decision + rationale live in the `a2_a3.py` module docstring.

- **Gate observability / GateEvent wiring (carried over, partially resolved).** Task 10 ships REAL structural `GateEvent` extraction (`extract_gate_events`) that parses the captured done-certificates: a discharged certificate (gates on, A1/A2) carries a real `VERDICT:` line which maps onto the closed `GATE_VERDICTS` enum and yields a typed `GateEvent`; an undischarged certificate (gates off, A3) keeps the authored `(blank …)` placeholder and yields none. So A2 emits ≥1 GateEvent and A3 none, observable from the bundle alone. **Residual:** (1) the events currently ride on the run backend (`ContainerRunBackend.last_gate_events`) rather than flowing through the `RunBackend.run()` return tuple onto the `Trial`/`ArtifactBundle` — the domain model hangs `GateEvent` off the Trial, but the backend interface returns only `(bundle, patch)`; threading them through the driver is deferred to a metrics task (14). (2) `retryIndex` is always `0`: the merged certificate reflects only the FINAL gate discharge, so per-retry gate history is not recoverable from the captured artifact. (3) The A1 live evidence shows the validate-done gate did not always rewrite the verdict INTO the certificate file (it can record the verdict in its build log instead); the A2 prompt now explicitly instructs discharge-in-place (`writing the gate VERDICT into certificates/NN-<task>.md`) so the verdict is observable, but a transcript-based fallback extractor is a possible future hardening.
