# Done Certificate — Task 10: Arms A2 / A3

**Task:** [10-arms_a2_a3.md](../10-arms_a2_a3.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-05-27 — unverified

> This certificate is a verification protocol for Task 10. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 10) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** A2 (spec given, gates on) and A3 (spec given, gates off) provisioning recipes, both scored on SWE-bench Pro.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** A2/A3 are config variants of the Task 08 A1 recipe; A1 and A0 must continue to run unchanged.

## Obligations

- **O1 — A2 and A3 run and are scored; A2 records gate events, A3 records none.**
  - *Claim:* both arms run to completion and score on the seed instances; A2's `ArtifactBundle` carries `GateEvent`s, A3's carries none.
  - *Evidence to collect:* run A2 and A3 on a seed instance; score both; read the bundles — expect A2 has gate events and A3 has zero.
  - *Checks:* resolve the A2/A3 difference to the single `gatesEnabled` flag on the `Arm` record (and `specProvided: true` for both); confirm no other behavioral divergence from A1's pipeline.
  - *Status:* ☐ unverified

- **O2 — The handed-in spec is produced to a fixed, documented bar shared by both arms.**
  - *Claim:* both arms consume the same given spec, produced to a fixed quality bar that does not vary per run.
  - *Evidence to collect:* read the given-spec provenance note (resolving the Open question) and confirm A2 and A3 consume the identical spec artifact.
  - *Status:* ☐ unverified

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* ☐ unverified

- **O4 — Reviewable: run A2 and A3 on one instance; confirm the only difference is the gates.**
  - *Claim:* a reviewer runs both arms on one instance and confirms the sole behavioural difference is the presence/absence of the gates.
  - *Evidence to collect:* run both; diff their bundles — expect they differ only in gate events (and gate-driven retries).
  - *Status:* ☐ unverified

## Regression check

- Task 08's A1 recipe and Task 07's driver dispatch are shared. Trace an A1 trial after A2/A3 are added → expect A1 still runs and scores unchanged : ☐ (PRESERVED / REGRESSION)

## Residue

- Given-spec provenance is a task Open question; if unresolved at validation, O2 is at best UNVERIFIED.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐
