# Task 13 — Conformance judge

**Plan:** [plan.md](plan.md) · **Status:** Todo · **Certificate:** [certificates/13-conformance_judge.md](certificates/13-conformance_judge.md)

**Implements:** [06-scoring-and-statistics.md](../../benchmark/specs/06-scoring-and-statistics.md) §The conformance judge; [04-metrics.md](../../benchmark/specs/04-metrics.md) §Bucket 3 (spec conformance)
**Depends on:** 07, 08, 12
**Produces:** a rubric-driven conformance score on `ScoreReport.conformanceScore`, with a stated human-label agreement figure
**Pointers:** `benchmark/harness/scoring/conformance/`; reuse `spec-reviewer` R2/R3 as the judging procedure where available

## Steps

- [ ] Implement the rubric-driven LLM judge that scores final code against its spec in `[0, 1]`, using `spec-reviewer` R2/R3 as the procedure where the spec-creator plugin is available, else the rubric directly.
- [ ] Apply it on the greenfield suite for **every** arm: the prose spec seed is the instance input, so even A0 and A4 are judged against it, and A1's authored spec (or the spec handed to A2/A3) is judged the same way.
- [ ] Build the calibration harness: score a human-labelled sample and report agreement.
- [ ] Write `conformanceScore` onto the relevant score reports.
- [ ] Add a test that conformance is populated for all five arms on greenfield instances (the instance spec seed is always present) and left null on suites with no spec to score against.

## Definition of done

- [ ] Conformance scores are produced for every arm on the greenfield suite and are null on suites that supply no spec.
- [ ] A human-label agreement figure is reported from the calibration sample and meets the agreed threshold (resolve the calibration Open question).
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer reads conformance scores for a greenfield instance across arms and the agreement figure against human labels.

## Open questions

- The agreement threshold and calibration sample size that make the conformance score reportable.
