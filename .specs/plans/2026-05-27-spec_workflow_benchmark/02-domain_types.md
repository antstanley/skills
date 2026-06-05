# Task 02 — Domain types

**Plan:** [plan.md](plan.md) · **Status:** Done · **Certificate:** [certificates/02-domain_types.md](certificates/02-domain_types.md)

**Implements:** [01-domain-model.md](../../benchmark/specs/01-domain-model.md) (entities, ID scheme), [canonical-types.schema.json](../../benchmark/specs/canonical-types.schema.json)
**Depends on:** 17
**Produces:** typed in-code records for every benchmark entity that validate against the canonical JSON Schema, with load/dump round-tripping
**Pointers:** `benchmark/harness/` (shared types module); [canonical-types.schema.json](../../benchmark/specs/canonical-types.schema.json) is the authority

## Steps

- [x] Define record types for `Suite`, `TaskInstance`, `Arm`, `Campaign`, `Trial`, `Telemetry`, `ArtifactBundle`, `GateEvent`, `InjectedDefect`, `ScoreReport`, `MetricResult`.
- [x] Implement ID generation per the spec's `<prefix>_<uuid7>` scheme and the fixed `ArmSlug` / suite-slug rules.
- [x] Validate every record against `canonical-types.schema.json` on construction and on load.
- [x] Provide load/dump for the JSONL instance files and the per-trial artifact records.
- [x] Add negative-space tests: a record with a bad ID prefix, a missing required field, and an out-of-enum `GateVerdict` are all rejected.

## Definition of done

- [ ] Every entity round-trips (construct → dump → load → equal) and validates against the canonical schema.
- [ ] Invalid records (bad prefix, missing required field, bad enum) are rejected with a clear error — the negative-space tests pass.
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer constructs each entity in a REPL or test, dumps and reloads it, and sees schema validation reject a deliberately malformed record.
