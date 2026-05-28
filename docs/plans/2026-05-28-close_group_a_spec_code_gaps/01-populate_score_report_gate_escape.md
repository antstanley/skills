# Task 01 — Populate `ScoreReport.gateEscape`

**Plan:** [plan.md](plan.md) · **Status:** Todo

**Implements:** [06-scoring-and-statistics.md](../../benchmark/specs/06-scoring-and-statistics.md) §The test oracle — "Two derived facts are recorded on the `ScoreReport`: `regressed` and `gateEscape`."
**Depends on:** —
**Produces:** every gated trial's `ScoreReport.gateEscape` is set by the harness pipeline rather than reconstructed downstream; A0/A4 trials' field stays `None`; a test asserts the field matches `not resolved` on A1/A2 trials and `None` on A0/A4 trials over a synthetic CampaignRun.
**Pointers:** `benchmark/harness/scoring/probes/escape.py:86` (`derive_gate_escape`); `benchmark/harness/scoring/probes/escape.py:39` (`GATED_ARMS`); `benchmark/harness/domain.py:438` (`ScoreReport.gateEscape`); `benchmark/harness/driver/scheduler.py:214` (`_drive_trial`, the post-score site); `benchmark/harness/scoring/conformance/judge.py:298` (`_with_conformance`, the rebuild pattern to mirror).

## Steps

- [ ] Add a `_with_gate_escape(report, value)` helper in `benchmark/harness/scoring/probes/escape.py` that returns a new `ScoreReport` with `gateEscape` set, mirroring `_with_conformance` in `benchmark/harness/scoring/conformance/judge.py:298` (re-validate through the canonical schema by going via `to_dict` / `from_dict`).
- [ ] In `benchmark/harness/driver/scheduler.py::_drive_trial`, immediately after the scoring backend returns a report, gate on `arm.slug in GATED_ARMS` and call `derive_gate_escape(report)` then `_with_gate_escape(report, value)`; for A0/A4 leave the report unchanged so `gateEscape` stays `None`. Keep this as one short helper next to the existing conformance/gate-event threading so the driver's structure does not grow a new responsibility.
- [ ] Add a non-live test under `benchmark/tests/test_gate_escape_population.py`: construct a synthetic `CampaignRun` with two A1 trials (one resolved, one not), one A2 trial (not resolved), one A0 trial, and one A4 trial; assert the A1/A2 trials' `gateEscape` matches `not resolved`, the A0/A4 trials' `gateEscape` is `None`, every emitted `ScoreReport` still validates against `canonical-types.schema.json`, and `escape_rate` over the new reports returns the same numeric value it does on the old (unpopulated) reports — i.e. the metric does not silently shift.
- [ ] Document the gating rule in `_with_gate_escape`'s docstring (it is the canonical write site for the field) so a future reader is not tempted to populate the field on non-gated arms.

## Definition of done

- [ ] Every gated trial (A1, A2) returned by `run_campaign` has `ScoreReport.gateEscape` populated by the driver; non-gated trials (A0, A4) carry `None`.
- [ ] The new field's value matches `not report.resolved` on gated arms (the same derivation `derive_gate_escape` documents); the metric `escape_rate` from `benchmark/harness/scoring/probes/escape.py:157` returns the same number on the populated reports it returned on the unpopulated ones.
- [ ] Negative-space test: a non-gated arm (A0 or A4) never has `gateEscape` set, even when the same instance is re-run later under A1; the driver does not propagate a stale gate-escape value across trials.
- [ ] Meets the repo definition of done (uv-locked deps, ruff format + lint clean, pyright clean, pytest clean — see `plan.md` baseline). No schema delta required (the field already exists in `canonical-types.schema.json`).
- [ ] Reviewable: a reviewer runs the test suite and loads any saved live A2 evidence (`benchmark/tests/_a2_a3_live_evidence/a2/score_report.json`) reproduced through the new pipeline, then checks that `gateEscape` is now a present `true`/`false` rather than `null`/absent.
