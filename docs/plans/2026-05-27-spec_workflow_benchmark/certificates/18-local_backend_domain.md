# Done Certificate — Task 18: Local-backend domain and schema extensions

**Task:** [18-local_backend_domain.md](../18-local_backend_domain.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-05-27 — unverified

> This certificate is a verification protocol for Task 18. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 18) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** The domain types and canonical schema carry the local-backend members: `Suite.kind` += `local-fixture`, `Suite.oracleConvention` += `local`, and `Campaign.backend` / `Campaign.solver`.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Extends Task 02's types and the canonical schema; existing entities and their validation must keep working (additive change only).

## Obligations

- **O1 — Local `Suite` and `Campaign` construct and validate.**
  - *Claim:* a `Suite{kind: local-fixture, oracleConvention: local}` and a `Campaign{backend: local, solver: fixture}` construct and validate against the schema.
  - *Evidence to collect:* construct both and validate against [canonical-types.schema.json](../../../benchmark/specs/canonical-types.schema.json) — expect valid; confirm the schema's `Suite` and `Campaign` `$defs` carry the change spec's enum/property additions.
  - *Checks:* resolve the schema the code validates against to the updated `canonical-types.schema.json`, not a stale copy.
  - *Status:* ☐ unverified

- **O2 — Defaults hold and an out-of-enum backend is rejected (negative-space).**
  - *Claim:* omitted `backend`/`solver` default to `container`/`agent`; an out-of-enum `backend` and an unknown `kind` are rejected.
  - *Evidence to collect:* construct a `Campaign` without `backend`/`solver` → expect the defaults; run the negative tests for a bad `backend` and unknown `kind` → expect rejection.
  - *Status:* ☐ unverified

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* ☐ unverified

- **O4 — Reviewable: construct the local Suite + Campaign, validate, see an unknown backend rejected.**
  - *Claim:* a reviewer constructs the local `Suite` and local `Campaign`, validates both, and sees an unknown `backend` rejected.
  - *Evidence to collect:* in a REPL/test, construct and validate both, then submit an unknown `backend` and observe rejection.
  - *Status:* ☐ unverified

## Regression check

- Task 02's existing entities must still validate. Trace a base `Suite{kind: issue-fixing}` and a base `Campaign` (no backend/solver) through validation after the additions → expect both still valid : ☐ (PRESERVED / REGRESSION)

## Residue

- Merging the change spec into the canonical pages/schema document is a separate spec-creator step once M0 lands; this task implements the schema delta in the code's authority.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐
