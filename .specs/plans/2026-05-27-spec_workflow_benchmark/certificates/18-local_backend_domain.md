# Done Certificate — Task 18: Local-backend domain and schema extensions

**Task:** [18-local_backend_domain.md](../18-local_backend_domain.md) · **Plan:** [plan.md](../plan.md)
**State:** Validated 2026-05-27

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
  - *Evidence collected:* `Suite(slug="local-fixture", kind="local-fixture", oracleConvention="local")` constructs and `to_dict()` validates; `Campaign(backend="local", solver="fixture")` constructs, `payload["backend"]=="local"`, `payload["solver"]=="fixture"`, and `Campaign.from_dict(payload)==campaign` (round-trip). Schema `Suite.kind` enum = `[issue-fixing, greenfield, local-fixture]`, `oracleConvention` enum = `[swe-bench-pro, greenfield-hidden-tests, local]`, `Campaign.backend`/`solver` properties present (schema lines 41–42, 87–88) — byte-for-byte the change spec §Type changes fragment. Check: `_validator_for` builds the validator from `CANONICAL_SCHEMA` loaded via `CANONICAL_SCHEMA_PATH` (domain.py:38, 55–67) from on-disk `canonical-types.schema.json`; `test_canonical_schema_file_is_the_authority` asserts on-disk == embedded — not a stale copy. Tests `test_local_fixture_suite_constructs_and_validates`, `test_local_campaign_constructs_and_validates` PASS.
  - *Status:* ☑ SATISFIED

- **O2 — Defaults hold and an out-of-enum backend is rejected (negative-space).**
  - *Claim:* omitted `backend`/`solver` default to `container`/`agent`; an out-of-enum `backend` and an unknown `kind` are rejected.
  - *Evidence to collect:* construct a `Campaign` without `backend`/`solver` → expect the defaults; run the negative tests for a bad `backend` and unknown `kind` → expect rejection.
  - *Evidence collected:* `Campaign.from_dict({...no backend/solver...})` → `backend=="container"`, `solver=="agent"` (== `DEFAULT_BACKEND`/`DEFAULT_SOLVER`); defaults apply via dataclass field defaults `backend: str = DEFAULT_BACKEND` / `solver: str = DEFAULT_SOLVER` (domain.py:338–339), then `__post_init__` re-validates the defaulted `to_dict()`. Bad `backend="kubernetes"` → `DomainValidationError: Campaign record invalid at backend: 'kubernetes' is not one of ['container', 'local']`. Tests `test_campaign_backend_solver_default_to_container_agent`, `test_out_of_enum_backend_rejected`, `test_out_of_enum_solver_rejected`, `test_unknown_suite_kind_rejected` PASS.
  - *Status:* ☑ SATISFIED

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Evidence collected:* `uv sync` → resolved 13 / checked 12 packages, locked. `uv run pytest -q` → `35 passed in 0.12s`. `uv run ruff check` → `All checks passed!`. `uv run ruff format --check` → `13 files already formatted`. Named limits: `BACKENDS`, `DEFAULT_BACKEND`, `SOLVERS`, `DEFAULT_SOLVER`, `SUITE_KINDS`, `ORACLE_CONVENTIONS` are module-level named constants (domain.py:111–131).
  - *Status:* ☑ SATISFIED

- **O4 — Reviewable: construct the local Suite + Campaign, validate, see an unknown backend rejected.**
  - *Claim:* a reviewer constructs the local `Suite` and local `Campaign`, validates both, and sees an unknown `backend` rejected.
  - *Evidence to collect:* in a REPL/test, construct and validate both, then submit an unknown `backend` and observe rejection.
  - *Evidence collected:* exercised live via `uv run python` snippet: `local Suite valid: {'slug': 'local-fixture', 'kind': 'local-fixture', 'oracleConvention': 'local'}`; `local Campaign valid: local fixture roundtrip== True`; `defaults: container agent == container agent`; `bad backend rejected: Campaign record invalid at backend: 'kubernetes' is not one of ['container', 'local']`. Reviewer constructed both local entities, validated them, and saw the unknown backend rejected.
  - *Status:* ☑ SATISFIED

## Regression check

- Task 02's existing entities must still validate. Trace a base `Suite{kind: issue-fixing}` and a base `Campaign` (no backend/solver) through validation after the additions → expect both still valid : PRESERVED. The enum changes are supersets of the prior values; `backend`/`solver` are optional in the schema and supplied by dataclass defaults, so a base `Campaign` without them validates. The task-02 baseline subset (`uv run pytest -k "not local and not backend and not solver and not unknown_suite_kind"`) → `29 passed, 6 deselected` — the 29 task-02 tests still pass; the full suite is 35 (29 + 5 new local-backend tests + 1 schema-authority test).

## Residue

- Merging the change spec into the canonical pages/schema document is a separate spec-creator step once M0 lands; this task implements the schema delta in the code's authority.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: DONE
CONFIDENCE: high
SUMMARY: O1–O4 all SATISFIED with collected evidence — schema delta matches the change spec §Type changes fragment exactly and is the on-disk authority, local Suite/Campaign construct and validate, defaults (container/agent) apply when omitted and bad backend/solver/kind are rejected, and the repo DoD (uv-locked, 35 pytest pass, ruff check + format clean) holds; the 29 task-02 tests still pass (PRESERVED), additive change only.
