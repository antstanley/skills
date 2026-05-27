# Task 18 — Local-backend domain and schema extensions

**Plan:** [plan.md](plan.md) · **Status:** Done · **Certificate:** [certificates/18-local_backend_domain.md](certificates/18-local_backend_domain.md)

**Implements:** [changes/2026-05-27-local_backends.md](../../benchmark/specs/changes/2026-05-27-local_backends.md) §Proposed changes (`01-domain-model.md` → Suite, Campaign), §Type changes
**Depends on:** 02
**Produces:** the domain types and the canonical schema carry the local-backend members — `Suite.kind` += `local-fixture`, `Suite.oracleConvention` += `local`, and `Campaign.backend` / `Campaign.solver`
**Pointers:** `benchmark/harness/` (the Task 02 types); [canonical-types.schema.json](../../benchmark/specs/canonical-types.schema.json)

## Steps

- [x] Extend `Suite.kind` with `local-fixture` and `Suite.oracleConvention` with `local`.
- [x] Add `Campaign.backend` (`container` default | `local`) and `Campaign.solver` (`agent` default | `fixture`).
- [x] Apply the change spec's `Type changes` fragment to `canonical-types.schema.json` (the modified `Suite` and `Campaign` `$defs`).
- [x] Add negative-space tests: an out-of-enum `backend` and an unknown `kind` are rejected; omitted `backend`/`solver` default to `container`/`agent`.

## Definition of done

- [ ] A `Suite{kind: local-fixture, oracleConvention: local}` and a `Campaign{backend: local, solver: fixture}` construct and validate against the schema.
- [ ] Defaults hold (`backend=container`, `solver=agent`) when omitted, and an out-of-enum `backend` is rejected — the negative-space tests pass.
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer constructs the local `Suite` and local `Campaign`, validates both, and sees an unknown `backend` value rejected.

## Open questions

- The change spec is merged into the canonical pages/schema only once the local backend ships (post-M0); this task implements the schema delta, the spec-creator merge step retires the change-spec document.
