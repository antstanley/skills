# Change: Raise the recursive-arm workflow timeout and budget

**Status:** Merged · **Date:** 2026-05-28 · **Merged:** 2026-05-29 · **Owner:** Ant Stanley · **Target:** apps/benchmark

> Built at [`docs/plans/2026-05-28-raise_recursive_arm_timeout_budget/`](../../../../plans/2026-05-28-raise_recursive_arm_timeout_budget/plan.md).

Raise the **recursive-workflow run timeout** for the A1/A2/A3 arms from 1200 s (20 min) to **3600 s (60 min)**, and raise the matched **per-run budget cap** from `$20` to **`$60`** (3× the time → 3× the dollars). The plain-agent (A0) and naive-parallel (A4) per-agent timeouts are *unchanged* — those are not recursive workflows. The change moves two named constants (one timeout, one dollar cap) and lets the existing A2/A3/A4 derivations track the new budget; it adds no entity, field, enum, or arm, and does not touch the resolution rule, the metrics, or the schema.

---

## Motivation

A live container witness ([05-harness-architecture.md](../../05-harness-architecture.md) → §Runtime verification) drove its gate-emission step by running a full recursive `spec-planner`+`spec-builder` workflow as **arm A2** inside the run container. The in-container `docker exec` running `claude -p` was **SIGKILLed by the 1200 s (20-min) `subprocess` timeout** in `ContainerRunBackend._run_workflow` before the recursive build could finish — the run reported a timeout fault rather than a real result.

The 20-minute bound was set as a conservative hard rail when the recursive path was first wired, before any live recursive build had been observed end to end. The witness shows it is too tight: a *genuine* recursive build — the orchestrator authoring/planning a spec and then spawning `spec-builder` sub-agents that walk the plan DAG, each gated — legitimately needs longer than 20 minutes. The bound is doing its job (it caught a run that could not finish in time), but the threshold is wrong: it kills honest in-progress builds, not just runaway ones.

Raising the timeout 3× to 60 minutes gives a real recursive build room to complete. The per-run **budget** cap must rise with it: the dollar cap and the time cap are the *paired* safety rails on the same recursive run (a 3× longer run can spend up to ~3× more), so a 3× time increase warrants a 3× dollar increase — `$20 → $60`. Leaving the budget at `$20` while tripling the time would let the run burn its full 60 minutes but still get cut off at the old spend, re-introducing the same "killed before finishing" failure by a different rail.

The plain-agent path (A0) and the naive N-way parallel path (A4) run *single* `claude -p` agents, not recursive workflows; their timeout is a **distinct** named constant (`AGENT_RUN_TIMEOUT_SECONDS`, reused by `A4_AGENT_RUN_TIMEOUT_SECONDS`) and must stay at the 20-minute plain-agent ceiling — raising it would wrongly inflate the A0/A4 wall-clock bound for a problem it does not have.

---

## Affected spec pages

| Canonical page | Nature of change |
|---|---|
| [`02-arms.md`](../../02-arms.md) | §Decisions — the *A4 matches A1's parallelism budget* Decision references `A1_MAX_BUDGET_USD`; note the budget cap's new `$60` value (the derivation `A4_TOTAL_MAX_BUDGET_USD = A1_MAX_BUDGET_USD`, per-agent `= total / A4_N`, is unchanged — only the resolved number moves) |
| [`05-harness-architecture.md`](../../05-harness-architecture.md) | §Concurrency and reproducibility (the *Intra-arm parallelism* row) and §Runtime verification — record that the recursive-workflow run (A1/A2/A3) is bounded by a 60-minute hard wall-clock cap paired with the per-run `--max-budget-usd` cap, distinct from the plain-agent/A4 bound |

No new canonical page is added; the schema (`canonical-types.schema.json`) is **unchanged** — this change introduces no entity, field, or enum, and moves no type. Only two named scalar constants and the prose that documents their values change.

---

## Proposed changes

Each block is the prose as it should read in the canonical page after merge.

### `02-arms.md` → §Decisions (Modify the *A4 matches A1's parallelism budget* Decision)

