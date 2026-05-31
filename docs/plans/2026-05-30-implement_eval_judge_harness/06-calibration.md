# Task 06 — Calibration

**Plan:** [plan.md](plan.md) · **Status:** Todo

**Implements:** [03-judge-stage.md](../../evaljudge/specs/03-judge-stage.md) §Calibration
**Depends on:** 05
**Produces:** a small hand-authored human-labelled sample of `(expected_output, actual behavior) → human score` items, an agreement computation (exact-bucket agreement + Cohen's kappa over the three bands), and a resolved `PASS_THRESHOLD` justified by the reported agreement figure rather than picked by feel
**Pointers:** new `benchmark/evaljudge/judge/calibration.py`; **reuse** the calibration primitives — `bucket_of`, `cohens_kappa`, `compute_agreement`, `run_calibration`, `CalibrationItem`, `AgreementReport`, `MIN_CALIBRATION_SAMPLE_SIZE`, `MIN_CALIBRATION_AGREEMENT` are all re-exported from the package root `benchmark.harness.scoring.conformance`; the `BANDS`/`LOW_BAND_MAX`/`HIGH_BAND_MIN` constants are **not** in the package `__all__`, so import those from the submodule `benchmark.harness.scoring.conformance.calibration` (where they are defined). Sample drawn from real skill behavior (e.g. captured runs of `spec-creator`/`semi-formal-review` evals).

## Steps

- [ ] Reuse the conformance calibration primitives (bands, `bucket_of`, `cohens_kappa`, `compute_agreement`) — import or mirror per [05-architecture.md](../../evaljudge/specs/05-architecture.md) §Reuse; do not fork the agreement math.
- [ ] Author a small `CALIBRATION_SAMPLE` of eval-judgment items spanning the bands: each carries an `expected_output`, a captured/representative behavior, a hand-authored `human_label` in `[0,1]`, and a one-line `rationale` written to the same rubric the judge applies. Be honest about size (a handful across a couple of skills — enough to prove the mechanism, not a publishable statistic).
- [ ] Define `MIN_CALIBRATION_SAMPLE_SIZE` and `MIN_CALIBRATION_AGREEMENT` as named constants (modest, matching the small seed); set `PASS_THRESHOLD` (task 05) against the sample and record the agreement figure that justifies it.
- [ ] Implement `run_calibration(sample, *, judge)` returning the agreement report, defaulting to the seeded sample and the live judge, with an injected deterministic judge for tests.
- [ ] Add `benchmark/tests/test_evaljudge_calibration.py` (hermetic): `compute_agreement` on a known label/score pairing yields the expected exact-bucket agreement and kappa; the seeded sample with an injected judge clears the resolved bar; an empty sample raises rather than dividing by zero.

## Definition of done

- [ ] A seeded human-labelled `CALIBRATION_SAMPLE` exists, spanning the `low`/`partial`/`high` bands, each label authored to the judge's rubric.
- [ ] The agreement computation (exact-bucket + Cohen's kappa) reuses the conformance calibration math (not forked) and reports an honest figure.
- [ ] `PASS_THRESHOLD` is set against the sample and the justifying agreement figure is recorded in the module; the sample-size and agreement bars are named constants.
- [ ] Negative space: an empty sample raises; a band disagreement is reflected in a lower agreement figure (tested with a known mismatched pairing).
- [ ] Meets the repo definition of done (tests, ruff, pyright, named constants — see plan.md baseline).
- [ ] Reviewable: `uv run pytest benchmark/tests/test_evaljudge_calibration.py` is green; a reviewer reads the sample, the reported agreement, and the threshold it justifies.

## Open questions

- The sample size and threshold value that make the verdict *trustworthy* (vs. merely mechanism-proving) are follow-up, not blockers ([03-judge-stage.md](../../evaljudge/specs/03-judge-stage.md), plan Open questions). This task ships the honest small seed and a documented threshold.
