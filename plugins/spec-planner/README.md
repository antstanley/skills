# spec-planner

Plan the implementation of a specification — decompose a spec into a dependency-ordered graph of reviewable task packages, each with a definition of done.

Triggers on phrases like "plan the implementation", "break this spec into tasks", "what's the build order", "sequence the work", or "turn this change spec into a plan". The output is a plan **folder** at `docs/plans/YYYY-MM-DD-snake_case_title/` containing a `plan.md` (a Mermaid + dependency-table task graph where the table is the source of truth, the implementation order and milestones, and the standard `Assumptions / Decisions / Open questions` block) plus one markdown file per task package (`NN-snake_case_task.md`, numbered in build order) in hybrid form — structure, a step checklist, and a definition of done.

The plan's two load-bearing rules: every task package is an independently **reviewable** slice with a clear **definition of done** (drawn from the repo's own development guidelines), and the implementation order is biased so the work produces reviewable pieces early — if a feature is gated behind auth, auth is built first so the gated feature can be reviewed end to end.

It consumes any specification: a canonical spec set or change spec from **spec-creator**, or a spec written in another method or framework (PRD, RFC, OpenAPI). It is a companion to spec-creator — it follows that skill's voice and closing-block conventions, reads the `development-guidelines` page for each task's definition of done, and can call **spec-reviewer** to learn what is already built so it does not re-plan finished work.

## Install

```
/plugin marketplace add antstanley/skills
/plugin install spec-planner@skills
```

## Skill content

The skill lives at [`skills/spec-planner/SKILL.md`](skills/spec-planner/SKILL.md). Worked examples are under [`skills/spec-planner/evals/`](skills/spec-planner/evals/); the method and templates are under [`skills/spec-planner/references/`](skills/spec-planner/references/):

- [`references/task-decomposition.md`](skills/spec-planner/references/task-decomposition.md) — how to slice a spec into reviewable packages, the four dependency edge types (build / data / contract / review), and the reviewability-ordering method, with a worked example.
- [`references/plan-template.md`](skills/spec-planner/references/plan-template.md) — the plan-folder layout and two skeletons: `plan.md` (header, source/DoD baseline, Mermaid + table task graph, milestones, closing block) and the per-task `NN-…md` file (header, hybrid structure + step checklist + definition of done).
- [`references/checklist.md`](skills/spec-planner/references/checklist.md) — pre-handoff checklist: graph coherence, coverage, definition of done on every package, voice, cross-links.
