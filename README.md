# skills

A collection of Claude Code skills by Ant Stanley.

> **Status:** This repo is in the process of being restructured into a Claude Code plugin marketplace (see [`docs/specs/spec.md`](docs/specs/spec.md)). Until that migration lands, the skills below live at the repo root and are installed manually rather than via `/plugin install`.

## Index

| Skill | Description |
|---|---|
| [reasoning-semiformally](reasoning-semiformally/) | Apply semi-formal certificate reasoning to code analysis — patch verification, fault localization, and patch equivalence. Useful when reviewing patches, hunting bugs across scopes, or comparing fixes. |
| [spec-creator](spec-creator/) | Create or expand formal design specifications for an app, package, or codebase. Produces numbered, layered, cross-linked markdown that defines what exists in the current branch. |

## Installing a skill in Claude Code

Skills are loaded by Claude Code from `~/.claude/skills/<name>/` (user-level) or `.claude/skills/<name>/` (project-level). Until this repo is published as a marketplace, install a skill by linking it into one of those locations.

```sh
# Clone this repo somewhere stable
git clone https://github.com/antstanley/skills.git ~/code/skills

# User-level install (available in every Claude Code session)
mkdir -p ~/.claude/skills
ln -s ~/code/skills/reasoning-semiformally ~/.claude/skills/reasoning-semiformally
ln -s ~/code/skills/spec-creator           ~/.claude/skills/spec-creator

# Or project-level install (scoped to one repo)
mkdir -p .claude/skills
ln -s ~/code/skills/reasoning-semiformally .claude/skills/reasoning-semiformally
```

Restart Claude Code (or start a new session) and the skill will appear in the available-skills list. Invoke it by name with the `Skill` tool, or let Claude trigger it automatically based on the `description` field in each `SKILL.md`.

## Planned: marketplace install

Once the marketplace migration in [`docs/specs/spec.md`](docs/specs/spec.md) is complete, installation will be:

```
/plugin marketplace add antstanley/skills
/plugin install reasoning-semiformally@skills
/plugin install spec-creator@skills
```

## Adding a new skill

1. Create a new top-level directory named after the skill.
2. Add a `SKILL.md` with YAML frontmatter (`name`, `description`, optional `version`).
3. Add this entry to the [Index](#index) table above.
