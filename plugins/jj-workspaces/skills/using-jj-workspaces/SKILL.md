---
name: using-jj-workspaces
description: Use when starting isolated feature work, executing implementation plans, or dispatching sub-agents in a jj (jujutsu) repo. ALSO INTERCEPTS any git-worktree request (the `using-git-worktrees` skill, brainstorming Phase 4, subagent-driven-development, executing-plans, or "create a worktree" phrasing) when the repo is jj-managed — creating isolated jj workspaces as sibling directories with verified-clean baselines so parallel work (including multiple agents) doesn't collide.
---

# Using jj Workspaces

## Overview

jj workspaces are independent working copies backed by the same underlying repository. Unlike git worktrees, they're not tied to a branch — they're tied to a *revision*, which jj can move freely. Every workspace sees the others in `jj log` (each marked with its own `@` pointer), and any command auto-snapshots the working copy, so context-switching never requires stashing.

This makes workspaces an ideal unit of isolation for sub-agent driven development: spin up one workspace per parallel task, let each agent iterate in its own directory, and merge back through jj's usual revision graph instead of branch-and-merge ceremony.

**Core principle:** Sibling-directory workspaces + clean shared base + verified green starting point = reliable parallel isolation.

**Announce at start:** "I'm using the using-jj-workspaces skill to set up an isolated workspace."

## Interception: Redirecting Git-Worktree Requests

Several skills in this toolkit (notably `using-git-worktrees`, and the skills that call it — `brainstorming` Phase 4, `subagent-driven-development`, `executing-plans`, `finishing-a-development-branch`) assume the repo is plain git. In a jj-managed repo those instructions produce the *wrong* kind of isolation: a git worktree locks a branch, misses jj's revision semantics, and won't appear in `jj log`, which breaks the multi-workspace coordination the rest of the workflow depends on.

**Interception rule:** If any skill, plan, or user request asks you to "create a git worktree", invoke the `using-git-worktrees` skill, or otherwise set up isolated parallel work, **run the detection step below first**. When jj is in use, this skill takes precedence and you should follow it instead of `using-git-worktrees`.

### Detection

```bash
jj workspace root 2>/dev/null
```

- **Exits 0** → jj repo. Use this skill. Translate any "worktree" wording in the caller's instructions to the jj equivalents (see mapping below) and proceed.
- **Exits non-zero**, but a `.git` directory or `git rev-parse --is-inside-work-tree` succeeds → plain git repo. Defer to `using-git-worktrees` unchanged.
- **Neither** → not a VCS repo; surface that to the caller rather than guessing.

### Announce the redirect

When intercepting a git-worktree request, say so explicitly so the caller (human or agent) understands the substitution:

> "This repo is jj-managed, so I'm using the `using-jj-workspaces` skill instead of `using-git-worktrees`. Mapping: `git worktree add` → `jj workspace add`, `.worktrees/<name>` → `../<repo>-<name>`, `git worktree remove` → `jj workspace forget` + `rm -rf`."

### Operation mapping

Use this table to translate any git-worktree instructions you receive into their jj equivalents before executing:

| git-worktree operation | jj-workspace equivalent |
|---|---|
| `git worktree add <path> -b <branch>` | `jj new && jj workspace add <path>` (create bookmark later with `jj bookmark create <name>` if/when needed) |
| `git worktree add <path> <existing-branch>` | `jj workspace add -r <bookmark-or-revision> <path>` |
| Place worktree under `.worktrees/<name>` | Place workspace at sibling `../<repo>-<name>` (workspaces cannot nest inside the main tree) |
| Verify `.worktrees/` is gitignored | **Skip** — workspaces live outside the repo tree; no gitignore concern |
| `git worktree list` | `jj workspace list` |
| `git worktree remove <path>` | `jj workspace forget <name>` + `rm -rf <path>` |
| Branch name per worktree | Workspace name (defaults to final path component); bookmarks are optional and created when work is ready to ship |

Once translated, continue with the creation steps below as normal.

## Why Workspaces Beat Worktrees for Parallel Work

- **Revision-based, not branch-based.** A workspace points at a revision; you can rebase or move it without branch gymnastics, and two workspaces can edit the same underlying change without conflict-locking.
- **Auto-snapshot.** jj records the working copy on every command, so there's never a "did I stash?" moment when an agent switches direction.
- **Shared log view.** `jj log` shows which workspace is editing which change (`@` for current workspace, `<name>@` for others). Agents can observe each other's progress.
- **No branch name required.** You don't have to invent a branch up front; the workspace name is enough, and bookmarks (jj's branches) can be created later when work is ready to ship.

## Precondition: Confirm You're in a jj Repo

```bash
jj workspace root
```

- Succeeds → proceed.
- Fails with "There is no jj repo in …" → either `jj git init --colocate` (adopts the existing git repo in place) or fall back to the `using-git-worktrees` skill.

## Directory Selection

jj workspaces must live **outside** the main repo's working tree. Nesting a workspace inside the repo it's linked to confuses jj's tracking and many tools. Sibling paths are the idiomatic choice.

Follow this priority order:

### 1. Check for an existing workspaces layout

```bash
repo_root=$(jj workspace root)
repo_name=$(basename "$repo_root")
parent=$(dirname "$repo_root")

# Preferred patterns, in order
ls -d "$parent/.${repo_name}-workspaces" 2>/dev/null   # hidden grouped folder
ls -d "$parent/${repo_name}-workspaces"  2>/dev/null   # visible grouped folder
jj workspace list                                       # any already-registered workspaces hint at the convention
```

If any of these already exist, honor the existing layout.

### 2. Check project conventions

```bash
grep -iE "jj workspace|workspace.*director" CLAUDE.md 2>/dev/null
```

Use the documented preference without asking.

### 3. Ask the user

If nothing is configured, ask:

```
No jj workspace layout found. Where should I create the workspace?

1. Sibling: ../<repo>-<feature>/                     (jj-idiomatic, one-off)
2. Grouped: ../<repo>-workspaces/<feature>/          (when several are in flight)
3. Global:  ~/.config/superpowers/jj-workspaces/<repo>/<feature>/
```

Because workspaces sit outside the main tree, there is **no `.gitignore` concern** — unlike git worktrees placed at `.worktrees/`.

## Creation Steps

### 1. Establish a clean shared base

Create a fresh empty commit before adding the workspace, so it branches from a stable revision rather than inheriting in-flight edits from the current working copy:

```bash
jj new
```

Skip this if you deliberately want the workspace to start from a specific revision — pass `-r <rev>` to `jj workspace add` below instead.

### 2. Add the workspace

```bash
# Default: branch off current @ (what `jj new` just created)
jj workspace add "<destination-path>"

# Or: start from a specific revision / bookmark
jj workspace add -r <revision-or-bookmark> "<destination-path>"
```

The destination path is the directory that will be created. The workspace name defaults to the final path component — e.g. `../myproject-auth` → workspace named `myproject-auth`. If you want a different name shown in `jj log`, rename afterwards with `jj workspace rename <old> <new>`.

### 3. Enter the workspace

```bash
cd "<destination-path>"
jj workspace root   # sanity-check: should print the new path
```

### 4. Install dependencies (auto-detect)

```bash
[ -f package.json ]     && npm install
[ -f Cargo.toml ]       && cargo build
[ -f requirements.txt ] && pip install -r requirements.txt
[ -f pyproject.toml ]   && poetry install
[ -f go.mod ]           && go mod download
```

Only run what matches; skip silently otherwise.

### 5. Verify a clean test baseline

Run the project's suite once to confirm the workspace starts green. Use whichever command the project uses — `npm test`, `cargo test`, `pytest`, `go test ./...`, etc.

- **Tests pass:** proceed and report ready.
- **Tests fail:** surface the failures and ask whether to investigate or continue. Don't silently paper over pre-existing breakage — later agent failures become impossible to attribute.

### 6. Report

```
Workspace ready at <full-path>  (name: <workspace-name>)
Tests passing (<N> tests, 0 failures)
Ready to implement <feature>
```

## Sub-Agent Driven Development Workflow

When the parent session will dispatch N sub-agents in parallel, create one workspace per agent:

```bash
jj new                                  # shared base
jj workspace add ../myproject-agent-1
jj workspace add ../myproject-agent-2
jj workspace add ../myproject-agent-3
```

Each sub-agent receives its own workspace path and operates independently. Because all workspaces share the same backing repo:

- `jj log` from any workspace shows every agent's in-progress revision.
- Merging an agent's output back is `jj rebase -s <agent-rev> -d <target>` or `jj new <rev1> <rev2> …` for a combined merge change — no pushing/pulling required.
- Abandoning a failed attempt is `jj abandon <rev>` followed by `jj workspace forget <name>` and `rm -rf <path>`.

## Handling a Stale Working Copy

If another workspace rewrote the revision your workspace was editing, the next `jj` command will report the working copy as stale. Resolve with:

```bash
jj workspace update-stale
```

This resyncs files to the current operation's working-copy commit. If prior state would otherwise be lost, jj preserves it as an automatic recovery commit — **don't force-reset**.

## Cleanup

When the workspace's work is integrated or abandoned:

```bash
# From anywhere in the repo
jj workspace forget <workspace-name>
rm -rf <workspace-path>
```

`jj workspace forget` unregisters the workspace from the repo; removing the directory is a separate manual step. Running them in either order is fine, but both must happen or `jj workspace list` will keep showing a ghost entry.

## Quick Reference

| Situation | Action |
|-----------|--------|
| Not a jj repo | `jj git init --colocate` or use `using-git-worktrees` |
| Existing `<repo>-workspaces/` sibling | Use it |
| No layout, no CLAUDE.md | Ask user |
| About to add workspace | `jj new` first for clean base |
| Different starting revision needed | `jj workspace add -r <rev> <path>` |
| Want a different workspace name than dir | `jj workspace rename <old> <new>` after add |
| "Working copy is stale" error | `jj workspace update-stale` |
| Done with workspace | `jj workspace forget <name>` + `rm -rf <path>` |
| Lost track of workspaces | `jj workspace list` |

## Common Mistakes

### Nesting the workspace inside the main repo

- **Problem:** jj expects workspaces as siblings or fully external paths; nesting breaks tooling and confuses `jj log`.
- **Fix:** Use `../<name>` or an absolute path outside the repo tree.

### Treating workspaces like long-lived branches

- **Problem:** Creating one workspace per branch "just in case" inflates disk usage and mental overhead. In jj, a single workspace can freely move between revisions.
- **Fix:** Create one workspace per *parallel task*, not per logical branch.

### Deleting the directory without `jj workspace forget`

- **Problem:** The workspace stays registered; `jj log` and `jj workspace list` show a phantom.
- **Fix:** Run `jj workspace forget <name>` when tearing down.

### Skipping the baseline test run

- **Problem:** When an agent's later changes break tests, you can't tell whether the breakage is new or pre-existing.
- **Fix:** Always run the suite once in the fresh workspace before handing off.

### Panicking on a stale working copy

- **Problem:** Treating the stale-copy message as data loss and force-resetting.
- **Fix:** `jj workspace update-stale` resolves it safely; jj preserves prior state in a recovery commit when needed.

### Adding a workspace without `jj new` first

- **Problem:** The new workspace inherits whatever uncommitted edits were in the current working copy, polluting its starting point.
- **Fix:** `jj new` before `jj workspace add`, unless deliberately branching from a specific revision with `-r`.

## Example Workflow

```
You: I'm using the using-jj-workspaces skill to set up an isolated workspace.

[jj workspace root         → /Users/jesse/myproject]
[Parent: /Users/jesse, repo_name: myproject]
[No existing *-workspaces directory; no CLAUDE.md preference]
[Ask user → chose "sibling" pattern]

[jj new]                                        # clean shared base
[jj workspace add ../myproject-auth]            # adds workspace, name "myproject-auth"
[cd ../myproject-auth]
[jj workspace root  → /Users/jesse/myproject-auth]
[npm install]
[npm test           → 47 passing]

Workspace ready at /Users/jesse/myproject-auth  (name: myproject-auth)
Tests passing (47 tests, 0 failures)
Ready to implement auth feature
```

## Integration

**Called by (natively):**
- **brainstorming** (Phase 4) — when design is approved and implementation begins in a jj repo.
- **subagent-driven-development** — before dispatching sub-agents in a jj repo; one workspace per agent.
- **executing-plans** — before executing tasks that need isolation.
- Any skill needing an isolated workspace in a jj-managed project.

**Pairs with:**
- **finishing-a-development-branch** — adapt its worktree-removal steps to `jj workspace forget <name>` + `rm -rf <path>`.
- **using-git-worktrees** — intercepted in jj repos (see [Interception](#interception-redirecting-git-worktree-requests)); it's the fallback only when `jj workspace root` fails and you won't colocate with `jj git init --colocate`.
