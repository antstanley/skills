# skills

A Claude Code plugin marketplace by Ant Stanley.

## Install

Register the marketplace, then install plugins individually:

```
/plugin marketplace add antstanley/skills
/plugin install reasoning-semiformally@skills
/plugin install spec-creator@skills
/plugin install spec-planner@skills
/plugin install jj-workspaces@skills
/plugin install spec-builder@skills
```

## Plugins

| Plugin | Description |
|---|---|
| [reasoning-semiformally](plugins/reasoning-semiformally/) | Apply semi-formal certificate reasoning to code analysis — patch verification, fault localization, and patch equivalence. |
| [spec-creator](plugins/spec-creator/) | Create or expand formal design specifications — numbered, layered, cross-linked markdown that defines what exists in the current branch. |
| [spec-planner](plugins/spec-planner/) | Plan the implementation of a specification — decompose a spec into a dependency-ordered graph of reviewable task packages, each with a definition of done. |
| [jj-workspaces](plugins/jj-workspaces/) | jj (jujutsu) workspaces skill for Claude Code — creates isolated workspaces for parallel work and sub-agent-driven development, and intercepts git-worktree requests in jj-managed repos. |
| [spec-builder](plugins/spec-builder/) | Implement a spec-planner plan — one sub-agent per task in its own isolated workspace (jj or git, jj preferred), gated through a semi-formal correctness review and a definition-of-done validation before each task merges and is marked Done; parallel by default (max 4 agents) or sequential. |

## Use with other agents / harnesses

These skills are standard [Agent Skills](https://github.com/agentskills/agentskills),
so they also work in Codex, Cursor, Pi, OpenCode, Zed, and Kiro. Install them with
`install.sh`:

```
./install.sh all          # Codex, Cursor, Pi, OpenCode, Zed (~/.agents/skills) + Kiro (~/.kiro/skills)
./install.sh codex        # or a single harness: agents/codex/zed | cursor | pi | opencode | kiro | claude
./install.sh cursor --project ~/work/myrepo   # per-project instead of global
```

Skills are copied by default (use `--symlink` for live updates). See
[docs/multi-harness-skills.md](docs/multi-harness-skills.md) for the full
discovery-path matrix and the sub-agent portability notes.

The flat [`skills/`](skills/) tree is a generated, vendor-neutral copy of every
skill (real files, no symlinks). It is regenerated from `plugins/` by
`scripts/sync-skills.sh`; `plugins/` is the canonical source — edit there, then
re-run the script. `scripts/check.sh` fails if `skills/` is stale.

## Repo layout

```
.
├── .claude-plugin/marketplace.json     # marketplace manifest
├── skills/                             # GENERATED flat tree (scripts/sync-skills.sh); plugins/ is canonical
├── install.sh                          # install skills into another harness
├── scripts/sync-skills.sh              # regenerate skills/ from plugins/ (+ --check)
├── plugins/
│   ├── reasoning-semiformally/
│   │   ├── .claude-plugin/plugin.json
│   │   ├── skills/reasoning-semiformally/
│   │   └── README.md
│   ├── spec-creator/
│   │   ├── .claude-plugin/plugin.json
│   │   ├── skills/spec-creator/
│   │   └── README.md
│   ├── spec-planner/
│   │   ├── .claude-plugin/plugin.json
│   │   ├── skills/spec-planner/
│   │   └── README.md
│   ├── jj-workspaces/
│   │   ├── .claude-plugin/plugin.json
│   │   ├── skills/using-jj-workspaces/
│   │   └── README.md
│   └── spec-builder/
│       ├── .claude-plugin/plugin.json
│       ├── skills/spec-builder/                 # orchestrator
│       │   └── references/                       # orchestration, workspaces (jj+git), subagent-brief, build-loop
│       ├── skills/semi-formal-review/           # gate 1 — correctness
│       ├── skills/validate-done-certificate/    # gate 2 — completeness
│       └── README.md
└── docs/specs/spec.md                  # marketplace design spec
```

## Adding a new plugin

1. Create `plugins/<name>/skills/<name>/SKILL.md` (with YAML frontmatter).
2. Add `plugins/<name>/.claude-plugin/plugin.json` and `plugins/<name>/README.md`.
3. Append an entry for the plugin to `.claude-plugin/marketplace.json`.
4. Run `scripts/sync-skills.sh` to refresh the generated `skills/` tree.
