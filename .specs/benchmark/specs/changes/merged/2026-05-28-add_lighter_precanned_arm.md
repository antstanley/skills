# Change: Add a lighter pre-canned ablation arm (A5)

**Status:** Merged · **Date:** 2026-05-28 · **Merged:** 2026-05-29 · **Owner:** Ant Stanley · **Target:** apps/benchmark

Add a sixth ablation arm, **A5 — Lighter pre-canned**, that produces the same *observable artifacts* a gated workflow arm does — a candidate code patch plus at least one discharged done-certificate carrying a real `VERDICT:` line — but WITHOUT running the full recursive `spec-planner` + `spec-builder` build. A5 runs a single, FIXED, non-recursive `claude -p` call on a small budget cap and a short wall-clock timeout. It exists so the gate-emission machinery (`extract_gate_events`) and the cheaper end of the cost curve have a witness that *completes within a small bounded budget/timeout* — the recursive workflow arms (A1/A2/A3) can legitimately exceed the run timeout, so they are a poor fit for a fast, reliable gate-emission check. This change opens the closed `ArmSlug` enum from five members to six and adds the A5 record + its pre-canned provisioning recipe; the existing arms, metrics, scoring rule, and the run/scoring split are unchanged.

---

## Motivation

The benchmark's gate-emission behaviour — a gates-on workflow run discharges its done-certificates and yields ≥ 1 `GateEvent`, a gates-off run yields none — is the observable backbone of the `A2 − A3` gate delta ([02-arms.md](../../02-arms.md) → §A3). Today the only arms that emit gate events are A1 and A2, both of which are RECURSIVE `spec-*` workflows: the orchestrator spawns `spec-planner` and `spec-builder` sub-agents that walk a plan DAG in waves. Those arms are bounded by a generous `--max-budget-usd` cap and a ~20-minute timeout (`A1_RUN_TIMEOUT_SECONDS`, `benchmark/harness/backends/container.py`), and they can *legitimately hit the cap or the timeout before finishing*. That is honest for a campaign, but it makes them an unreliable and expensive fixture for two needs:

1. **A fast gate-emission witness.** Verifying that `extract_gate_events` maps a discharged `VERDICT:` line in a captured certificate onto a typed `GateEvent` does not require a full recursive build; it requires a captured certificate carrying a real verdict. A recursive arm produces that only at the end of a long, costly run that may time out first.
2. **A cheaper ablation point.** The cost curve from A0 (plain agent) to A1 (full workflow) has a large gap; a lighter arm that still emits gate events sits between the recursive arms and the plain baseline at a fraction of the budget.

A5 fills both. It is a PRE-CANNED, non-recursive flow: one bounded `claude -p` call with a FIXED prompt that directly implements the feature AND writes one done-certificate (with a real `VERDICT:` line) into the captured-artifact tree. It is deterministic and scripted — no `spec-planner`/`spec-builder` recursion, no plan DAG — so it finishes inside a small `A5_MAX_BUDGET_USD` (default 5.0) and `A5_RUN_TIMEOUT_SECONDS` (default 600). The captured certificate flows through the SAME `extract_gate_events` path the recursive arms use, so the witness is real structural extraction, not a synthetic flag.

A5 is *not* a new pairwise-delta arm: it does not isolate a workflow stage in a single-variable comparison the way A0–A4 do. It is a lighter instrument for gate-emission verification and a cheap cost-curve point, which is why this change reconciles the canonical *"Five arms, closed set"* decision to *"Six arms"* with that explicit rationale rather than claiming a new stage isolation.

---

## Affected spec pages

| Canonical page | Nature of change |
|---|---|
| [`01-domain-model.md`](../../01-domain-model.md) | §Arm (slug): the `slug` member set changes from `A0`–`A4` to `A0`–`A5`; the entity prose is otherwise unchanged |
| [`02-arms.md`](../../02-arms.md) | Add an **A5 — Lighter pre-canned** subsection and a row to the arm table; RECONCILE the *"Five arms, closed set"* Decision to *"Six arms"* with the rationale that A5 is a lighter pre-canned variant for gate-emission verification and a cheaper cost point, not a new stage isolation |
| [`canonical-types.schema.json`](../../canonical-types.schema.json) | Add `"A5"` to the `ArmSlug` enum (this is the runtime validation authority the code needs, so it is edited as implementation, not deferred to merge) |

No new canonical page is added. The `Arm` schema shape is otherwise unchanged: A5 reuses `executionMode = "single"` (the enum is NOT extended) and the existing `pluginsEnabled` / `gatesEnabled` / `specProvided` fields.

> **Note on the canonical prose pages.** This change spec authors the proposed-changes blocks below; the orchestrator merges the prose into `01-domain-model.md` and `02-arms.md` at integration (a parallel job also edits `02-arms.md`). The SCHEMA file (`canonical-types.schema.json`) IS edited as part of implementation, because `benchmark/harness/domain.py` loads it at runtime to validate every `Arm` record — `Arm(slug="A5")` cannot validate until the enum admits `"A5"`.

---

## Proposed changes

Each block is the prose as it should read in the canonical page after merge.

