# Done Certificate — Task 11: Arm A4 unstructured

**Task:** [11-arm_a4_unstructured.md](11-arm_a4_unstructured.md) · **Plan:** [plan.md](../plan.md)
**State:** Validated 2026-05-27

> This certificate is a verification protocol for Task 11. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 11) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** A4 — a budget-matched naive N-way parallel split with no plugins, no DAG, no DoD, no gates — scored on the greenfield suite.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** A4 has its own orchestration (not the `spec-*` plugins); must run through Task 07's driver and Task 04's oracle without changing them.

## Obligations

- **O1 — A4 runs with `N` matched to A1's task count and yields a scored patch.**
  - *Claim:* A4 splits the problem N ways across parallel agents, merges the outputs into one `candidatePatch`, and scores on the seed instances, with `N` set to A1's typical task count on the same instance.
  - *Evidence to collect:* run A4 on a seed instance; confirm `N` matches A1's task count for that instance; apply and score the merged patch → expect a `ScoreReport`.
  - *Checks:* resolve the orchestration to A4's own splitter, not the `spec-planner` DAG; confirm no `GateEvent`s are produced.
  - *Status:* SATISFIED — Live evidence (`benchmark/tests/_a4_live_evidence/`, $0.65, ~109s):
    `run_summary.json` records `n_agents: 4`, `resolved: true`, `regressed: false`,
    `trial_status: "aggregated"`, `merge_conflict_count: 3`; `score_report.json` shows
    all 15 `failToPassResults` and 2 `passToPassResults` `true` with `resolved: true` —
    i.e. a scored merged patch. **N=4 matched to A1:** A1's saved live plan
    (`_a1_live_evidence/artifact_bundle.json`) decomposed `text_toolkit` into exactly four
    task files (`01-tokenizer`, `02-normalizer`, `03-frequency`, `04-pipeline`), and
    `A4_N = 4` (`a4.py:108`) is documented as that match. **Orchestration resolves to A4's
    own splitter:** `ContainerRunBackend.run` (`container.py:383-395`) routes A4 by slug to
    `_run_a4` (`_selects_a4` first, `container.py:811-821`), which fans out N plain
    `claude -p` agents via `_run_agents_in_parallel` + `_run_single_a4_agent` — no
    `spec-planner`/`--plugin-dir`, no DAG. **No GateEvents:** `_run_a4` never assigns
    `_last_gate_events` (only `_run_workflow_arm` does, `container.py:739`); the A4 transcript
    carries `perAgentResults` + a merge-conflict record, no gate events.

- **O2 — The decomposition policy is pinned and documented.**
  - *Claim:* the "naive split" policy (fixed partition vs single split-N-ways prompt) is fixed and recorded, so the arm is reproducible.
  - *Evidence to collect:* read the pinned policy note (resolving the Open question); re-run A4 and confirm the same split policy is applied.
  - *Status:* SATISFIED — The "naive split" policy is pinned to a **fixed, prompt-only N-way
    split with no intelligent planning**: all N agents get the IDENTICAL full
    `problemStatement` plus a fixed coordination-free framing. It is documented in two places:
    (1) `benchmark/harness/arms/a4.py` module docstring ("The pinned decomposition policy")
    plus the named constant `A4_SLICE_INSTRUCTION` (`a4.py:134-148`) and the deterministic
    `a4_slice_prompt()` (`a4.py:151-164`); (2) the task's `## Open questions` block, struck
    through and marked **RESOLVED (Task 11)** with the chosen policy and the rationale for
    rejecting a component partition (the diff on `11-arm_a4_unstructured.md`). Reproducibility:
    the prompt is a fixed template and N is a named constant, so `a4_slice_prompt` yields the
    identical split on every call (asserted by `test_a4_slice_prompt_is_coordination_free...`
    and `test_all_agents_get_the_same_problem_statement`, both passing).

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline; `N` derivation is a named, documented rule).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* SATISFIED — `bash scripts/check.sh` exited 0 in the task-11 workspace:
    `uv sync` clean (33 packages), `ruff format --check` "72 files already formatted",
    `ruff check` "All checks passed!", `pyright` "0 errors, 0 warnings, 0 informations",
    `pytest` **161 passed, 3 skipped** (the 3 skips are the opt-in live arm tests —
    A1/A2-A3/A4 — gated behind `BENCHMARK_RUN_*_LIVE=1`, not failures). `uv sync --frozen`
    re-run separately: clean (no lockfile drift). Limits are named constants:
    `A4_N`, `A4_TOTAL_MAX_BUDGET_USD`, `A4_PER_AGENT_MAX_BUDGET_USD = total / N`,
    `A4_AGENT_RUN_TIMEOUT_SECONDS`, `_A4_MERGE_CONFLICT_NOTE` — no magic numbers.

- **O4 — Reviewable: run A4 on one instance; see N parallel agents, a merged scored patch, and the pinned policy.**
  - *Claim:* a reviewer runs A4 on one instance, sees `N` parallel agents and a merged scored patch, and reads the pinned policy.
  - *Evidence to collect:* run A4 once; show the N parallel runs, the merged patch, the `ScoreReport`, and the policy note.
  - *Status:* SATISFIED — The live A4 run already executed and saved reviewable evidence
    under `benchmark/tests/_a4_live_evidence/`: **N parallel agents** — `transcript.json` /
    `artifact_bundle.json` carry `agentCount: 4` and four distinct `perAgentResults` (each a
    completed `claude` run with its own session_id), run concurrently (per-agent durations
    ~54-86s vs ~109s arm wall clock → genuinely parallel, not serial). **Merged scored
    patch** — `candidate_patch.diff` is a clean unified diff over the four `text_toolkit`
    modules with **no `<<<<<<<`/`=======`/`>>>>>>>` conflict markers** (grep count 0),
    `resolved: true`. **ScoreReport** — `score_report.json` (17 tests all `true`).
    **Policy note** — readable in `a4.py` and the resolved Open-questions block.
    **Conflicts recorded not resolved** — `merge_conflicts.json` records 3 conflicting
    agents (1, 2, 3) with apply stderr; first-applier seeds the merge, later overlaps dropped.

## Regression check

- Task 07's driver dispatch is shared with A0/A1/A2/A3. Trace one A1 trial after A4 is added → expect it still runs and scores unchanged : PRESERVED — `run` dispatches workflow (A1/A2/A3) FIRST via `_selects_workflow`, then A4 via `_selects_a4`, then A0 via `_selects_agent` (`container.py:383-389`); A4 added a new branch + a slug guard that runs BEFORE the A0 branch, leaving the existing branches' routing intact. `_run_workflow_arm`, `_run_a0`, `_run_agent`, and the A0/A1 constants are unchanged by the diff (A4 imports them, does not edit them). The A1/A2-A3 unit suites still pass and their live tests still skip cleanly in the same `check.sh` run (161 passed, 3 skipped). No REGRESSION.

## Residue

- A4 merge conflicts feed the robustness metric in Task 15; this task only records them, not analyses them.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: DONE
CONFIDENCE: high
SUMMARY: O1–O4 all SATISFIED — saved live evidence shows N=4 parallel agents (matched to A1's 4-task plan), a clean merged scored patch (resolved=true, no conflict markers, 3 conflicts recorded not resolved), the fixed prompt-only split pinned in `a4.py` and the resolved Open question, and `scripts/check.sh` green (uv frozen-clean, ruff/pyright clean, 161 passed / 3 opt-in-live skipped); the shared A0/A1/A2/A3 dispatch is PRESERVED (A4 added a slug-guarded branch ahead of A0, touching no existing path).
