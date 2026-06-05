# Task 01 — Domain types and schema

**Plan:** [plan.md](plan.md) · **Status:** Todo

**Implements:** [01-domain-model.md](../../evaljudge/specs/01-domain-model.md) (all entities, ID scheme, lifecycle) and [canonical-types.schema.json](../../evaljudge/specs/canonical-types.schema.json) (the authored authority)
**Depends on:** —
**Produces:** the five frozen-dataclass records (`EvalCase`, `EvalRun`, `EvalJudgment`, `EvalResult`, `EvalReport`) plus their value objects, each validating against a hand-authored `benchmark/evaljudge/canonical-types.schema.json` on construction and load, with a test asserting the in-memory schema equals the on-disk file
**Pointers:** new `benchmark/evaljudge/domain.py`, new `benchmark/evaljudge/canonical-types.schema.json` (copy of the spec sidecar), `benchmark/evaljudge/__init__.py`; pattern source `benchmark/harness/domain.py` (frozen dataclasses, `new_record_id`, `<prefix>_<uuid7>`, schema-equality test); schema source [.specs/evaljudge/specs/canonical-types.schema.json](../../evaljudge/specs/canonical-types.schema.json)

## Steps

- [ ] Create the `benchmark/evaljudge/` package with an `__init__.py` whose docstring states the package surface and traces to the eval-judge spec.
- [ ] Copy the spec's `canonical-types.schema.json` to `benchmark/evaljudge/canonical-types.schema.json` as the hand-authored authority (the schema-is-authority rule).
- [ ] Implement the value objects and closed enums as the schema defines them: `RunStatus`, `ChangeKind`, `Band`, `Verdict` (closed string sets), `SeedFile`, `FileChange`, `Telemetry`, `SkillPassRate`.
- [ ] Implement the five record dataclasses as `@dataclass(frozen=True)` with `to_dict`/`from_dict` and `__post_init__` schema validation; generate ids via a `new_record_id(prefix)` helper using the `run_`/`judg_`/`res_`/`rep_` prefixes; `EvalCase` is keyed naturally by `(skill, id)` and is not generated.
- [ ] **Name every dataclass field in camelCase, identical to its schema key** (`fileChanges`, `expectedOutput`, `rawScore`, `caseSkill`, `caseId`, `passRate`, `bySkill`, …), mirroring the benchmark's `Record.to_dict` discipline (`out[f.name] = …`, no snake↔camel translation). The snake_case names in [01-domain-model.md](../../evaljudge/specs/01-domain-model.md)'s field bullets are a readability gloss, not the attribute names — see [05-architecture.md](../../evaljudge/specs/05-architecture.md) §Field naming. Snake/upper enum *values* (`run_failed`, `NOT_RUN`) are unaffected.
- [ ] Raise a typed `DomainValidationError` (rooted in a small package base exception) naming the entity and field on any schema or shape violation; no bare `except`, no `None`-as-error.
- [ ] Add `benchmark/tests/test_evaljudge_domain.py`: round-trip each record through `to_dict`/`from_dict`; assert the in-memory schema dict equals the on-disk JSON file; negative-space cases (bad id prefix, missing required field, out-of-enum `status`/`verdict`/`changeKind` value) each raise `DomainValidationError`.

## Definition of done

- [ ] All five records and their value objects construct, validate against `canonical-types.schema.json`, and round-trip through `to_dict`/`from_dict`.
- [ ] A test asserts the in-memory schema equals the on-disk `canonical-types.schema.json` file (drift guard), mirroring the benchmark's schema-equality test.
- [ ] Negative space: a bad ID prefix, a missing required field, and an out-of-enum value each raise a typed `DomainValidationError` with entity+field context.
- [ ] Meets the repo definition of done (tests, ruff format+lint, pyright standard, named-constant prefixes — see plan.md baseline).
- [ ] Reviewable: `uv run pytest benchmark/tests/test_evaljudge_domain.py` is green, and a reviewer can construct each record from a dict and read back a validated record.

## Open questions

- Whether to re-declare `RecordId`/`Slug`/`Timestamp` in this app's schema (per the layering rule) or `$ref` the benchmark schema is settled by the spec as *re-declare* ([05-architecture.md](../../evaljudge/specs/05-architecture.md) §Schema); the promote-to-global question is plan-level, not task-local.
