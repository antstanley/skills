# Workspace isolation (jj and git)

The vendored, self-contained method for isolating each task in its own working copy.
spec-builder builds one task per isolated workspace so parallel sub-agents never step on
each other and a failed attempt can be abandoned without touching the rest. This file
makes the plugin self-contained — it does not require the standalone `jj-workspaces`
skill, though that skill is a richer companion when installed.

**Two backends, one model.** jj (jujutsu) and git both give isolated working copies as
sibling directories. The orchestration concept is the same for both — an **integration
point** that accumulates completed tasks, and one workspace per in-flight task branched
from it. Only the commands differ. **jj is preferred when a repo supports both** (a
colocated repo has both a `.jj` and a `.git`); detection checks jj first.

**Core principle:** sibling-directory workspaces + a clean shared base + a verified-green
starting point = reliable parallel isolation.

**The plan folder is never in a workspace.** A task workspace holds only the repo's code; the
plan folder (`plan.md` plus the `backlog/`/`in-progress/`/`blocked/`/`done/` subfolders) stays
on the orchestrator's **main working tree**. Moving a task file and its `-certificate.md`
between subfolders — the kanban status transition — is a main-tree-only operation the
orchestrator performs; a sub-agent never moves a task file or touches the plan folder. The
gates read each task's and certificate's content from the main-tree location, never from a
workspace copy.

---

## Detection — which backend, jj preferred

Run, in order, from inside the repo:

```bash
jj workspace root 2>/dev/null            # exits 0 → jj (use this, even if .git also exists)
git rev-parse --is-inside-work-tree 2>/dev/null   # true → plain git (jj absent)
```

- **`jj workspace root` exits 0** → **jj backend.** A colocated repo (both `.jj` and
  `.git`) still resolves here; prefer jj for its revision semantics and conflict-free
  parallel edits.
- **Else git reports a work tree** → **git backend.** Use git worktrees.
- **Neither** → not a VCS repo. Surface that to the user rather than guessing; offer
  `jj git init --colocate` or `git init` if they want one.

