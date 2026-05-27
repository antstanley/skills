# Done Certificate — Task 02: Domain types

**Task:** [02-domain_types.md](../02-domain_types.md) · **Plan:** [plan.md](../plan.md)
**State:** Authored 2026-05-27 — unverified

> This certificate is a verification protocol for Task 02. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 02) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** Typed in-code records for every benchmark entity that validate against `canonical-types.schema.json`, with load/dump round-tripping.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Must not break the package skeleton's import tree from Task 17; the shared types module is imported by the driver, suites, backends, and scoring later.

## Obligations

- **O1 — Every entity round-trips and validates against the canonical schema.**
  - *Claim:* `Suite`, `TaskInstance`, `Arm`, `Campaign`, `Trial`, `Telemetry`, `ArtifactBundle`, `GateEvent`, `InjectedDefect`, `ScoreReport`, `MetricResult` each construct, dump, reload, and equal, and validate against `canonical-types.schema.json`.
  - *Evidence to collect:* run the round-trip test for each entity — expect PASS; confirm each `dump` output validates against the schema at [canonical-types.schema.json](../../../benchmark/specs/canonical-types.schema.json).
  - *Checks:* resolve the schema-validation call to the JSON Schema validator import, not a local stub; confirm IDs follow the `<prefix>_<uuid7>` pattern and `ArmSlug` is the fixed enum.
  - *Status:* ☐ unverified

- **O2 — Invalid records are rejected (negative-space).**
  - *Claim:* a bad ID prefix, a missing required field, and an out-of-enum `GateVerdict` are each rejected with a clear error.
  - *Evidence to collect:* run the negative-space tests — expect each to raise a validation error; confirm the error names the offending field.
  - *Status:* ☐ unverified

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* ☐ unverified

- **O4 — Reviewable: construct, dump, reload each entity, and see a malformed record rejected.**
  - *Claim:* a reviewer can construct each entity, round-trip it, and watch schema validation reject a deliberately malformed record.
  - *Evidence to collect:* in a REPL or test, construct each entity and round-trip it; submit a malformed record and observe rejection.
  - *Status:* ☐ unverified

## Regression check

- The shared types module is imported by Task 17's `benchmark.harness` tree. Trace that `import benchmark.harness` still resolves after the types are added : ☐ (PRESERVED / REGRESSION)

## Residue

- Schema/prose parity (every `$def` described in [01-domain-model.md](../../../benchmark/specs/01-domain-model.md)) was verified at spec time; not re-litigated here.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: ☐ (DONE | PARTIAL | NOT_DONE)
CONFIDENCE: ☐ (high | medium | low)
SUMMARY: ☐
