# spec-builder

Implement a spec-planner plan — dispatch one sub-agent per task in its own isolated workspace, and gate every task through a semi-formal correctness review and a definition-of-done validation before it merges and is marked `Done`. Isolation runs on **jj or git** repos (jj preferred when both exist) and is vendored self-contained, so the plugin needs no other plugin installed.

Triggers on phrases like "build this plan", "implement the plan in .specs/plans/…", "run the spec-builder", "build the tasks in parallel" or "…sequentially". It consumes a spec-planner plan folder (`.specs/plans/YYYY-MM-DD-title/` — `plan.md`, the `NN-task.md` files, and the optional `certificates/` subfolder) and produces merged, reviewed, validated code, keeping the plan folder current as a live board so progress is readable from the files and an interrupted build resumes from them.

Its load-bearing rule: **a task is only `Done` when proven done — correct and complete — by an agent other than the one that built it.** Each task is built by its own sub-agent in its own isolated workspace; no task reaches `Done` until it passes two gates the implementer does not run on its own work — a semi-formal review for correctness, and a definition-of-done validation for completeness (discharging the task's done certificate, or its DoD checklist when none exists). The build walks the plan's dependency graph in waves, **parallel by default (max 4 concurrent agents)** or sequential.

## Install

```
/plugin marketplace add antstanley/skills
/plugin install spec-builder@skills
```

This plugin ships three skills: **spec-builder** (orchestrate the build), **semi-formal-review** (gate 1 — correctness), and **validate-done-certificate** (gate 2 — completeness).

## The pipeline

spec-builder is the execution end of a four-skill pipeline:

```
spec-creator → spec-planner → done-certificates → spec-builder
  (the spec)   (task graph +    (per-task proof     (build, review,
                definition of    protocol)            validate, merge)
                done)
```

It is **self-contained** — it needs no other plugin installed. Workspace isolation is vendored into the skill (one workspace per task, branched from an accumulating integration point, torn down after merge) and works on **both jj and git**: jj (jujutsu) is preferred when a repo supports both (a colocated repo), plain git repos use git worktrees. The standalone `jj-workspaces` skill is a richer companion when present, but not required. The two gate skills ship in this plugin. It is optimised for spec-planner plans — it reads the dependency table as the source of truth, the per-task `Implements / Produces / Pointers / Steps / Definition of done` fields, and the `certificates/` subfolder.

## spec-builder

The orchestrator. It lives at [`skills/spec-builder/SKILL.md`](skills/spec-builder/SKILL.md). It loads the plan, resolves execution settings (parallel/sequential, max agents — defaults parallel/4, overridable inline or via `.claude/spec-builder.local.md`), runs a bounded-concurrency wave scheduler over the dependency graph, and runs the per-task build loop (implement → review → validate → merge → mark `Done`). The method is under [`skills/spec-builder/references/`](skills/spec-builder/references/):

- [`references/orchestration.md`](skills/spec-builder/references/orchestration.md) — configuration, reading the plan into a schedule, the wave scheduler, the backend-neutral workspace lifecycle and the accumulating integration point, merge-conflict handling, and status bookkeeping.
- [`references/workspaces.md`](skills/spec-builder/references/workspaces.md) — the vendored, self-contained workspace-isolation method for both backends: detection (jj preferred, else git), sibling directory selection, the per-workspace commands, the baseline test run, merging and teardown, and an operation-mapping table (concept → jj → git).
- [`references/subagent-brief.md`](skills/spec-builder/references/subagent-brief.md) — assembling a context-sized brief from a task package (the package defines the context), the implementer prompt template, and the narrower reviewer/validator briefs.
- [`references/build-loop.md`](skills/spec-builder/references/build-loop.md) — the per-task lifecycle, the two gates and their pass/fail rules, merge-and-mark-done, handling a failed gate (feedback, bounded retries, parking), and the invariants.

## semi-formal-review

Gate 1 — **correctness**. The consolidated, self-contained form of the [reasoning-semiformally](../reasoning-semiformally) method, pointed at one question: does this implementation correctly and completely do what its task asked, without breaking what it touched? It runs a semi-formal certificate — premises, the 5-step function-resolution sequence, an execution trace, a regression check, a sufficiency check — and derives a `CORRECT / LIKELY_CORRECT / CONCERNS / BUGGY` verdict rather than declaring one. Run by an agent other than the implementer. It lives at [`skills/semi-formal-review/SKILL.md`](skills/semi-formal-review/SKILL.md):

- [`references/method.md`](skills/semi-formal-review/references/method.md) — the vendored, consolidated method: the certificate shape, the single step-by-step procedure used for every review regardless of model, the verdict rubric, and a worked example.

## validate-done-certificate

Gate 2 — **completeness**. The validating agent the [done-certificates](../spec-planner) skill authors for: it opens a task's blank done certificate, collects each obligation's named evidence, runs its checks, sets each status from real evidence, traces regressions, and derives a `DONE / PARTIAL / NOT_DONE` verdict by the certificate's rubric. When a task has no authored certificate, it derives obligations from the definition-of-done checklist and discharges those the same way. It validates; it does not author. Run by an agent other than the implementer. It lives at [`skills/validate-done-certificate/SKILL.md`](skills/validate-done-certificate/SKILL.md):

- [`references/validation-protocol.md`](skills/validate-done-certificate/references/validation-protocol.md) — how to discharge a certificate end to end, the no-certificate DoD fallback, and a worked discharge. It reuses the checkpoints vendored in [`semi-formal-review/references/method.md`](skills/semi-formal-review/references/method.md).

## Configuration

| Setting | Default | Where |
|---|---|---|
| `execution_mode` | `parallel` | `.claude/spec-builder.local.md` frontmatter, or inline in the request |
| `max_parallel_agents` | `4` | same (ignored when sequential) |
| `workspace_layout` | `sibling` | same (`sibling` \| `grouped` — see workspaces.md) |

An explicit request ("build sequentially", "max 2 agents") overrides the file and the defaults for that run.