Announce the chosen backend before building ("This repo is jj-managed — using jj
workspaces" / "This repo is git — using git worktrees").

---

## Directory selection (both backends)

Workspaces/worktrees live **outside** the main repo's working tree — sibling paths are
idiomatic; nesting confuses both tools. Resolve the location in this order:

1. **Existing layout.** If a sibling `../<repo>-workspaces/` (or `.<repo>-workspaces/`)
   already exists, honour it. `jj workspace list` / `git worktree list` reveal an existing
   convention.
2. **Project convention.** `grep -iE "workspace|worktree" CLAUDE.md` and the
   `workspace_layout` setting in `.claude/spec-builder.local.md` (`sibling` | `grouped`).
3. **Default.** Sibling paths: `../<repo>-task-NN`. Use `grouped`
   (`../<repo>-workspaces/task-NN/`) when several are in flight and you want them gathered.

There is no `.gitignore` concern — workspaces sit outside the tree.

---

## jj backend

### Clean base and the integration revision

The **integration revision** is the running jj revision that holds every task merged
`done` so far. Establish a clean base, then anchor the integration revision to it:

```bash
jj new                 # fresh empty commit → clean shared base (no in-flight edits leak in)
# integration revision := current @  (or a revision the user names, via -r below)
```

### Add a task workspace (branched from the integration revision)

A task's workspace must start from a base that already contains its dependencies' work —
the current integration revision:

```bash
jj workspace add -r <integration-rev> ../<repo>-task-NN     # workspace name = task-NN
```

Parallel tasks in one wave share the same integration revision as their base (the ready
set guarantees they don't depend on each other), so they branch from the same point and
cannot see each other's in-flight edits.

### Prepare and verify (in the workspace)

```bash
cd ../<repo>-task-NN
jj workspace root                       # sanity-check: prints the new path
# install deps if present: npm install / cargo build / pip install -r / poetry install / go mod download
# run the project's suite once → must be green before handing to the sub-agent
```

A red baseline is reported, not papered over — later failures must be attributable.

### Merge a completed task and advance the tip

Once both gates pass, fold the workspace revision into the integration tip and advance it:

```bash
jj new <integration-rev> <task-rev>        # combined merge change, or:
jj rebase -s <task-rev> -d <integration-rev>
# integration revision := the result
```

Because parallel tasks branched from the same base, the second and later merges of a wave
land on an integration tip that already moved; jj usually does this cleanly. On a
conflict, see *Merge conflicts* in [`orchestration.md`](orchestration.md).

### Stale working copy

If a merge rewrote a revision another workspace was editing, its next `jj` command reports
it stale. Resolve with `jj workspace update-stale` — never force-reset; jj preserves prior
state in a recovery commit if needed.

### Teardown

```bash
jj workspace forget task-NN && rm -rf ../<repo>-task-NN     # after a successful merge
jj abandon <task-rev>                                       # first, for an abandoned attempt, then forget + rm
```

---

## git backend

The same model with worktrees and an **integration branch** standing in for the
integration revision. The orchestrator's main working tree stays on the integration
branch; that is where merges happen.

### Clean base and the integration branch

```bash
# from a clean main working tree on the base commit (or a ref the user names):
git switch -c spec-builder/integration        # the integration branch; its tip is the integration point
```

If the working tree is dirty, stash or commit first — the base must be clean so nothing
in-flight leaks into the workspaces.

### Add a task worktree (branched from the integration tip)

```bash
git worktree add -b spec-builder/task-NN ../<repo>-task-NN spec-builder/integration
```

Each task gets its own branch off the **current** integration tip, so its base holds its
dependencies' merged work. Parallel tasks branch from the same tip. A branch checked out
in a worktree is locked, so two worktrees can't share one — one branch per task is the rule.

### Prepare and verify (in the worktree)

```bash
cd ../<repo>-task-NN
git rev-parse --show-toplevel           # sanity-check
# install deps if present (as above)
# run the suite once → must be green before handing to the sub-agent
```

### Merge a completed task and advance the tip

From the main working tree on `spec-builder/integration`:

```bash
git merge --no-ff spec-builder/task-NN          # advances the integration tip
# (or: rebase the task branch onto integration, then fast-forward integration)
```

Parallel tasks branched from the same tip, so the second merge of a wave may conflict —
handle per *Merge conflicts* in [`orchestration.md`](orchestration.md); never auto-resolve
silently.

### Teardown

```bash
git worktree remove ../<repo>-task-NN && git branch -d spec-builder/task-NN     # after merge
git worktree remove --force ../<repo>-task-NN && git branch -D spec-builder/task-NN   # abandoned attempt
```

---

## Operation mapping (orchestration concept → jj → git)

| Concept | jj | git |
|---|---|---|
| Detect backend | `jj workspace root` (exit 0) | `git rev-parse --is-inside-work-tree` |
| Clean shared base | `jj new` | clean tree on base commit |
| Integration point | a **revision** (advances on merge) | the **`spec-builder/integration` branch** tip |
| Add task workspace | `jj workspace add -r <int> ../<repo>-task-NN` | `git worktree add -b spec-builder/task-NN ../<repo>-task-NN spec-builder/integration` |
| List workspaces | `jj workspace list` | `git worktree list` |
| Merge completed task | `jj new <int> <task-rev>` / `jj rebase -s <task-rev> -d <int>` | `git merge --no-ff spec-builder/task-NN` |
| Abandon attempt | `jj abandon <task-rev>` | `git branch -D spec-builder/task-NN` |
| Stale working copy | `jj workspace update-stale` | (n/a — worktrees lock their branch) |
| Teardown | `jj workspace forget <name>` + `rm -rf <path>` | `git worktree remove <path>` + `git branch -d <branch>` |

---

## Common mistakes (both backends)

- **Nesting a workspace inside the main tree.** Both tools expect siblings or external
  paths; nesting breaks tooling. Use `../<name>`.
- **Skipping the baseline test run.** When a sub-agent's change breaks tests, a green
  baseline is what lets you attribute the breakage to that task. Always run the suite once
  in the fresh workspace first.
- **Adding a jj workspace without `jj new` first** (or a git worktree from a dirty tree).
  The workspace inherits in-flight edits, polluting its starting point.
- **Deleting the directory without unregistering.** `jj workspace forget` / `git worktree
  remove` must run too, or `jj workspace list` / `git worktree list` keep a phantom.
- **Treating a workspace like a long-lived branch.** One workspace per *parallel task*, not
  per logical branch; tear it down after the merge.
- **Auto-resolving a cross-task conflict silently.** A conflict between tasks the plan
  called independent is signal of a missing dependency edge — resolve deliberately and
  re-gate (see [`orchestration.md`](orchestration.md)).
