# Task 07 — Driver scheduler

**Plan:** [plan.md](plan.md) · **Status:** Done · **Certificate:** [certificates/07-driver_scheduler.md](certificates/07-driver_scheduler.md)

**Implements:** [01-domain-model.md](../../benchmark/specs/01-domain-model.md) §Lifecycle / state machine, [05-harness-architecture.md](../../benchmark/specs/05-harness-architecture.md) §Component shape, §Concurrency and reproducibility; [changes/2026-05-27-local_backends.md](../../benchmark/specs/changes/2026-05-27-local_backends.md) §Backends (backend-neutral driver)
**Depends on:** 19
**Produces:** a backend-neutral driver — a campaign runs end to end through the `RunBackend` / `ScoringBackend` interface, expanding the matrix, driving each trial through its lifecycle, and emitting one `ScoreReport` per trial (first exercised over the local-fixture suite in task 23, and on SWE-bench Pro via the container backend in M1)
**Pointers:** `benchmark/harness/driver/`; the backend interface from task 19

## Steps

- [x] Expand a `Campaign` into `Trial`s over (arm × instance × seed).
- [x] Drive each trial through `queued → provisioning → running → captured → scored → aggregated`, calling the campaign's `RunBackend` then its `ScoringBackend` through the task 19 interface — not a hardcoded backend.
- [x] Run independent trials concurrently up to a configured pool size (a named constant).
- [x] Treat an infra fault as `failed` (excluded from metrics, re-queueable), distinct from a legitimate `resolved: false`.
- [x] Add a test that a small campaign (driven through a backend test-double) produces a `ScoreReport` per trial and that a forced infra fault lands in `failed`, not `scored`.

## Definition of done

- [ ] A campaign over a suite completes and yields one `ScoreReport` per trial, the driver calling run then score through the backend interface, from which raw %Resolved is computable.
- [ ] Infra failures are recorded as `failed` and excluded from scored results.
- [ ] Meets the repo definition of done (uv-locked deps, pytest + ruff clean, named-constant limits, jj — see plan.md baseline).
- [ ] Reviewable: a reviewer launches a small campaign through a backend test-double (or the local backend) and reads the per-trial score reports and the raw %Resolved.
