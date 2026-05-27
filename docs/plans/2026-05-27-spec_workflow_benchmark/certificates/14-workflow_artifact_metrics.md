# Done Certificate — Task 14: Workflow-artifact metrics

**Task:** [14-workflow_artifact_metrics.md](../14-workflow_artifact_metrics.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-05-27 — unverified

> This certificate is a verification protocol for Task 14. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 14) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** Plan coverage and DAG validity from plan artifacts, gate catch rate from injected defects, and false-`Done` escape rate.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Consumes Task 08/10 plan artifacts and gates and Task 12 `testTags`; injecting defects must not corrupt organic trial results.

## Obligations

- **O1 — Catch and escape rates for gated arms; coverage and DAG validity for plan-producing arms.**
  - *Claim:* gate catch rate (from `InjectedDefect`) and false-`Done` escape rate are produced for A1/A2; plan coverage and DAG validity are produced for A1/A2/A3.
  - *Evidence to collect:* run the metrics over a campaign with gated arms; read catch rate, escape rate, coverage, DAG validity — expect each populated for its applicable arms.
  - *Checks:* resolve the escape source to `ScoreReport.gateEscape`; resolve coverage to the `Implements`→spec-section mapping and DAG validity to an acyclicity check over the plan's dependency table.
  - *Status:* ☐ unverified

- **O2 — Per-task escape attribution works where `testTags` exist and falls back otherwise.**
  - *Claim:* with `testTags` (greenfield) escape is attributed per task via the `Implements` pointer; without them escape is computed at instance granularity.
  - *Evidence to collect:* run on a greenfield instance with `testTags` → expect per-task attribution; run on an instance without `testTags` → expect instance-granularity escape. Run the known-bad-patch tests (one caught, one escaped) and confirm the counts.
  - *Status:* ☐ unverified

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline; defect counts/classes are named constants).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* ☐ unverified

- **O4 — Reviewable: inject a known defect, see it counted caught/escaped; read coverage and DAG validity.**
  - *Claim:* a reviewer injects a known defect, sees it counted as caught or escaped, and reads the coverage and DAG-validity figures for a workflow trial.
  - *Evidence to collect:* inject one defect through a gated build; show whether it was caught; print coverage and DAG validity for the trial's plan.
  - *Status:* ☐ unverified

## Regression check

- Injected-defect probe trials must be segregated from organic trials. Trace an organic A1 trial run alongside probes → expect its `ScoreReport` is unaffected by the injected defects : ☐ (PRESERVED / REGRESSION)

## Residue

- Defect-injection realism (hand-injected vs mined from real failed trials) is a spec Open question; the validator should note which was used and let it inform CONFIDENCE.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐
