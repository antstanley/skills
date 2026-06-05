# Change: Kanban plan-folder layout (backlog / in-progress / blocked / done)

**Status:** Proposed · **Date:** 2026-06-05 · **Owner:** Ant Stanley · **Target:** Repo-wide — `plugins/spec-planner` + `plugins/spec-builder` (the plan-folder layout contract)

Replace the flat plan folder — `plan.md` plus `NN-task.md` files and a `certificates/` subfolder at the root, with per-task state carried in a `**Status:**` field — with a **kanban board of folders**. The plan folder keeps `plan.md` at its root and gains four task subfolders, `backlog/`, `in-progress/`, `blocked/`, and `done/`; each task file and its certificate physically **move** between them as work progresses, so a task's folder _is_ its status. The per-task `Status:` field is retired (folder location supersedes it); `plan.md`'s own plan-level `Status` stays. spec-planner authors every new task into `backlog/`; spec-builder is the sole agent that moves files between subfolders, on the main tree, as it walks the build. This change touches both plugins' `SKILL.md`, every layout-bearing reference file, all four `evals.json` fixtures, both `plugin.json` descriptions, and both plugin READMEs; `semi-formal-review` is the only skill left untouched.

---

## Motivation

The plan folder already calls itself a "live board," but the board is encoded indirectly — you read each task file's `**Status:**` field to know where it stands, and the orchestrator edits that field in place to move a task forward. The state is real but invisible at a glance: a `ls` of the folder shows every task jumbled together regardless of progress, and "what is left to do" requires opening files. A board whose columns are folders makes the same state directly legible — `ls backlog/` is the to-do list, `ls in-progress/` is what is in flight, `ls blocked/` is what is parked, `ls done/` is what shipped — and makes resume after interruption a directory listing rather than a field-parse across many files.

The change also removes a class of drift. Today the per-task `Status:` field is a second source of truth that can disagree with reality (a merged task whose field was never bumped); the certificate lives in a separate `certificates/` tree that must be kept in lockstep with its task by number. Folder-as-status collapses both: a task and its certificate move together as a unit, and there is exactly one place — the parent directory — that says where a task stands. The cost is mechanical (every layout-bearing doc, fixture, and description must be reworded) and one genuine design question — how `plan.md` keeps referring to task files that now move — which this spec resolves by referencing tasks by number rather than by path.

---

## Affected spec pages

The plugins are their own canonical definition: the layout contract lives in the plugin `SKILL.md` files and their reference docs, not in a `.specs/` page. The "canonical pages" this change targets are therefore the plugin source files below. (`plugins/` is canonical; the flat `skills/` tree is regenerated from it by `scripts/sync-skills.sh` and gated by `scripts/check.sh` — see Implementation notes.)

