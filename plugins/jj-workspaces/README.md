# jj-workspaces

A jj (jujutsu) workspaces skill for Claude Code — creates isolated workspaces for parallel work and sub-agent-driven development, and intercepts git-worktree requests in jj-managed repos.

Triggers when starting feature work that needs isolation, before executing implementation plans, or before dispatching sub-agents in a jj repository. Also intercepts any request for git worktrees (including the `using-git-worktrees` skill, `brainstorming` Phase 4, `subagent-driven-development`, `executing-plans`, and any "create a worktree" phrasing) whenever the current repo is jj-managed, substituting `jj workspace add` so parallel work and bookmark semantics behave correctly.

## Install

```
/plugin marketplace add antstanley/skills
/plugin install jj-workspaces@skills
```

## Skill content

The skill itself lives at [`skills/using-jj-workspaces/SKILL.md`](skills/using-jj-workspaces/SKILL.md).

## Upstream

Originally authored at [antstanley/jj-workspace-skill](https://github.com/antstanley/jj-workspace-skill). This copy is maintained as part of the `antstanley/skills` marketplace.