> - *A4 matches A1's parallelism budget on both dollars and concurrency.* **`N ≈ A1's task count` and total `--max-budget-usd` matched.** `A4_TOTAL_MAX_BUDGET_USD = A1_MAX_BUDGET_USD` (`$60` — raised from `$20` to match the 3× increase of the recursive-workflow run timeout; see [05-harness-architecture.md](05-harness-architecture.md) → §Concurrency and reproducibility) and each agent's cap is `A4_TOTAL_MAX_BUDGET_USD / A4_N` (`benchmark/harness/arms/a4.py:115, 120`), so the sum of A4's per-agent caps equals A1's single-run cap by construction. Without the dollar match, A1 − A4 would partly measure who got a bigger budget rather than what structure adds over raw parallelism.

### `05-harness-architecture.md` → §Concurrency and reproducibility (Modify the *Intra-arm parallelism* row)

> | **Intra-arm parallelism** | A1/A2/A3 run `spec-builder`'s own wave scheduler *inside* the run container; that concurrency is the arm's, not the driver's. The recursive workflow run is bounded by a **60-minute** hard wall-clock cap (`A1_RUN_TIMEOUT_SECONDS = 3600`, governing A1/A2/A3 in `ContainerRunBackend._run_workflow`) paired with the per-run `--max-budget-usd` cap (`$60`); a build that cannot finish within either rail reports an honest timeout/cap fault with partial evidence. This recursive-run bound is *distinct* from the plain-agent ceiling (`AGENT_RUN_TIMEOUT_SECONDS`) the A0 and A4 single-agent paths use. |

### `05-harness-architecture.md` → §Runtime verification (Modify the *Provisioning + capture* bullet)

> - **Provisioning + capture.** The `container` `RunBackend` builds/loads the instance run image, runs a bounded real arm (A0 by default; A1/A2/A3 when a budget is supplied), and returns a `candidatePatch` plus an `ArtifactBundle`. A recursive workflow arm (A1/A2/A3) runs under the 60-minute recursive-run wall-clock cap and the matched `$60` per-run budget cap; the plain A0 arm runs under the 20-minute plain-agent cap.

---

## Type changes

None. This change adds no entity, field, or enum; `canonical-types.schema.json` and `benchmark/harness/domain.py` are untouched. It moves the value of two named scalar constants — `A1_RUN_TIMEOUT_SECONDS` (1200 → 3600) and `A1_MAX_BUDGET_USD` (20.0 → 60.0) — and the A2/A3/A4 budget caps, which are *derived* from `A1_MAX_BUDGET_USD`, track the new value with no code change to the derivations.

---

## Implementation notes

Pointers for the implementing agent. Both changes are single-constant edits; the surrounding code already reads the constants by name, so the new values propagate without touching the call sites.

```
1. Timeout: in benchmark/harness/backends/container.py raise the recursive-workflow run
   timeout A1_RUN_TIMEOUT_SECONDS from 1200 to 3600. Trace its uses: _run_workflow
   (subprocess timeout for the A1/A2/A3 claude -p run) and the workflow-arm branch of
   _start_container's keepalive `sleep` (alive = A1_RUN_TIMEOUT_SECONDS + ...). BOTH pick
   up the new value because both read the constant by name. Leave AGENT_RUN_TIMEOUT_SECONDS
   (1200, the plain A0 path / its A4 reuse A4_AGENT_RUN_TIMEOUT_SECONDS), AUTH_PROBE_*,
   SETUP_*, and A1_FEASIBILITY_PROBE_TIMEOUT_SECONDS unchanged — they are not the recursive
   run. A1_RUN_TIMEOUT_SECONDS is already a SEPARATE constant from the plain-agent one, so
   no new constant is needed and the plain-agent path cannot be inflated.
2. Budget: in benchmark/harness/arms/a1.py raise A1_MAX_BUDGET_USD from 20.0 to 60.0.
   A2_A3_MAX_BUDGET_USD = A1_MAX_BUDGET_USD (a2_a3.py:175) and A4_TOTAL_MAX_BUDGET_USD =
   A1_MAX_BUDGET_USD (a4.py:115) inherit it; A4_PER_AGENT_MAX_BUDGET_USD =
   A4_TOTAL_MAX_BUDGET_USD / A4_N (a4.py:120) recomputes to 60 / 4 = 15.0. Keep all three
   derivations intact (do NOT hardcode the derived numbers).
