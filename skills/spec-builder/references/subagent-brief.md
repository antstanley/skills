# Sub-agent brief — context assembly and the implementer prompt

Each task is built by its own implementer sub-agent in its own isolated workspace (a jj
workspace or a git worktree — see [`workspaces.md`](workspaces.md)). The agent sees *only*
what its brief carries, so the brief must hold **enough context to complete
the task and no more** — the spec-planner task file already named exactly that context.
This file is how the orchestrator turns a task file into a self-contained brief.

The guiding rule: **the task package defines the context.** spec-planner wrote each task's
`Implements`, `Depends on`, `Produces`, `Pointers`, `Steps`, and `Definition of done`
precisely so a builder needs nothing outside them. Assemble the brief from those fields;
do not dump the whole repo or the whole spec into the sub-agent.

---

## What to assemble for one task

From the plan folder, gather for task `NN`:

| Source | What to pull | Why the builder needs it |
|---|---|---|
| `NN-<task>.md` `Produces` | the reviewable artifact to deliver | the goal — what "built" looks like |
| `NN-<task>.md` `Steps` | the implementation checklist | the plan of work, in order |
| `NN-<task>.md` `Implements` | spec page §headings | the authority for behavior — read these spec sections |
| `NN-<task>.md` `Pointers` | code entry points (`file:line`) | where to touch the code |
| `NN-<task>.md` `Definition of done` | the DoD checklist | the bar the work is judged against (and the gates) |
| `plan.md` DoD baseline | the repo's development-guidelines source | the testing / lint / limits discipline every task inherits |
| The referenced spec sections | the actual prose from `Implements` | behavior detail — pull the sections, not the whole spec set |
| `certificates/NN-<task>.md` | **summary only** — that a certificate exists | so the builder knows the completeness bar; do **not** hand over the certificate body |

**Withhold the certificate's evidence/checks from the implementer.** The certificate is
the validator's protocol. A builder who reads "run `lock.test.ts › rejects wrong
passphrase`" may write code that passes that one named test rather than the general
behavior. The builder gets the *definition of done* (the claim); the validator holds the
*certificate* (the proof). This keeps the two genuinely independent.

Resolve spec-section links from the plan folder (from a repo-wide plan, `../../…` for a
global page and `../../<package>/specs/…` for a per-package page; from a plan under
`.specs/<package>/plans/`, the package's own spec is `../../specs/…` and a global page
`../../../…`) and include the relevant text in the brief so
the sub-agent need not go hunting.

---

## The implementer prompt template

Dispatch the sub-agent (general-purpose, or a feature-dev implementer) into its workspace
with a brief shaped like this — adapt, do not paste verbatim:

```
You are implementing one task of a larger plan, in an isolated workspace. Build ONLY
this task. Do not start work the task does not name; do not touch files outside its scope.

## Workspace
Work in: <workspace-path>   (an isolated jj workspace / git worktree — just edit files here)
Your base already contains the completed work of this task's dependencies. Run the
project's test suite once before you start to confirm a green baseline; if it is red,
stop and report — do not build on a broken base.

## Task NN — <title>
Produces (your goal): <Produces line — the reviewable artifact you must deliver>

Implements (the authority for behavior): <spec page §headings>
<the relevant spec-section text, pulled in so you need not search for it>

Pointers (where to touch): <file:line entry points>

## Steps
<the task's Steps checklist, in order>

## Definition of done — the bar your work must meet
<the task's Definition of done checklist, including the Reviewable line>
Repo definition of done (inherited): <tests / lint / format / named-constant limits,
from plan.md's baseline — name the actual commands, e.g. `npm test`, `npm run lint`>.

## How you are judged (so build for it, do not game it)
After you report done, a SEPARATE agent reviews your diff semi-formally for correctness
and regressions, and a SEPARATE validator checks it against the definition of done. Write
the code the task actually needs — general, correct behavior — not code aimed at a
specific named test. Add or update tests as the definition of done requires.

## Report back
When done, report: the files you changed, how each Definition-of-done item is met, the
result of the project's test/lint commands you ran, and anything you could not complete.
Do not mark the task done yourself — that is the gates' decision.
```

### Sizing the brief

- **Too little context** — the agent guesses at behavior the spec already settled. Pull
  the `Implements` sections in full.
- **Too much context** — the whole spec set or unrelated tasks. The agent loses the thread
  and edits outside scope. Carry only this task's fields and its dependencies' *outputs*
  (already in its workspace base), not their task files.
- **Dependencies are in the base, not the brief.** The builder does not re-read a
  dependency's task file; that task's code is already in the workspace it branched from.
  Mention a dependency only when this task's `Pointers` reach into code the dependency
  produced.

---

## Reviewer and validator briefs

The two gate agents are briefed more narrowly — they get the diff and the contract, not
the implementer's reasoning:

- **Reviewer (semi-formal-review):** the workspace diff, the task's `Produces` and `Steps`
  (what it was meant to do), and the instruction to run the semi-formal certificate and
  return `CORRECT / LIKELY_CORRECT / CONCERNS / BUGGY`. It must not be the implementer.
- **Validator (validate-done-certificate):** the workspace diff, the task's `Definition of
  done`, and the certificate file if one exists; the instruction to discharge it and
  return `DONE / PARTIAL / NOT_DONE`. It must not be the implementer, and ideally not the
  reviewer either, though the orchestrator may run both gates itself since it did not write
  the code.

See [`build-loop.md`](build-loop.md) for how the three fit together and what happens on
each verdict.
