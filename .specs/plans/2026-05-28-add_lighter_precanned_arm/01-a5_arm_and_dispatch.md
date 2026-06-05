# Task 01 — A5 arm: schema + domain + arm module + dispatch

**Plan:** [plan.md](plan.md) · **Status:** Proposed

**Implements:** [changes/2026-05-28-add_lighter_precanned_arm.md](../../benchmark/specs/changes/merged/2026-05-28-add_lighter_precanned_arm.md) → §Proposed changes (`01-domain-model.md` §Arm slug `A0`–`A5`; `02-arms.md` §A5 — Lighter pre-canned) + §Type changes (the `ArmSlug` enum gains `"A5"`); Implementation notes steps 1–3.
**Depends on:** —
**Produces:** `"A5"` in the `ArmSlug` enum (`.specs/benchmark/specs/canonical-types.schema.json`) and in `ARM_SLUGS` (`benchmark/harness/domain.py`); `benchmark/harness/arms/a5.py` with the `A5 = Arm(...)` record + named constants + an `a5_prompt` builder; the public symbols exported from `benchmark/harness/arms/__init__.py`; a `_selects_a5` + `_run_a5` pre-canned (non-recursive) dispatch branch in `benchmark/harness/backends/container.py`. `Arm(slug="A5")` validates; A0–A4 dispatch is unchanged.
**Pointers:** mirror `benchmark/harness/arms/a0.py` (plain-agent record + recipe) and `benchmark/harness/arms/a4.py` (slug, model, budget, prompt-template shape); `benchmark/harness/domain.py:101` (the `ARM_SLUGS` comment) `:102` (the tuple); the `ArmSlug` `$def` in `.specs/benchmark/specs/canonical-types.schema.json:22`; in `container.py`: `run:363`, `_selects_a4:841` (matched-first pattern), `_run_a0:398` (single-call shape), `_run_workflow_arm:678` (artifact capture + `extract_gate_events` + `last_gate_events`), `_extract_patch:1086` (`exclude_artifacts`), `_capture_artifacts:1169`, `_run_agent:1009` (single `claude -p` invocation). `extract_gate_events` (`benchmark/harness/arms/a2_a3.py:370`).

## Steps

- [ ] Schema: add `"A5"` to the `ArmSlug` enum (`.specs/benchmark/specs/canonical-types.schema.json`, the `ArmSlug` `$def`) and update its `description` from "five" to "six".
- [ ] Domain: add `"A5"` to `ARM_SLUGS` (`benchmark/harness/domain.py`) and update the "five fixed / closed set" comment to reflect six.
- [ ] New `benchmark/harness/arms/a5.py`: a module docstring tracing to the change spec's §A5; `A5_SLUG = "A5"`; the `A5 = Arm(slug=A5_SLUG, pluginsEnabled=[], gatesEnabled=True, specProvided=False, executionMode="single")` record; named constants `A5_MODEL` (reuse the plain model, e.g. `A0_MODEL`), `A5_MAX_BUDGET_USD = 5.0`, `A5_RUN_TIMEOUT_SECONDS = 600`, and `A5_INSTRUCTION` — the FIXED pre-canned prompt that (a) implements the feature in place AND (b) writes ONE done-certificate under `.specs/plans/.../certificates/` with a real `VERDICT:` line (DONE/PARTIAL/NOT_DONE or CORRECT/LIKELY_CORRECT/CONCERNS/BUGGY) so `extract_gate_events` finds ≥ 1 `GateEvent`; an `a5_prompt(problem_statement)` builder. Mirror the shape of `a0.py` / `a4.py`.
- [ ] Export `A5` and the public symbols (`A5_SLUG`, `A5_MODEL`, `A5_MAX_BUDGET_USD`, `A5_RUN_TIMEOUT_SECONDS`, `A5_INSTRUCTION`, `a5_prompt`) from `benchmark/harness/arms/__init__.py` (and `__all__`).
- [ ] `container.py` dispatch: add `_selects_a5(arm_or_solver)` (routes by the A5 slug) and call it in `run()` BEFORE `_selects_agent` (like A4), routing to a new `_run_a5`.
- [ ] `_run_a5`: provision a fresh container with NO plugin mounts, make the base commit, run the auth probe, run ONE bounded pre-canned `claude -p` (no `--plugin-dir`) under `A5_MAX_BUDGET_USD` / `A5_RUN_TIMEOUT_SECONDS`, extract the CODE-only candidate patch (`exclude_artifacts=True`, like the workflow arms), capture the artifacts, build the `ArtifactBundle` (with `certificateArtifacts`), and populate `self._last_gate_events = extract_gate_events(cert_files, trial_id=self._trial_id)`. Reuse the existing helpers; add no new capture path.
- [ ] Name every limit a `SCREAMING_SNAKE_CASE` constant (the budget cap and timeout live in `a5.py`; reuse `container.py`'s existing setup/auth-probe timeouts).

## Definition of done

- [ ] `from benchmark.harness.arms import A5` imports an `Arm` with `slug="A5"`, `pluginsEnabled=[]`, `gatesEnabled=True`, `specProvided=False`, `executionMode="single"`, and `Arm(slug="A5")` validates against the (updated) canonical schema.
- [ ] `"A5"` is in `ARM_SLUGS`; the schema `ArmSlug` enum and `ARM_SLUGS` agree on the six-member set; the "five → six" comment/description is updated in both places.
- [ ] `ContainerRunBackend._selects_a5(A5)` is `True` and `_selects_agent(A5)` / `_selects_workflow(A5)` / `_selects_a4(A5)` are all `False`; `run()` routes A5 to `_run_a5` and A0–A4 routing is unchanged (the A4-first / workflow-by-slug dispatch still holds).
- [ ] `_run_a5` runs a SINGLE non-recursive `claude -p` (no `--plugin-dir`, no `spec-*` mount), excludes `.specs/` from the candidate patch, captures the certificates, and threads them through `extract_gate_events` onto `last_gate_events`.
- [ ] Meets the repo definition of done (ruff lint+format, pyright standard, named-constant limits — see plan.md baseline). The full pytest run is task 02's gate, but `benchmark/harness` must import clean and pyright-clean here.
- [ ] Reviewable: a reviewer reads `a5.py` + the `_run_a5` branch and confirms the flow is pre-canned (one call, no recursion) and that a certificate it writes would map to a `GateEvent`.