| Canonical file                                                                                         | Nature of change                                                                                                                                                                                  |
| ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `plugins/spec-planner/skills/spec-planner/SKILL.md`                                                    | Phase 4 authors into `backlog/`; Phase 5 link rules gain a depth level and verify against current subfolders; §Adding done certificates drops the `certificates/` subfolder; frontmatter reworded |
| `plugins/spec-planner/skills/spec-planner/references/plan-template.md`                                 | New folder tree; Status-lifecycle table becomes folder-based; task skeleton drops `Status:` and re-depths links; dependency table references tasks by number (no path link)                       |
| `plugins/spec-planner/skills/spec-planner/references/checklist.md`                                     | Folder-structure, graph-coherence, cross-link, and done-certificate checks rewritten for subfolders + number references                                                                           |
| `plugins/spec-planner/skills/spec-planner/references/task-decomposition.md`                            | "one numbered file per task" → authored into `backlog/`; the "files sort in build order" rationale reconciled with NN-as-identity                                                                 |
| `plugins/spec-planner/skills/done-certificates/SKILL.md`                                               | §Where the certificate lives: co-located `NN-task-certificate.md`, no `certificates/` subfolder; ownership boundary redrawn; next-free-NN spans the four folders                                            |
| `plugins/spec-planner/skills/done-certificates/references/certificate-template.md`                     | Header links become same-dir (`NN-task.md`) + `../plan.md`                                                                                                                                        |
| `plugins/spec-builder/skills/spec-builder/SKILL.md`                                                    | Core principle, "optimised for" line, Phase 1 read, Phase 4 status writes become folder moves                                                                                                     |
| `plugins/spec-builder/skills/spec-builder/references/orchestration.md`                                 | Reading the plan, the wave scheduler's done/running/ready sets, and §Status bookkeeping become directory operations; resume reads folders                                                         |
| `plugins/spec-builder/skills/spec-builder/references/build-loop.md`                                    | "Mark In progress / Done" become moves; certificate path is the task's sibling; parked task moves to `blocked/`                                                                                              |
| `plugins/spec-builder/skills/spec-builder/references/subagent-brief.md`                                | Spec-link depth +1; certificate read from the task's current subfolder                                                                                                                            |
| `plugins/spec-builder/skills/spec-builder/references/workspaces.md`                                    | State that folder moves are a main-tree operation by the orchestrator, never inside a task workspace                                                                                              |
| `plugins/spec-builder/skills/spec-builder/references/portability.md`                                   | Sequential fallback's "update the plan board" = the same moves                                                                                                                                    |
| `plugins/spec-builder/skills/validate-done-certificate/SKILL.md` + `references/validation-protocol.md` | Certificate read from the task's current subfolder (not `certificates/`); cert naming; main-tree view                                                                                             |
| Both `.claude-plugin/plugin.json` descriptions                                                         | "live board / Status" wording → folder-as-status (manual edit — not synced, not checked)                                                                                                          |
| Both plugin `README.md` files                                                                          | Intro / pipeline / build-loop prose reworded (manual edit — not synced)                                                                                                                           |
| 4 × `evals.json` (spec-planner, done-certificates, spec-builder, validate-done-certificate)            | Golden `expected_output`s asserting the flat layout, `certificates/`, and `Status:`-field flips rewritten                                                                                         |

**Out of scope (do not edit):** `semi-formal-review` (path-agnostic — consumes task _content_ + a diff), and the vendored reasoning-method triangle `done-certificates/references/semiformal-method.md` ↔ `semi-formal-review/references/method.md` ↔ the `reasoning-semiformally` plugin. The change gives no reason to touch the 5-step sequence or verdict rubric.

---

## Proposed changes

Each block is the prose as it should read in the plugin docs after merge. The change is cross-cutting, so blocks are organised by rule and name the files each lands in.

### A — The plan folder is a board of folders

_Lands in: spec-planner `SKILL.md` Phase 4, `plan-template.md` tree, both READMEs._

> A plan is a **folder**. `plan.md` sits at its root; the task packages live in four status subfolders that double as a kanban board:
>
> ```
> .specs/plans/2026-05-22-add_auth_flow/
> ├── plan.md                       ← overview: graph, order, closing block (stays at root)
> ├── backlog/                      ← not started
> │   ├── 01-passphrase_lock.md
> │   ├── 01-passphrase_lock-certificate.md
> │   └── 02-entry_store.md
> ├── in-progress/                  ← being built
> │   └── 03-app_shell.md
> ├── blocked/                      ← parked on a failed gate (blocks dependents)
> └── done/                         ← merged, both gates passed
>     └── 04-editor.md
> ```
>
> A task's **status is the subfolder it sits in.** A new plan has every task in `backlog/` and nothing elsewhere. The two-digit `NN` is the task's identity everywhere in the plan and is append-only; a task keeps its number as it moves between subfolders. spec-planner creates `backlog/` and writes every task into it; `in-progress/`, `blocked/`, and `done/` are created by spec-builder when the first task moves into them.

### B — Status is folder location, not a field

_Lands in: `plan-template.md` Status-lifecycle section + task skeleton + Notes; spec-planner `SKILL.md` Phase 4; spec-builder `SKILL.md` + `orchestration.md` §Status bookkeeping + `build-loop.md`._

> Per-task status is no longer a `**Status:**` field. A task file carries its `**Plan:**` back-link but no status line; its lifecycle state is the subfolder it sits in — `backlog/` (Todo) → `in-progress/` (in flight) → `done/` (Done), or `blocked/` when a gate parks it. `plan.md` keeps its own plan-level `**Status:**` (`Draft` → `Accepted` → `In progress` → `Done`), which spec-builder **recomputes from the subfolders** after each transition — `In progress` once any task has left `backlog/`, `Done` once every task is in `done/` — and writes back; it is the only field the builder writes to `plan.md`.
>
> A task that fails a gate past its retry bound is **parked**: it moves to `blocked/` and gains a `**Blocked:** <reason>` line in its header. A parked task blocks its dependents, so the unreachable-subgraph report is a pure `ls blocked/` (plus the dependents that transitively need those tasks) — no per-file marker scan required.