### `01-domain-model.md` → §Arm (slug) (Modify the `slug` bullet and the lead)

> A scaffold configuration: which plugins are active, whether the gates run, and the execution mode. The model is *not* an arm field — it is fixed by the Campaign. The six arms are defined in [02-arms.md](../../02-arms.md).
>
> Carries:
>
> - `slug` — `A0`–`A5`.
> - `pluginsEnabled` — the `spec-*` plugins active for this arm.
> - `gatesEnabled` — whether `spec-builder`'s correctness and done-certificate gates run.
> - `specProvided` — whether a ready-made spec is handed to the arm rather than authored by `spec-creator`.
> - `executionMode` — `single`, `parallel-structured`, or `parallel-unstructured`.

### `02-arms.md` → §The arms table (Add a row)

> | **A5** | none (pre-canned) | on | input only | single | Lighter pre-canned variant: emits gate events without a recursive build. |

### `02-arms.md` → new subsection **§A5 — Lighter pre-canned** (Add)

Insert after §A4 — Parallel but unstructured, before the `---` that precedes §The pairwise deltas.

> ### A5 — Lighter pre-canned
>
> A lighter, **pre-canned (non-recursive)** arm that produces the same observable artifacts a gated workflow arm does — a candidate code patch and at least one discharged done-certificate carrying a real `VERDICT:` line — but WITHOUT running the full recursive `spec-planner` + `spec-builder` build. A5 runs a single FIXED `claude -p` call (the pre-canned `A5_INSTRUCTION`) under a small `A5_MAX_BUDGET_USD` cap and a short `A5_RUN_TIMEOUT_SECONDS` wall-clock bound, with `gatesEnabled = true` so the captured certificate flows through the same `extract_gate_events` path the recursive arms use.
>
> A5 is **not** a pairwise-delta arm — it does not isolate a single workflow stage against another arm the way A0–A4 do. It exists for two operational needs the recursive arms serve poorly: (1) a fast, reliable **gate-emission witness** for `extract_gate_events` (`benchmark/harness/arms/a2_a3.py`) that does not depend on a long recursive build finishing before the run timeout; and (2) a **cheaper cost-curve point** between the plain A0 baseline and the full A1 workflow. The flow is deterministic and scripted: the fixed prompt instructs the single agent to implement the feature in place AND to write one done-certificate under the captured-artifact tree (`.specs/plans/.../certificates/`) with a real `VERDICT:` line. The container backend routes the A5 slug to a dedicated pre-canned path (`_run_a5`) — NOT the recursive `_run_workflow_arm` path — so no `spec-*` plugin is mounted and no sub-agent recursion occurs. The captured certificate yields ≥ 1 `GateEvent` via the same structural extraction A2 uses; A5's candidate patch excludes the `.specs/` artifact subtree exactly like the workflow arms.

### `02-arms.md` → §Decisions (Reconcile *Five arms, closed set* → *Six arms*)

> - *Six arms, closed set.* **A0–A5.** A0–A4 each isolate one stage in a pair; A5 is a lighter **pre-canned (non-recursive) variant** added for gate-emission verification and as a cheaper cost-curve point, *not* to isolate a new workflow stage. The pairwise-delta chain (A0 → A4 → A2 → A1, with A3 off A2) is unchanged — A5 sits outside it. The set is fixed at six so cross-campaign comparison is stable; A5 is included because the recursive workflow arms (A1/A2) can exceed the run timeout, making them a poor fixture for a fast, reliable check that a discharged certificate `VERDICT:` line maps to a `GateEvent`.

---

## Type changes

```json
{
  "$comment": "Fragment for 2026-05-28-add_lighter_precanned_arm. The ArmSlug enum opens from five members to six. The schema file IS edited as implementation (domain.py loads it at runtime to validate Arm records); this block records the canonical delta. No other $def changes — A5 reuses executionMode 'single' and the existing Arm fields.",
  "$defs": {
    "ArmSlug": {
      "description": "One of the six fixed ablation arms.",
      "type": "string",
      "enum": ["A0", "A1", "A2", "A3", "A4", "A5"]
    }
  }
}
```

`Arm` is otherwise unchanged: A5 sets `executionMode = "single"` (the `executionMode` enum is NOT extended), `gatesEnabled = true`, `specProvided = false`, and `pluginsEnabled = []` (no `spec-*` plugins — the flow is pre-canned, not recursive).

---

## Implementation notes

Pointers for the implementing agent. A5 is a new arm record plus a pre-canned provisioning recipe and a backend dispatch branch; it layers over already-shipped run/capture machinery and changes no metric or scoring rule.

