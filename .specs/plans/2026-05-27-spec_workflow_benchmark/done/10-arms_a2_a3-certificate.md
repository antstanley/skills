# Done Certificate — Task 10: Arms A2 / A3

**Task:** [10-arms_a2_a3.md](10-arms_a2_a3.md) · **Plan:** [plan.md](../plan.md)
**State:** Validated 2026-05-27

> This certificate is a verification protocol for Task 10. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 10) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** A2 (spec given, gates on) and A3 (spec given, gates off) provisioning recipes, both scored on the greenfield suite.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** A2/A3 are config variants of the Task 08 A1 recipe; A1 and A0 must continue to run unchanged.

## Obligations

- **O1 — A2 and A3 run and are scored; A2 records gate events, A3 records none.**
  - *Claim:* both arms run to completion and score on the seed instances; A2's `ArtifactBundle` carries `GateEvent`s, A3's carries none.
  - *Evidence to collect:* run A2 and A3 on a seed instance; score both; read the bundles — expect A2 has gate events and A3 has zero.
  - *Checks:* resolve the A2/A3 difference to the single `gatesEnabled` flag on the `Arm` record (and `specProvided: true` for both); confirm no other behavioral divergence from A1's pipeline.
  - *Status:* ☑ SATISFIED — Saved live evidence (`benchmark/tests/_a2_a3_live_evidence/`): A2 run_summary `resolved:true, regressed:false, gate_event_count:4, gates_enabled:true` ($4.18); A3 run_summary `resolved:true, regressed:false, gate_event_count:0, gates_enabled:false` ($1.60). A2 `gate_events.json` = 4 `validate-done-certificate` PASS events (tasks 01-tokenizer..04-pipeline); A3 `gate_events.json` = `[]`. Both `score_report.json` show all 15 failToPass + 2 passToPass true, resolved=true. Checks: `arms/a2_a3.py:100-117` — A2/A3 `Arm` records differ in exactly `gatesEnabled` (True/False), both `specProvided=True`; `test_a3_arm_is_a2_without_gates` asserts `differing == {"gatesEnabled"}` (PASS). `_workflow_config_for` (`container.py:242-274`) gives A2/A3 identical `plugin_dir_names/model/max_budget_usd/provides_given_spec`, differing only in `prompt_builder` (a2/a3) + `gates_enabled`; the a2/a3 prompts differ only in gate instructions (`test_a2_prompt_*`/`test_a3_prompt_*` PASS). GateEvent extraction is real structural parsing of captured certificates (`extract_gate_events`), confirmed against the live certs. No divergence from A1's pipeline beyond the isolated variables.

- **O2 — The handed-in spec is produced to a fixed, documented bar shared by both arms.**
  - *Claim:* both arms consume the same given spec, produced to a fixed quality bar that does not vary per run.
  - *Evidence to collect:* read the given-spec provenance note (resolving the Open question) and confirm A2 and A3 consume the identical spec artifact.
  - *Status:* ☑ SATISFIED — Open question resolved and documented: `arms/a2_a3.py:19-35` provenance note + `GIVEN_SPEC_QUALITY_BAR` (`a2_a3.py:149-163`) fix a frozen, human-authored single-file spec, authored ONCE per instance, consumed identically by A2 and A3. Assets checked in: `benchmark/suites/greenfield-features/{greenfield__text_toolkit__0001,greenfield__scheduler__0001}/given_spec/given_spec.md`. A single arm-agnostic loader `load_given_spec(slug)` (`greenfield.py:398-409`) is the only source; `_run_workflow_arm` (`container.py:401-403`) calls it identically for A2 and A3 (keyed only by instance slug, no per-arm branch). Tests `test_given_spec_loader_returns_the_frozen_asset`, `test_given_spec_is_identical_bytes_for_both_arms`, `test_quality_bar_is_documented` PASS — same slug yields identical bytes for both arms.

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* ☑ SATISFIED — `bash scripts/check.sh` clean: `uv sync` checked 33 packages; `ruff format --check` 70 files already formatted; `ruff check` All checks passed; `pyright` 0 errors/0 warnings; `pytest` 146 passed, 2 skipped (the two opt-in LIVE arm tests, gated on `BENCHMARK_RUN_A2_A3_LIVE=1`/`BENCHMARK_RUN_A1_LIVE=1` + Docker + creds). `uv sync --frozen` clean (no lock drift). Limits are named constants: `A2_A3_MAX_BUDGET_USD` (= `A1_MAX_BUDGET_USD`), `A2_A3_MODEL`, `GIVEN_SPEC_QUALITY_BAR`, plugin/slug tuples — no magic numbers.

- **O4 — Reviewable: run A2 and A3 on one instance; confirm the only difference is the gates.**
  - *Claim:* a reviewer runs both arms on one instance and confirms the sole behavioural difference is the presence/absence of the gates.
  - *Evidence to collect:* run both; diff their bundles — expect they differ only in gate events (and gate-driven retries).
  - *Status:* ☑ SATISFIED — The reviewable action was exercised live and SAVED (per task instruction: discharge against saved evidence, not a re-run). Both arms ran on the SAME seed instance (`greenfield__text_toolkit__0001`) through the production `run_campaign` + container backends. Diffing the bundles: both candidate patches are CODE-only over the identical four modules (`text_toolkit/{tokenizer,normalizer,frequency,pipeline}.py`), both `resolved:true`/`regressed:false` with identical 15+2 test outcomes. The ONLY divergences are gate-driven: A2 `gate_event_count:4` + `certificate_artifact_count:4` (gates discharge certificates) vs A3 `0`/`0` (gates off, certificates never discharged), plus the expected cost/wall-clock consequences of running the gate sub-agents ($4.18/1141s vs $1.60/475s). No non-gate behavioural difference observed. `test_live_a2_emits_gate_events_and_a3_emits_none` is the harness for this (skipped on CI by design; its saved evidence is the discharge artifact).

## Regression check

- Task 08's A1 recipe and Task 07's driver dispatch are shared. Trace an A1 trial after A2/A3 are added → expect A1 still runs and scores unchanged : ☑ PRESERVED — A1 was refactored onto the shared `_run_workflow_arm` path but its config (`_workflow_config_for(A1)`, `container.py:244-252`) keeps creator-on, gates-on, NO given spec, A1's plugins/prompt/cap/model. The A1 dispatch helper was renamed `_selects_a1`→`_selects_workflow`; `test_a1_pipeline.py` updated to the new name and PASSES (A1 routes to the workflow path, A0/AGENT_SOLVER do not). `test_workflow_config_differs_only_in_the_isolated_variables` asserts A1's config differs from A2/A3 only in `provides_given_spec`/`gates_enabled`. Full suite 146 passed — no A1 or driver regression.

## Residue

- Given-spec provenance is a task Open question; if unresolved at validation, O2 is at best UNVERIFIED.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: DONE
CONFIDENCE: high
SUMMARY: O1–O4 all SATISFIED with evidence (saved live A2/A3 runs both resolved=true on the seed instance, A2 = 4 validate-done PASS GateEvents and A3 = 0; given-spec Open question resolved as a frozen shared per-instance asset; check.sh clean — 146 passed/2 opt-in-live skipped, uv --frozen clean, named limits; reviewable bundle diff shows the sole divergence is gate-driven), and the shared A1 recipe + driver dispatch are PRESERVED.

## Validation note (residue, not defects)

Honest residuals carried as scope (consistent with gate 1's CORRECT/high): (a) extracted `GateEvent`s ride on the backend's `last_gate_events` attribute rather than being attached to the `Trial` record yet — deferred to task 14 (workflow-artifact metrics); the DoD only requires A2 to "record" gate events and A3 none, which the saved evidence demonstrates. (b) `retryIndex` is fixed at 0 because the merged certificate reflects only the final discharge; per-retry history is the carried Open question. Neither weakens any O1–O4 obligation.