### C — A certificate co-locates with its task and moves with it

_Lands in: done-certificates `SKILL.md` §Where the certificate lives + §When invoked; `certificate-template.md` header; spec-planner `SKILL.md` Phase 4.5/5; `checklist.md` done-certificates section._

> A done certificate is written **beside its task**, named `NN-snake_case_task-certificate.md` (the `-certificate` suffix avoids colliding with the task's own `NN-snake_case_task.md` in the same folder). It is authored into `backlog/` alongside its still-unbuilt task and moves with the task through `in-progress/` (or `blocked/`) and into `done/` as a single unit. There is no dedicated `certificates/` subfolder.
>
> Because the certificate and task always share a directory, their cross-links are same-directory and survive every move unchanged: the certificate links to its task as `[NN-…md](NN-…md)` and to the plan as `[plan.md](../plan.md)`; the task header carries `**Certificate:** [NN-…-certificate.md](NN-…-certificate.md)`. done-certificates authors certificates into `backlog/` and owns their content; spec-builder owns moving them (with their tasks) between subfolders.

### D — `plan.md` refers to tasks by number, not by path

_Lands in: `plan-template.md` dependency table + Notes; spec-planner `SKILL.md` Phase 5; `checklist.md` graph-coherence._

> The dependency table is the source of truth and keys every task by its `NN` number. Because a task file moves between subfolders as it is built, the table does **not** hyperlink the task by path — it names it by number and title (`01 · passphrase lock`). A reader or tool finds a task's file by its number across the four subfolders (`*/01-*.md`). This keeps `plan.md` stable: apart from its recomputed plan-level `Status`, it is never rewritten when a task moves, so parallel task transitions never contend on it. (`plan.md`'s primary reader is an agent, so dropping clickable task links costs nothing.)

### E — Relative-link depth: one level deeper, but move-stable

_Lands in: spec-planner `SKILL.md` Phase 5 step 2; `checklist.md` Cross-links; `subagent-brief.md` spec-link resolution; `plan-template.md` task skeleton._

