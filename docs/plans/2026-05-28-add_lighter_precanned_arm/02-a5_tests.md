# Task 02 — A5 tests

**Plan:** [plan.md](plan.md) · **Status:** Proposed

**Implements:** [changes/2026-05-28-add_lighter_precanned_arm.md](../../benchmark/specs/changes/2026-05-28-add_lighter_precanned_arm.md) → Implementation notes step 4 (the A5 test surface); the gate-emission witness the change's Motivation centres on.
**Depends on:** 01 (the A5 record, constants, and `_run_a5` dispatch must exist).
**Produces:** `benchmark/tests/test_a5_arm.py` covering the A5 record/config/constants, dispatch, the pre-canned prompt, and the gate-emission witness; updates to `benchmark/tests/test_domain.py` for the six-member arm set. `uv run pytest benchmark/tests` green.
**Pointers:** mirror `benchmark/tests/test_a4_arm.py` (non-gated arm-record + dispatch + the live-by-reading discipline) and `benchmark/tests/test_a2_a3_arms.py` (the `extract_gate_events` assertions over a synthetic captured certificate); `benchmark/tests/test_domain.py:324` (`test_out_of_enum_arm_slug_rejected` — its docstring says "five-member set"); `extract_gate_events` (`benchmark/harness/arms/a2_a3.py:370`) and the certificate capture entry shape `"<relpath>\n<contents>"` (`container._classify_artifacts`).

## Steps

- [ ] New `benchmark/tests/test_a5_arm.py` with a module docstring tracing it to the change spec. Cover (non-gated, no Docker):
  - [ ] the A5 record: `slug == "A5"`, `pluginsEnabled == []`, `gatesEnabled is True`, `specProvided is False`, `executionMode == "single"`;
  - [ ] round-trip: `Arm.from_dict(A5.to_dict()) == A5`;
  - [ ] constants: `A5_MAX_BUDGET_USD == 5.0`, `A5_RUN_TIMEOUT_SECONDS == 600`, `A5_MODEL` is the plain model, and the budget is small relative to `A1_MAX_BUDGET_USD` (the "lighter" claim);
  - [ ] dispatch: `ContainerRunBackend._selects_a5(A5) is True` and `_selects_agent(A5)` / `_selects_workflow(A5)` / `_selects_a4(A5)` are all `False`; and that A0 still selects the agent path and does NOT select `_selects_a5`;
  - [ ] the pre-canned prompt: `a5_prompt(instance.problemStatement)` carries the problem statement, instructs writing a done-certificate, and names a `VERDICT:` line; it does NOT invoke `spec-planner` / `spec-builder` recursively (assert the recursion-driving skill names / "isolated workspace" phrasing are absent — it is pre-canned);
  - [ ] the gate-emission witness: build a synthetic captured certificate entry (`"docs/plans/p/certificates/01-feature.md\n…VERDICT: DONE…"`) in the shape `extract_gate_events` parses and assert it yields ≥ 1 `GateEvent` with the expected `gateKind` / mapped `verdict` — proving an A5 run's certificate maps to a `GateEvent` exactly as A2's does.
- [ ] Update `benchmark/tests/test_domain.py`: change `test_out_of_enum_arm_slug_rejected`'s docstring from "five-member set" to "six-member set" (keep it rejecting a bogus slug — `"A9"`); confirm any test that materialises `ARM_SLUGS` (e.g. `_campaign()`) still passes with the six-member tuple.
- [ ] If a live A5 test is added, gate it behind a `BENCHMARK_RUN_A5_LIVE=1` + Docker + creds `skipif` (mirror `test_a4_arm.py`'s opt-in) so `check.sh` / CI never pays for it; the build verifies only the SKIP/unit surface.

## Definition of done

- [ ] `uv run pytest benchmark/tests -q` is green (no failures; any live A5 test SKIPs without the env var / Docker).
- [ ] The A5 record validates + round-trips, the config + constants are asserted, A5 routes to `_run_a5` (not A0/workflow/A4), the pre-canned prompt carries the problem + certificate + `VERDICT:` directive (and is non-recursive), and a captured A5-style certificate yields ≥ 1 `GateEvent`.
- [ ] Negative space: a bogus arm slug (`"A9"`) is still rejected by the schema (`test_out_of_enum_arm_slug_rejected` passes with the updated docstring); A5 does NOT fall into the plain-A0 or the workflow path.
- [ ] Meets the repo definition of done (ruff lint+format, pyright standard, `uv run pytest benchmark/tests` green — see plan.md baseline).
- [ ] Reviewable: a reviewer reads `test_a5_arm.py` and confirms the assertions pin the change spec's claims — A5 emits a `GateEvent` without a recursive build, and routes to its own pre-canned path.
