# Done Certificate — Task 13: Conformance judge

**Task:** [13-conformance_judge.md](13-conformance_judge.md) · **Plan:** [plan.md](../plan.md)
**State:** Validated 2026-05-27

> This certificate is a verification protocol for Task 13. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 13) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** A rubric-driven conformance score on `ScoreReport.conformanceScore`, with a stated human-label agreement figure.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Consumes Task 07 score reports, Task 08 spec artifacts, and Task 12 greenfield specs; writing `conformanceScore` must not alter `resolved`/`regressed`.

## Obligations

- **O1 — Conformance is scored for the right arm/suite combinations and null where no spec exists.**
  - *Claim:* every arm on greenfield (scored against the instance spec seed, A0–A4 alike) gets a `conformanceScore` in `[0,1]`; arms on a suite that supplies no spec to score against get null.
  - *Evidence to collect:* run the judge over a mixed campaign; read `conformanceScore` per (arm, suite) → expect populated where a spec exists, null otherwise. Run the applicability test.
  - *Checks:* resolve the judging procedure to `spec-reviewer` R2/R3 where the spec-creator plugin is available, else the rubric directly; confirm greenfield scoring uses the instance's input spec seed.
  - *Status:* ☑ SATISFIED — `score_arm_conformance` (`judge.py:268`) is a single per-arm call site with no arm branching, so A0–A4 are judged identically against the `spec_text` passed (the instance `problemStatement` seed for A0/A4, the authored/given spec for A1–A3). `suite_supplies_spec` (`judge.py:257`) returns True only for `kind == "greenfield"`; otherwise the report gets `conformanceScore = None` and the judge is NOT invoked (`judge.py:292-293`). Tests `test_conformance_populated_for_every_arm_on_greenfield` (parametrized A0–A4, all → 0.88 populated), `test_conformance_null_on_no_spec_suite`, and `test_no_spec_suite_does_not_invoke_judge` (exploding judge never called) all pass in the 186-passed run. Checks: judging procedure resolves to the **rubric-direct** path (`judge.py:8-19`, `CONFORMANCE_RUBRIC`), the documented default the spec explicitly permits when not delegating to `spec-reviewer`; the rubric mirrors R2's four axes (coverage / API correctness / behavioural fidelity / no unspecified divergence) so it scores against the same bar. Greenfield scoring uses the instance spec seed (`TEXT_TOOLKIT_PROBLEM_STATEMENT`, `greenfield.py:142`) as the test's `spec_text`.

- **O2 — A human-label agreement figure is reported and meets the agreed threshold.**
  - *Claim:* the judge is calibrated against a human-labelled sample and the reported agreement meets the threshold set for reportability.
  - *Evidence to collect:* read the calibration output — the agreement figure and sample size; confirm it meets the agreed threshold (resolving the calibration Open question).
  - *Status:* ☑ SATISFIED — saved live `calibration.json` reports `n=5`, `exact_bucket_agreement=0.80`, `cohens_kappa=0.6428571…`, `meets_threshold=true`. Independently recomputed from the saved (human_label, judge_score) pairs: exact-bucket agreement = 0.80 and Cohen's kappa = 0.6428571428571429 — an exact match (formula `(p_o − p_e)/(1 − p_e)` correct). The Open question is resolved by named constants `MIN_CALIBRATION_SAMPLE_SIZE = 4` and `MIN_CALIBRATION_AGREEMENT = 0.75` (`calibration.py:66-67`); 0.80 ≥ 0.75 and n=5 ≥ 4, so the threshold is met. Labels are hand-authored against the same rubric and non-circular — the judge disagrees with the human on `a1-tokenizer-only` (human=partial/0.4, judge=low/0.2), so labels are not the judge's own output. Sample size is honestly documented as deliberately small (one instance, five exemplars; `calibration.py:24-29`).

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* ☑ SATISFIED — ran `bash scripts/check.sh` (exit 0, "All checks passed"): `uv sync --frozen` clean, `ruff format --check` clean, `ruff check` clean, `pyright` clean, `pytest` → **186 passed, 4 skipped** in 144s. The 4 skips are the documented opt-in live tests (A2/A3, A4, conformance live judge) gated behind env vars. Limits are named constants: `SCORE_MIN`/`SCORE_MAX`, `CONFORMANCE_MODEL`, `CONFORMANCE_MAX_BUDGET_USD`, `JUDGE_TIMEOUT_SECONDS` (`judge.py:48-66`); `LOW_BAND_MAX`, `HIGH_BAND_MIN`, `MIN_CALIBRATION_SAMPLE_SIZE`, `MIN_CALIBRATION_AGREEMENT` (`calibration.py:54-67`) — no magic numbers.

- **O4 — Reviewable: read conformance across arms on a greenfield instance and the agreement figure.**
  - *Claim:* a reviewer reads conformance scores for a greenfield instance across arms and the agreement figure against human labels.
  - *Evidence to collect:* render conformance per arm for one greenfield instance; show the calibration agreement figure.
  - *Status:* ☑ SATISFIED — for the greenfield `greenfield__text_toolkit__0001` instance, saved `judgment.json` renders the live A2 conformance score (`0.97`, raw 0.97) with a substantive rubric rationale; the per-arm scoring path is exercised across A0–A4 by `test_conformance_populated_for_every_arm_on_greenfield`. The calibration agreement figure is readable in `calibration.json` as a per-item table (name, human_label/band vs judge_score/band) plus the summary `exact_bucket_agreement=0.80`, `cohens_kappa=0.6429`, `n=5`, `meets_threshold=true`. A reviewer can read both directly. Exercised, not assumed.

## Regression check

- Task 07 score reports must keep their existing fields. Trace a score report after conformance is written → expect `resolved`/`regressed` unchanged, `conformanceScore` added : ☑ PRESERVED — `_with_conformance` (`judge.py:298-306`) rebuilds via `report.to_dict()` then sets only `payload["conformanceScore"]` and round-trips through `ScoreReport.from_dict`, so the required `resolved`/`regressed` fields (and any already-set optional `failToPass`/`passToPass`) carry through unchanged; `conformanceScore` is an existing optional field on `ScoreReport` (`domain.py:437`), not a schema addition. The test asserts `resolved=True`/`regressed=False` survive and `conformanceScore` is set (or null on no-spec). No mutation — inputs are frozen dataclasses; a fresh record is returned.

## Residue

- The calibration threshold is a task Open question; if unset at validation, O2 is UNVERIFIED.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: DONE
CONFIDENCE: high
SUMMARY: O1–O4 all SATISFIED with named evidence (every-arm scoring + null-on-no-spec confirmed via passing tests; agreement 0.80 ≥ 0.75 bar at n=5, kappa 0.6429 independently recomputed; `scripts/check.sh` exit 0 with 186 passed / 4 documented skips and named-constant limits; both judgment and calibration JSON render for a greenfield instance) and the Task 07 `ScoreReport` regression is PRESERVED (`_with_conformance` round-trips `to_dict`/`from_dict`, leaving `resolved`/`regressed` untouched).