```
1. Schema + domain: add "A5" to the ArmSlug enum in
   .specs/benchmark/specs/canonical-types.schema.json (the ArmSlug $def, ~line 25) and to the
   mirror constant ARM_SLUGS in benchmark/harness/domain.py (~line 102), updating the
   "five fixed / closed set" comment (~line 101) to say six. Arm(slug="A5") must validate.
2. New benchmark/harness/arms/a5.py — the A5 = Arm(...) record (pluginsEnabled=[],
   gatesEnabled=True, specProvided=False, executionMode="single") plus named constants
   A5_SLUG, A5_MODEL, A5_MAX_BUDGET_USD (5.0), A5_RUN_TIMEOUT_SECONDS (600),
   A5_INSTRUCTION (the FIXED pre-canned prompt that implements the feature AND writes one
   done-certificate with a real VERDICT: line under .specs/plans/.../certificates/), and an
   a5_prompt(problem_statement) builder. Mirror the shape of a0.py / a4.py. Export the public
   symbols from benchmark/harness/arms/__init__.py.
3. benchmark/harness/backends/container.py: add an A5 dispatch branch. Route the A5 slug
   (a new _selects_a5, matched BEFORE the plain-A0 _selects_agent test, like A4) to a
   dedicated _run_a5 that runs ONE bounded pre-canned claude -p call (no --plugin-dir, no
   spec-* mount) under A5_MAX_BUDGET_USD / A5_RUN_TIMEOUT_SECONDS, extracts the CODE-only
   candidate patch (.specs/ excluded, like the workflow arms), captures the artifacts, and
   threads the captured certificates through extract_gate_events so last_gate_events is
   populated. Do not break A0–A4.
4. Tests in benchmark/tests/: A5 Arm record validates + round-trips through the schema;
   ARM_SLUGS / ArmSlug include A5; the A5 config is correct (no plugins, gates on, no spec,
   single, the budget + timeout constants); A5 routes to _run_a5, NOT _selects_agent /
   _selects_workflow / _selects_a4; the pre-canned prompt carries the problem statement and a
   certificate-writing + VERDICT directive; a captured A5-style certificate fed to
   extract_gate_events yields >= 1 GateEvent. The live behaviour is gated/by-reading (no
   Docker here). Update test_domain.py's out-of-enum slug test docstring (five -> six) and keep
   it rejecting a bogus slug (e.g. "A9").
```

This change does not touch the Docker-free `local` pipeline, the metrics layer, the scoring rule, or arms A0–A4; it adds one enum member, one arm module, one backend branch, and tests.

---

## Merge plan

1. Apply each `Proposed changes` block to its canonical page; bump that page's `**Date:**` to the merge date. (Modify §Arm (slug) lead + `slug` bullet in `01`; add the §The arms table row, the §A5 — Lighter pre-canned subsection, and reconcile the *Five arms, closed set* Decision to *Six arms* in `02`. A parallel job also edits `02-arms.md`, so apply the A5 blocks without clobbering its edits.)
2. Fold the `Type changes` `$def` into `canonical-types.schema.json` — add `"A5"` to the `ArmSlug` enum and update its description to "six". (Done as implementation in this change, since the runtime code needs it; the merge step only confirms the canonical schema matches.)
3. No new canonical page; nothing to index beyond existing entries.
4. Flip this file's `**Status:**` to `Merged`, add `**Merged:** YYYY-MM-DD`, and move it to `.specs/benchmark/specs/changes/merged/`.

---

## Assumptions and open questions

**Assumptions**

- A single bounded `claude -p` call with a fixed prompt can reliably implement the small seed feature AND write one well-formed done-certificate (with a real `VERDICT:` line) within `A5_MAX_BUDGET_USD` / `A5_RUN_TIMEOUT_SECONDS`. The flow is honest about partial outcomes if it does not (the run reports what it produced), exactly as A0 does.
- A certificate written by the pre-canned prompt under `.specs/plans/.../certificates/` is captured into the bundle's `certificateArtifacts` by the same `_capture_artifacts` walk the workflow arms use, so `extract_gate_events` sees it without a new capture path.
- A5 reusing `executionMode = "single"` is sufficient: the flow is one agent, one call — it does not need a new execution mode, and not extending the enum keeps the `Arm` shape stable.

**Decisions**

- *Pre-canned, not recursive.* **One fixed `claude -p` call, no `spec-*` mount, no sub-agent recursion.** The whole point is a fast, bounded witness; a recursive workflow can exceed the run timeout, which is what A5 exists to avoid.
- *Gates on, but emitted by the prompt, not a gate sub-agent.* **`gatesEnabled = true` and the fixed prompt writes the discharged `VERDICT:` line directly.** A5 does not run `spec-builder`'s gate sub-agents (that would be recursion); it scripts the observable certificate the gate machinery reads, so `extract_gate_events` finds ≥ 1 `GateEvent` deterministically.
- *Outside the pairwise-delta chain.* **A5 is a verification / cost-curve instrument, not a stage-isolation arm.** The reconciled "Six arms" decision says so explicitly so a reader does not mistake A5 for a new single-variable comparison.

**Open questions**

- *Should A5 be a campaign arm or only a verification fixture?* It validates as a `Campaign.arms` member, but its scientific reading is "lighter cost-curve point", not a delta; whether campaigns routinely include it or it stays a self-test fixture is a campaign-design question, not a build blocker.
- *Certificate-shape robustness.* The pre-canned prompt asks the model to write a `VERDICT:` line in the shape `extract_gate_events` parses; if a model drifts from that shape the witness finds no event. Should A5 post-process / normalise the written certificate to guarantee the line, or rely on the fixed prompt? Left to the live run to inform.
