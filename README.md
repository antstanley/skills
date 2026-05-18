# skills

A Claude Code plugin marketplace by Ant Stanley.

## Install

Register the marketplace, then install plugins individually:

```
/plugin marketplace add antstanley/skills
/plugin install reasoning-semiformally@skills
/plugin install spec-creator@skills
```

## Plugins

| Plugin | Description |
|---|---|
| [reasoning-semiformally](plugins/reasoning-semiformally/) | Apply semi-formal certificate reasoning to code analysis — patch verification, fault localization, and patch equivalence. |
| [spec-creator](plugins/spec-creator/) | Create or expand formal design specifications — numbered, layered, cross-linked markdown that defines what exists in the current branch. |

## Repo layout

```
.
├── .claude-plugin/marketplace.json     # marketplace manifest
├── plugins/
│   ├── reasoning-semiformally/
│   │   ├── .claude-plugin/plugin.json
│   │   ├── skills/reasoning-semiformally/
│   │   └── README.md
│   └── spec-creator/
│       ├── .claude-plugin/plugin.json
│       ├── skills/spec-creator/
│       └── README.md
└── docs/specs/spec.md                  # marketplace design spec
```

## Adding a new plugin

1. Create `plugins/<name>/skills/<name>/SKILL.md` (with YAML frontmatter).
2. Add `plugins/<name>/.claude-plugin/plugin.json` and `plugins/<name>/README.md`.
3. Append an entry for the plugin to `.claude-plugin/marketplace.json`.