> A task file now sits one directory deeper than before, so its links resolve from its subfolder: the `**Plan:**` back-link is `../plan.md`, a global spec page is `../../../foo.md` (was `../../foo.md`), and a per-package page is `../../../<package>/specs/NN-name.md`. Because `backlog/`, `in-progress/`, `blocked/`, and `done/` are all at the same depth, these links are authored **once** and stay correct as the task moves between subfolders — the depth never changes. (The depth rule is stated in four places — the planner's Phase 5, the checklist, the implementer brief, and the planner eval — which must all gain the extra `../` identically, or the builder resolves spec links at a different depth than the planner verifies.)

### F — The orchestrator moves files, on the main tree, as one transaction

_Lands in: spec-builder `orchestration.md` §Status bookkeeping + Workspace lifecycle; `build-loop.md` steps 1 & 4 + Invariants; `workspaces.md`._

> Folder-as-status is authoritative **only on the orchestrator's main working tree**. Task sub-agents work in isolated workspaces that hold code, not the plan folder; they never move task files. A status transition is a single serialized step the orchestrator performs on main: on dispatch it moves `backlog/NN-*.md` (and its `-certificate.md`) into `in-progress/`; on both-gates-pass-and-merge it moves them into `done/`; on a park it moves them into `blocked/`. The move into `done/` is the commit point for "Done" — it is the last action, after the code merges into the integration point. After each transition the orchestrator recomputes `plan.md`'s plan-level `Status` from the subfolders and writes only that field back. The gates read each task's and certificate's content from the **main-tree** location, never from a sub-agent's stale workspace copy.
>
> On resume, **folder membership is authoritative**: `done/` holds the completed tasks, `backlog/` the not-yet-started, `in-progress/` the in-flight, and `blocked/` the parked — each task is in exactly one. If an interrupted transition left a task merged but not yet moved, the resume repairs the folder from the integration point, never the reverse.

### G — The planner→builder discovery contract

_Lands in: spec-planner `SKILL.md` Phase 4 + Phase 5; spec-builder `SKILL.md` Phase 1 + `orchestration.md` "Reading the plan into a schedule"._

> spec-planner guarantees the initial condition: on a freshly authored plan every task (and its certificate) is in `backlog/`, and `in-progress/`, `blocked/`, and `done/` do not yet exist. spec-builder enumerates the full task set as the union of `backlog/`, `in-progress/`, `blocked/`, and `done/` (treating a missing subfolder as empty) and builds the DAG from `plan.md`'s dependency table. The `ready` set is the tasks in `backlog/` whose `Depends-on` are all in `done/`; `running` is `in-progress/`; the parked set is `blocked/`; `done` is `done/`.

### H — A layout marker distinguishes kanban from legacy-flat plans

_Lands in: spec-planner `plan-template.md` `plan.md` header; spec-builder `orchestration.md` "Reading the plan"._

> `plan.md`'s header carries a `**Layout:** kanban` field, and spec-builder also infers `kanban` from the presence of a `backlog/` subfolder. A plan with neither — task files flat at the folder root — is **legacy-flat**, and the builder **migrates it in place** rather than reading it: `Status: Done` → `done/`, `In progress` → `in-progress/`, `Todo` → `backlog/`, relocating each `certificates/NN-*.md` to `NN-*-certificate.md` beside its task. The seven existing flat plans in `.specs/plans/` are migrated this way in one pass at merge time. The marker exists so the builder never mistakes a flat plan for an empty one (a root glob would otherwise find only `plan.md`).

---

## Implementation notes

What an implementing agent needs beyond the blocks above.

**Order of work.**

1. **spec-planner first** (the creator defines the new shape): `SKILL.md` (Phase 4 ~L75, Phase 5 ~L96/L99, §Adding done certificates ~L119, frontmatter L3) → `plan-template.md` (tree L5–12, Status lifecycle L20–37, task skeleton L130–159, dependency table L81–91, Notes L170) → `checklist.md` (folder structure, graph coherence, Cross-links, Done-certificates sections) → `task-decomposition.md` (the "one numbered file" line + the build-order rationale) → done-certificates `SKILL.md` (§Where the certificate lives) + `certificate-template.md` (header links L40, L121).
2. **spec-builder next** (the consumer reads + moves): `SKILL.md` (core principle rule 3 L36, "optimised for" L60, Phase 1 L118, Phase 4 L151) → `orchestration.md` (Reading the plan L38–50, wave scheduler L56–85, §Status bookkeeping L140–161) → `build-loop.md` (step 1 L22, step 3 cert path L50, step 4 L63–73, parking L92, Invariants L104–114) → `subagent-brief.md` (spec-link depth + cert path) → `workspaces.md` (assert main-tree-only moves) → `portability.md` (fallback board update) → validate-done-certificate `SKILL.md` + `validation-protocol.md` (Inputs cert path, `State:` field).
3. **Fixtures and descriptions:** the four `evals.json` golden outputs, both `.claude-plugin/plugin.json` descriptions, both plugin `README.md` files.
4. **Re-sync and migrate** (below).

**The sync obligation (CI-gated).** `scripts/sync-skills.sh` regenerates the flat `skills/` tree with `cp -R` of each whole skill directory (only `evals/` stripped), and `scripts/check.sh` (wired into CI and the pre-push hook) fails on drift. Therefore **every** edited `SKILL.md` _and reference file_ must be followed by a `scripts/sync-skills.sh` run — not just `SKILL.md`. The files **not** covered by the sync (and therefore **not** caught by `check.sh`) are the two `plugin.json` descriptions, the two plugin READMEs, and the `evals/` fixtures — these are a silent-staleness surface and must be edited by hand.

**The shared worked example.** The `01-passphrase_lock …` journal-app example is duplicated across ~8 files (`plan-template.md`, `task-decomposition.md`, `certificate-template.md`, and the four eval fixtures). Update it identically everywhere so no stale copy reintroduces the flat layout.

**Migration of existing plans.** This repo dogfoods its own workflow: `.specs/plans/` holds seven flat-layout plan folders (one, `2026-05-27-spec_workflow_benchmark/`, with a `certificates/` subfolder). All seven are migrated in place at merge time by the rule in block H — mapping each task's real `Status:` value to its subfolder (the benchmark plans are partly `Done`/`In progress`, so the mapping must read the actual fields, not assume `backlog/`) and relocating the one `certificates/` subfolder to co-located `NN-*-certificate.md` files. The `blocked/` folder is created only when a build parks a task.

**The four-folder ripple.** Adding `blocked/` makes the board four columns, so the "each task in exactly one subfolder" invariant (checklist), the enumeration union (builder), and the four eval golden outputs all assert four buckets; the unreachable-dependents report becomes `ls blocked/` rather than a per-file marker scan.

---

## Merge plan

Folding this change spec into the canonical definition = applying it to the plugin source and regenerating the derived artifacts.

1. Apply each `Proposed changes` block (A–H) to the plugin files named under it, in the order above.
2. Run `scripts/sync-skills.sh`; confirm `scripts/check.sh` passes (no `skills/` drift).
3. Update the four `evals.json` golden outputs, both `plugin.json` descriptions, and both plugin READMEs by hand.
4. Migrate the seven existing `.specs/plans/` folders in place (map each task's `Status:` to its subfolder; relocate the one `certificates/` subfolder to `NN-*-certificate.md`).
5. Flip this file's `**Status:**` to `Merged`, add `**Merged:** YYYY-MM-DD`, and move it to `.specs/changes/merged/`.
6. Update `.specs/README.md`: move this entry from the pending list to the merged area.

---

## Assumptions and open questions

**Assumptions**

- `plan.md` stays at the plan-folder root and never moves; only task files and their certificates move. The plan-level `**Status:**` field is a different axis from per-task status and is retained.
- git/jj do not track empty directories, so `in-progress/`, `blocked/`, and `done/` are created lazily by the builder rather than pre-created with `.gitkeep` placeholders that the task glob would then have to exclude.
- A task and its certificate always move together, so their same-directory cross-links never dangle except during the single atomic move the orchestrator performs.
- The harness still dispatches one sub-agent per task into an isolated workspace; nothing about isolation, the integration point, or the two gates changes — only how the plan folder records state.

**Decisions**

- _Link strategy (the pivotal choice)._ **`plan.md` references tasks by number; files are found by glob, not by path link.** The alternative — rewriting `plan.md`'s dependency-table link to a task on every move — turns `plan.md` into a high-churn shared file that up-to-4 parallel transitions contend on, and makes each transition a multi-file transaction that can half-apply on a crash. Referencing by number removes that contention entirely; the trade-off — the dependency table loses clickable task links — is acceptable because `plan.md`'s primary reader is an agent, not a human browser.
- _Status representation._ **Drop the per-task `Status:` field; folder location is the sole source of truth.** Keeping it as a mirror reintroduces exactly the drift the change removes. `plan.md`'s plan-level `Status` is unaffected because `plan.md` does not move.
- _Certificate placement._ **Co-locate as `NN-task-certificate.md` and move with the task.** Same-directory cross-links are move-stable (zero rewrites per transition), which is the cleanest behaviour; the `-certificate` suffix resolves the name collision with the task file in the shared folder.
- _Parked state._ **A parked task moves to a dedicated `blocked/` folder** (a fourth column). This makes the eval-tested "report unreachable dependents" behaviour a pure `ls blocked/` query and keeps each task in exactly one folder, rather than overloading `in-progress/` with a marker scan.
- _Who moves files._ **The orchestrator, on the main tree, as the last step of a serialized transaction.** Sub-agents never touch the plan folder; gates read content from main. Folder membership is authoritative on resume.
- _Plan-level Status._ **spec-builder recomputes `plan.md`'s `Status` from the subfolders after each transition and writes back only that field** — `In progress` once any task has left `backlog/`, `Done` once all are in `done/`. With path links dropped, this is the single thing the builder ever writes to `plan.md`.
- _Back-compat / migration._ **Migrate the seven existing flat plans in place at merge time**, mapping each task's real `Status:` to its subfolder. Going forward the builder detects a legacy-flat plan (no `Layout: kanban` marker and no `backlog/`) and migrates it in place rather than reading two shapes indefinitely or globbing it empty.

**Open questions**

(None — the five questions raised at drafting are resolved in the Decisions above: a fourth `blocked/` folder for parked tasks; number-only task references in `plan.md` (its reader is an agent); migrate the seven existing flat plans in place at merge time; the `-certificate.md` suffix; and spec-builder recomputing `plan.md`'s `Status` from the subfolders.)
