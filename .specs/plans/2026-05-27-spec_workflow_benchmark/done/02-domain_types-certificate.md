# Done Certificate — Task 02: Domain types

**Task:** [02-domain_types.md](02-domain_types.md) · **Plan:** [plan.md](../plan.md)
**State:** Validated 2026-05-27

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
  - *Status:* ☑ SATISFIED — `test_round_trip_and_schema_valid` parametrized over all 11 entities PASSES (construct → dump → load → equal, each dump validated against `#/$defs/<Entity>`); `test_jsonl_round_trip` and `test_artifact_record_json_round_trip` PASS. Machine-checked field parity: all 11 code dataclasses match the schema `$defs` properties + required exactly — no invented or omitted fields. Checks: `_validate` resolves to `jsonschema.Draft202012Validator` (domain.py:30, real validator not a stub); `new_record_id` builds `<prefix>_<uuid7>` and `uuid7()` returns `.version == 7` with RFC-4122 variant and time-ordered output (verified two calls 5ms apart sort ascending); `ARM_SLUGS = ("A0","A1","A2","A3","A4")` matches the fixed `ArmSlug` enum.

- **O2 — Invalid records are rejected (negative-space).**
  - *Claim:* a bad ID prefix, a missing required field, and an out-of-enum `GateVerdict` are each rejected with a clear error.
  - *Evidence to collect:* run the negative-space tests — expect each to raise a validation error; confirm the error names the offending field.
  - *Status:* ☑ SATISFIED — `test_bad_id_prefix_rejected`, `test_bad_id_body_rejected`, `test_missing_required_field_rejected`, `test_out_of_enum_gate_verdict_rejected`, `test_out_of_enum_arm_slug_rejected`, `test_unknown_field_rejected`, `test_slug_pattern_rejects_uppercase`, `test_error_message_is_clear` all PASS. Manually confirmed both paths: construct-path (`Arm(slug="A9", …)`) raises `DomainValidationError: Arm record invalid at slug: 'A9' is not one of [...]`; load-path (`GateEvent.from_dict` with `verdict="MAYBE"`) raises `... invalid at verdict: 'MAYBE' is not one of [...]`; missing-required (`Trial.from_dict` without `status`) raises `... invalid at <root>: 'status' is a required property`. Errors name the entity and offending location.

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* ☑ SATISFIED — `uv sync` clean (13 packages resolved); `uv run pytest -q` → `29 passed in 0.11s`; `uv run ruff check` → `All checks passed!`; `uv run ruff format --check` → `14 files already formatted`. Deps locked in `uv.lock` (`jsonschema>=4.0` runtime, `pytest`/`ruff` dev). Limits are named constants in domain.py (`ARM_SLUGS`, `GATE_VERDICTS`, `RECORD_ID_PATTERN`, `SLUG_PATTERN`, the `*_ID_PREFIX` constants, `_UUID7_VERSION`/`_UUID7_VARIANT`/bit-width constants).

- **O4 — Reviewable: construct, dump, reload each entity, and see a malformed record rejected.**
  - *Claim:* a reviewer can construct each entity, round-trip it, and watch schema validation reject a deliberately malformed record.
  - *Evidence to collect:* in a REPL or test, construct each entity and round-trip it; submit a malformed record and observe rejection.
  - *Status:* ☑ SATISFIED — exercised directly in a `uv run python` session: constructed `ArtifactBundle` (nested `Telemetry`) and `ScoreReport` with optional fields omitted, dumped → reloaded → equal, and the nested `telemetry` reloaded as a typed `Telemetry`. Submitted malformed records (`Arm(slug="A9")` on construct, `GateEvent.from_dict(verdict="MAYBE")` and `Trial.from_dict` missing `status` on load) and observed each rejected with a clear `DomainValidationError`. The parametrized round-trip test covers all 11 entities.

## Regression check

- The shared types module is imported by Task 17's `benchmark.harness` tree. Trace that `import benchmark.harness` still resolves after the types are added : ☑ PRESERVED — `import benchmark.harness` and `from benchmark.harness import domain` both resolve; the 4 skeleton smoke tests (`test_smoke.py`) all PASS; `jj diff -r @ --summary` shows only two **added** files (`benchmark/harness/domain.py`, `benchmark/tests/test_domain.py`) — no existing file (including `main.py` and `__init__.py`) was modified.

## Residue

- Schema/prose parity (every `$def` described in [01-domain-model.md](../../../benchmark/specs/01-domain-model.md)) was verified at spec time; not re-litigated here.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: DONE
CONFIDENCE: high
SUMMARY: O1–O4 all SATISFIED with evidence (29/29 tests pass, ruff clean, all 11 entities round-trip and validate against the on-disk canonical schema, both construct and load reject malformed records, uuid7 is genuine RFC-9562 v7); the `benchmark.harness` import tree is PRESERVED and only two new files were added.