3. Tests: grep benchmark/tests for the old values (1200 / 20.0 / A1_MAX_BUDGET_USD /
   *_RUN_TIMEOUT_SECONDS) and update/add assertions to the new ones. The arm tests already
   assert the budget derivations symbolically, so they track the new value; add an explicit
   assertion that A1_RUN_TIMEOUT_SECONDS == 3600, that AGENT_RUN_TIMEOUT_SECONDS stays 1200
   (regression: the plain-agent/A4 bound was NOT inflated), and that the resolved budget cap
   is 60.0 / per-agent 15.0. Every limit stays a named SCREAMING_SNAKE_CASE constant.
4. Validate: uv run ruff format <changed .py> && uv run ruff check benchmark &&
   uv run pyright benchmark/harness && uv run pytest benchmark/tests -q.
```

The committed `benchmark/tests/_a4_live_evidence/run_summary.json` records a *past* live A4 run at the old `$20` total / `$5` per-agent budget; it is a historical evidence artifact (an output of a real run, not a code constant or a test assertion), so it is left as-is — rewriting it would falsify the record of what that run actually spent. A future live run regenerates it at the new caps.

---

## Merge plan

1. Apply the `Proposed changes` blocks to their canonical pages; bump each page's `**Date:**` to the merge date. (Modify the *A4 matches A1's parallelism budget* Decision in `02`; modify the *Intra-arm parallelism* row in §Concurrency and the *Provisioning + capture* bullet in §Runtime verification in `05`.)
2. No `Type changes` to fold — `canonical-types.schema.json` is unchanged.
3. No new canonical page; nothing to index beyond existing entries.
4. Flip this file's `**Status:**` to `Merged`, add `**Merged:** YYYY-MM-DD`, and move it to `docs/benchmark/specs/changes/merged/`.

> **Note for the integrating orchestrator.** A parallel job also edits `02-arms.md`; merge this change's single-Decision prose edit alongside that job's edits rather than overwriting. The `05` edits are independent of the `02` job.

---

## Assumptions and open questions

**Assumptions**

- 60 minutes is enough wall-clock for a real recursive `spec-planner`+`spec-builder` build on the greenfield seed; the witness was killed at 20 min mid-build, and 3× is the proportional headroom that keeps the time/dollar rails matched. If a live 60-min run still cannot finish, the bound (and the matched budget) can be raised again the same way.
- The dollar cap and the time cap are the paired rails on the *same* recursive run, so a 3× time increase warrants a 3× dollar increase; holding the budget at `$20` would re-introduce the "killed before finishing" failure via the spend rail.
- A2/A3 are no more expensive or longer-running than A1 (same recursive workflow minus spec-creator / minus the gates), so reusing A1's raised cap and timeout for them stays a safe, conservative ceiling — the existing derivation, not a new assumption.

**Decisions**

- *Raise the recursive-run timeout only, not the plain-agent one.* **`A1_RUN_TIMEOUT_SECONDS` 1200 → 3600; `AGENT_RUN_TIMEOUT_SECONDS` unchanged.** A0/A4 are single `claude -p` runs, not recursive workflows; they do not have the "killed mid-recursive-build" problem and must keep the 20-minute plain-agent ceiling. The two timeouts are already distinct named constants, so no new constant is introduced.
- *Match the budget 3× to the timeout.* **`A1_MAX_BUDGET_USD` 20.0 → 60.0.** The paired rails must move together; 3× the time gets 3× the dollars.
- *Keep the A2/A3/A4 budget derivations.* **They read `A1_MAX_BUDGET_USD` by name and track the new value automatically; A4's per-agent cap recomputes to `60 / 4 = 15.0`.** Do not hardcode the derived numbers — the single source stays `A1_MAX_BUDGET_USD`.

**Open questions**

- *Live re-run.* Should an operator re-run the gate-emission live container witness (arm A2) under the new 60-min / `$60` rails to confirm the recursive build now completes, before this change is marked `Merged`? The build verifies the constants and derivations statically; only a live run proves the witness no longer SIGKILLs.
- *Future tightening.* If real recursive builds consistently finish well under 60 minutes, should the bound be tuned down toward the observed p95 to fail runaway runs faster, rather than left at a round 3× of the old value?
