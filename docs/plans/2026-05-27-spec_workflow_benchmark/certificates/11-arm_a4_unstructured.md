# Done Certificate — Task 11: Arm A4 unstructured

**Task:** [11-arm_a4_unstructured.md](../11-arm_a4_unstructured.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-05-27 — unverified

> This certificate is a verification protocol for Task 11. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 11) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** A4 — a budget-matched naive N-way parallel split with no plugins, no DAG, no DoD, no gates — scored on the greenfield suite.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** A4 has its own orchestration (not the `spec-*` plugins); must run through Task 07's driver and Task 04's oracle without changing them.

## Obligations

- **O1 — A4 runs with `N` matched to A1's task count and yields a scored patch.**
  - *Claim:* A4 splits the problem N ways across parallel agents, merges the outputs into one `candidatePatch`, and scores on the seed instances, with `N` set to A1's typical task count on the same instance.
  - *Evidence to collect:* run A4 on a seed instance; confirm `N` matches A1's task count for that instance; apply and score the merged patch → expect a `ScoreReport`.
  - *Checks:* resolve the orchestration to A4's own splitter, not the `spec-planner` DAG; confirm no `GateEvent`s are produced.
  - *Status:* ☐ unverified

- **O2 — The decomposition policy is pinned and documented.**
  - *Claim:* the "naive split" policy (fixed partition vs single split-N-ways prompt) is fixed and recorded, so the arm is reproducible.
  - *Evidence to collect:* read the pinned policy note (resolving the Open question); re-run A4 and confirm the same split policy is applied.
  - *Status:* ☐ unverified

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline; `N` derivation is a named, documented rule).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* ☐ unverified

- **O4 — Reviewable: run A4 on one instance; see N parallel agents, a merged scored patch, and the pinned policy.**
  - *Claim:* a reviewer runs A4 on one instance, sees `N` parallel agents and a merged scored patch, and reads the pinned policy.
  - *Evidence to collect:* run A4 once; show the N parallel runs, the merged patch, the `ScoreReport`, and the policy note.
  - *Status:* ☐ unverified

## Regression check

- Task 07's driver dispatch is shared with A0/A1/A2/A3. Trace one A1 trial after A4 is added → expect it still runs and scores unchanged : ☐ (PRESERVED / REGRESSION)

## Residue

- A4 merge conflicts feed the robustness metric in Task 15; this task only records them, not analyses them.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐
