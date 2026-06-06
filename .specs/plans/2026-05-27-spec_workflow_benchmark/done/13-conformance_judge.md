# Task 13 — Conformance judge

**Plan:** [plan.md](../plan.md) · **Certificate:** [13-conformance_judge-certificate.md](13-conformance_judge-certificate.md)

**Implements:** [06-scoring-and-statistics.md](../../../benchmark/specs/06-scoring-and-statistics.md) §The conformance judge; [04-metrics.md](../../../benchmark/specs/04-metrics.md) §Bucket 3 (spec conformance)
**Depends on:** 07, 08, 12
**Produces:** a rubric-driven conformance score on `ScoreReport.conformanceScore`, with a stated human-label agreement figure
**Pointers:** `benchmark/harness/scoring/conformance/`; reuse `spec-reviewer` R2/R3 as the judging procedure where available

## Steps

- [x] Implement the rubric-driven LLM judge that scores final code against its spec in `[0, 1]`, using `spec-reviewer` R2/R3 as the procedure where the spec-creator plugin is available, else the rubric directly. *(`scoring/conformance/judge.py`: rubric-direct via a bounded host-side `claude -p`; four axes mirroring spec-reviewer R2; injectable judge backend.)*
- [x] Apply it on the greenfield suite for **every** arm: the prose spec seed is the instance input, so even A0 and A4 are judged against it, and A1's authored spec (or the spec handed to A2/A3) is judged the same way. *(`score_arm_conformance`; parametrized test over A0–A4.)*
- [x] Build the calibration harness: score a human-labelled sample and report agreement. *(`calibration.py`: exact-bucket agreement + Cohen's κ over a 5-item hand-labelled sample → 0.80 / κ 0.64, clears the 0.75 bar.)*
- [x] Write `conformanceScore` onto the relevant score reports. *(`_with_conformance` re-validates through the schema; null on no-spec suites.)*
- [x] Add a test that conformance is populated for all five arms on greenfield instances (the instance spec seed is always present) and left null on suites with no spec to score against. *(`test_conformance.py`: 25 non-live + 1 opt-in live (`BENCHMARK_RUN_CONFORMANCE_LIVE=1`); local-fixture never invokes the judge.)*

## Definition of done

- [ ] Conformance scores are produced for every arm on the greenfield suite and are null on suites that supply no spec.
- [ ] A human-label agreement figure is reported from the calibration sample and meets the agreed threshold (resolve the calibration Open question).
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer reads conformance scores for a greenfield instance across arms and the agreement figure against human labels.

## Open questions

- The agreement threshold and calibration sample size that make the conformance score reportable.
  - **Resolved (honestly, given a tiny seed).** Threshold pinned in `benchmark/harness/scoring/conformance/calibration.py` as named constants: `MIN_CALIBRATION_SAMPLE_SIZE = 4` and `MIN_CALIBRATION_AGREEMENT = 0.75` (exact-bucket agreement over three conformance bands — low/partial/high — reported alongside Cohen's kappa, which corrects for chance). The seeded human-labelled sample is 5 hand-authored exemplars from the saved live-arm patches for the one `text_toolkit` self-test instance (an empty stub anchoring `low`, A1's tokenizer-only patch anchoring `partial`, and A2/A3/A4's full implementations anchoring `high`), each label authored to the judge's rubric with a one-line rationale.
  - **Achieved (real judge, live):** exact-bucket agreement **0.80** (Cohen's kappa **0.64**) on the 5-item sample — clears the 0.75 bar. The single disagreement was the judge scoring A1's tokenizer-only patch in the `low` band (0.15) where the human labelled it `partial` (0.4). Live evidence saved at `benchmark/tests/_conformance_live_evidence/calibration.json` and a single-patch judgment at `.../judgment.json` (A2 patch → score 0.97 with an axis-citing rationale).
  - **Honesty note:** this seed is deliberately small (one instance, five exemplars) — enough to prove the calibration mechanism and report a real figure, not a publishable agreement statistic. A production-grade calibration needs a substantially larger human-labelled sample spanning many instances and arms, at which point both the threshold and the sample-size constant should be raised.
