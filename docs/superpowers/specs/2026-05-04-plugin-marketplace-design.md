# Plugin Marketplace Design

**Status:** Draft · **Date:** 2026-05-04 · **Owner:** Ant Stanley

The `antstanley/skills` GitHub repository serves as a Claude Code plugin marketplace — a registered source from which users can discover and install individual plugins via the Claude Code plugin system.

---

## Problem

Skills authored in this repo have no standard installation path. Without a marketplace structure, distributing them requires manual file copying or pointing users at raw files. The Claude Code plugin system solves this, but the repo must conform to the expected layout before it can be registered as a marketplace.

---

## Goals

1. Make the repo registerable as a Claude Code marketplace via `/plugin marketplace add antstanley/skills`.
2. Make each skill independently installable as its own plugin.
3. Conform to the same layout used by `antstanley/jj-workspace-skill` for consistency.
4. Establish a clear slot for future plugins without requiring restructuring.

## Non-goals

- Building a web UI or browse experience beyond what the Claude Code plugin manager provides.
- Versioned release automation (handled separately via git tags if needed later).
- Modifying the content of existing `SKILL.md` files.

---

## System shape

```
antstanley/skills (GitHub)
        │
        ▼
.claude-plugin/marketplace.json    ← registered by Claude Code
        │
        ├── plugins/reasoning-semiformally/
        │       ├── .claude-plugin/plugin.json
        │       └── skills/reasoning-semiformally/SKILL.md + haiku.md + sonnet.md
        │
        └── plugins/spec-creator/
                ├── .claude-plugin/plugin.json
                └── skills/spec-creator/SKILL.md + evals/ + references/
```

Claude Code reads `marketplace.json` to enumerate available plugins. Each plugin's `plugin.json` provides metadata. The `skills/<name>/` directory is where Claude Code loads skill content from at install time.

---

## Detail pages

| Section | Topic |
|---|---|
| [File layout](#file-layout) | Full directory tree after migration |
| [marketplace.json](#marketplacejson) | Root marketplace manifest |
| [plugin.json per plugin](#pluginjson-per-plugin) | Per-plugin metadata shape |
| [File migrations](#file-migrations) | What moves where |
| [Install flow](#install-flow) | How a user installs from this marketplace |

---

## File layout

```
skills/                                        ← repo root
├── .claude-plugin/
│   └── marketplace.json
├── plugins/
│   ├── reasoning-semiformally/
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   ├── skills/
│   │   │   └── reasoning-semiformally/
│   │   │       ├── SKILL.md
│   │   │       ├── haiku.md
│   │   │       └── sonnet.md
│   │   └── README.md
│   └── spec-creator/
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── skills/
│       │   └── spec-creator/
│       │       ├── SKILL.md
│       │       ├── evals/
│       │       └── references/
│       └── README.md
├── docs/
│   └── superpowers/specs/
│       └── 2026-05-04-plugin-marketplace-design.md
├── README.md
├── main.py
├── pyproject.toml
└── .gitignore
```

The empty `skills/` directory at the repo root is removed. The `main.py` / `pyproject.toml` Python scaffolding is left untouched.

---

## marketplace.json

Location: `.claude-plugin/marketplace.json`

```json
{
  "name": "skills",
  "metadata": {
    "description": "A collection of Claude Code plugins by Ant Stanley."
  },
  "owner": { "name": "antstanley" },
  "plugins": [
    {
      "name": "reasoning-semiformally",
      "source": "./plugins/reasoning-semiformally",
      "description": "Apply semi-formal certificate reasoning to code analysis — patch verification, fault localization, patch equivalence.",
      "category": "development",
      "homepage": "https://github.com/antstanley/skills"
    },
    {
      "name": "spec-creator",
      "source": "./plugins/spec-creator",
      "description": "Create or expand formal design specifications for an app, package, or codebase — numbered, layered, cross-linked markdown.",
      "category": "development",
      "homepage": "https://github.com/antstanley/skills"
    }
  ]
}
```

Adding a new plugin requires appending an entry here and creating the corresponding directory under `plugins/`.

---

## plugin.json per plugin

Each plugin carries its own metadata at `plugins/<name>/.claude-plugin/plugin.json`.

**reasoning-semiformally:**
```json
{
  "name": "reasoning-semiformally",
  "description": "Apply semi-formal certificate reasoning to code analysis — patch verification, fault localization, patch equivalence. Use when reviewing patches, hunting bugs across scopes, comparing fixes, or when code reasoning requires tracing execution across files/modules.",
  "author": { "name": "antstanley" },
  "repository": "https://github.com/antstanley/skills",
  "keywords": ["reasoning", "code-review", "debugging", "patch-verification"]
}
```

**spec-creator:**
```json
{
  "name": "spec-creator",
  "description": "Create or expand formal design specifications for an app, package, or codebase — numbered, layered, cross-linked markdown that defines what exists in the current branch.",
  "author": { "name": "antstanley" },
  "repository": "https://github.com/antstanley/skills",
  "keywords": ["spec", "design", "documentation", "architecture"]
}
```

Version is omitted initially; the plugin system falls back to `unknown`. A `version` field can be added when a release tagging workflow is in place.

---

## File migrations

| Current path | New path |
|---|---|
| `reasoning-semiformally/SKILL.md` | `plugins/reasoning-semiformally/skills/reasoning-semiformally/SKILL.md` |
| `reasoning-semiformally/haiku.md` | `plugins/reasoning-semiformally/skills/reasoning-semiformally/haiku.md` |
| `reasoning-semiformally/sonnet.md` | `plugins/reasoning-semiformally/skills/reasoning-semiformally/sonnet.md` |
| `spec-creator/SKILL.md` | `plugins/spec-creator/skills/spec-creator/SKILL.md` |
| `spec-creator/evals/` | `plugins/spec-creator/skills/spec-creator/evals/` |
| `spec-creator/references/` | `plugins/spec-creator/skills/spec-creator/references/` |
| `skills/` (empty dir) | deleted |

---

## Install flow

```
# Register the marketplace
/plugin marketplace add antstanley/skills

# Install individual plugins
/plugin install reasoning-semiformally@skills
/plugin install spec-creator@skills
```

---

## Assumptions and open questions

**Assumptions**

- The Claude Code plugin system resolves `source` in `marketplace.json` as a relative path from the marketplace root.
- Skill content is loaded from `skills/<name>/SKILL.md` within each plugin directory.
- The `main.py` / `pyproject.toml` scaffolding does not interfere with marketplace registration.

**Decisions**

- *Plugin.json location.* **`.claude-plugin/plugin.json`** (nested). Matches `antstanley/jj-workspace-skill` and the Anthropic official marketplace — the community `plugin.json`-at-root format is older and diverges from current tooling.
- *Version omitted from plugin.json initially.* **Omitted.** The plugin system accepts `unknown`; adding a version field before a release workflow exists would require manual maintenance with no benefit.
- *`skills/` empty directory removed.* **Deleted.** It was scaffolding with no content; `plugins/` supersedes it.

**Open questions**

- Should a `LICENSE` file be added to each plugin directory (as Anthropic's official plugins include)?
- Should `main.py` / `pyproject.toml` be removed, repurposed, or left as-is?
