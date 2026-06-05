# Plugin Marketplace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the `antstanley/skills` repo into a Claude Code plugin marketplace per [`.specs/spec.md`](../../spec.md), making each existing skill (`reasoning-semiformally`, `spec-creator`) installable via `/plugin install <name>@skills`.

**Architecture:** Pure file-layout migration plus three new JSON manifests. No code changes. Move each skill into `plugins/<name>/skills/<name>/`, add a `.claude-plugin/plugin.json` and `README.md` per plugin, and create the top-level `.claude-plugin/marketplace.json`. Existing skill content (`SKILL.md`, `haiku.md`, `sonnet.md`, `evals/`, `references/`) is moved verbatim, never edited.

**Tech Stack:** Filesystem + JSON. Version control via `jj` (this repo is jj-managed — never use `git add`/`git commit`).

---

## Pre-flight

This plan assumes:

- Working directory is `/Users/ant/code/skills`.
- The current branch has `reasoning-semiformally/`, `spec-creator/`, and an empty `skills/` directory at the repo root.
- A `README.md` already exists at the repo root (currently documents the pre-marketplace state).
- The reference implementation is at `/Users/ant/.claude/plugins/marketplaces/jj-workspace-skill/` — consult it for any structural questions.

**jj commits:** Each task ends with `jj describe -m "<msg>"` to set the description on the current change, then `jj new` to start the next change on top of it. Do **not** use `git commit`. Do **not** use `--allow-backwards` on the `main` bookmark unless explicitly required.

---

### Task 1: Migrate `reasoning-semiformally` into `plugins/`

**Files:**
- Create dir: `plugins/reasoning-semiformally/skills/`
- Move: `reasoning-semiformally/` → `plugins/reasoning-semiformally/skills/reasoning-semiformally/`

- [ ] **Step 1: Create the destination parent**

```sh
mkdir -p plugins/reasoning-semiformally/skills
```

- [ ] **Step 2: Move the skill directory**

```sh
mv reasoning-semiformally plugins/reasoning-semiformally/skills/reasoning-semiformally
```

- [ ] **Step 3: Verify the move**

Run:
```sh
ls plugins/reasoning-semiformally/skills/reasoning-semiformally/
```

Expected output (three files):
```
SKILL.md
haiku.md
sonnet.md
```

Also verify the old path is gone:
```sh
test ! -e reasoning-semiformally && echo OK
```
Expected: `OK`

- [ ] **Step 4: Verify file contents unchanged**

Run:
```sh
head -5 plugins/reasoning-semiformally/skills/reasoning-semiformally/SKILL.md
```

Expected: YAML frontmatter starting with `---` and `name: reasoning-semiformally`.

- [ ] **Step 5: Commit**

```sh
jj describe -m "Move reasoning-semiformally into plugins/ layout"
jj new
```

---

### Task 2: Migrate `spec-creator` into `plugins/`

**Files:**
- Create dir: `plugins/spec-creator/skills/`
- Move: `spec-creator/` → `plugins/spec-creator/skills/spec-creator/`

- [ ] **Step 1: Create the destination parent**

```sh
mkdir -p plugins/spec-creator/skills
```

- [ ] **Step 2: Move the skill directory**

```sh
mv spec-creator plugins/spec-creator/skills/spec-creator
```

- [ ] **Step 3: Verify the move**

Run:
```sh
ls plugins/spec-creator/skills/spec-creator/
```

Expected output (one file + two dirs):
```
SKILL.md
evals
references
```

Also verify the old path is gone:
```sh
test ! -e spec-creator && echo OK
```
Expected: `OK`

- [ ] **Step 4: Verify subdirectories survived intact**

Run:
```sh
ls plugins/spec-creator/skills/spec-creator/evals plugins/spec-creator/skills/spec-creator/references
```
Expected: non-empty listings (whatever was originally there — do not modify).

- [ ] **Step 5: Commit**

```sh
jj describe -m "Move spec-creator into plugins/ layout"
jj new
```

---

### Task 3: Delete the empty top-level `skills/` directory

**Files:**
- Delete: `skills/`

- [ ] **Step 1: Confirm it is empty**

Run:
```sh
ls -A skills/ 2>&1
```
Expected: empty output. If anything is there, STOP and investigate before deleting.

- [ ] **Step 2: Remove the directory**

```sh
rmdir skills
```

- [ ] **Step 3: Verify removal**

Run:
```sh
test ! -e skills && echo OK
```
Expected: `OK`

- [ ] **Step 4: Commit**

```sh
jj describe -m "Remove empty top-level skills/ directory"
jj new
```

---

### Task 4: Create `plugins/reasoning-semiformally/.claude-plugin/plugin.json`

**Files:**
- Create dir: `plugins/reasoning-semiformally/.claude-plugin/`
- Create: `plugins/reasoning-semiformally/.claude-plugin/plugin.json`

- [ ] **Step 1: Create the manifest directory**

```sh
mkdir -p plugins/reasoning-semiformally/.claude-plugin
```

- [ ] **Step 2: Write the plugin manifest**

File: `plugins/reasoning-semiformally/.claude-plugin/plugin.json`

```json
{
  "name": "reasoning-semiformally",
  "description": "Apply semi-formal certificate reasoning to code analysis — patch verification, fault localization, patch equivalence. Use when reviewing patches, hunting bugs across scopes, comparing fixes, or when code reasoning requires tracing execution across files/modules.",
  "author": { "name": "antstanley" },
  "repository": "https://github.com/antstanley/skills",
  "keywords": ["reasoning", "code-review", "debugging", "patch-verification"]
}
```

- [ ] **Step 3: Verify it parses as JSON**

Run:
```sh
python3 -c "import json; json.load(open('plugins/reasoning-semiformally/.claude-plugin/plugin.json'))" && echo OK
```
Expected: `OK`

- [ ] **Step 4: Commit**

```sh
jj describe -m "Add plugin.json for reasoning-semiformally"
jj new
```

---

### Task 5: Create `plugins/spec-creator/.claude-plugin/plugin.json`

**Files:**
- Create dir: `plugins/spec-creator/.claude-plugin/`
- Create: `plugins/spec-creator/.claude-plugin/plugin.json`

- [ ] **Step 1: Create the manifest directory**

```sh
mkdir -p plugins/spec-creator/.claude-plugin
```

- [ ] **Step 2: Write the plugin manifest**

File: `plugins/spec-creator/.claude-plugin/plugin.json`

```json
{
  "name": "spec-creator",
  "description": "Create or expand formal design specifications for an app, package, or codebase — numbered, layered, cross-linked markdown that defines what exists in the current branch.",
  "author": { "name": "antstanley" },
  "repository": "https://github.com/antstanley/skills",
  "keywords": ["spec", "design", "documentation", "architecture"]
}
```

- [ ] **Step 3: Verify it parses as JSON**

Run:
```sh
python3 -c "import json; json.load(open('plugins/spec-creator/.claude-plugin/plugin.json'))" && echo OK
```
Expected: `OK`

- [ ] **Step 4: Commit**

```sh
jj describe -m "Add plugin.json for spec-creator"
jj new
```

---

### Task 6: Add `plugins/reasoning-semiformally/README.md`

**Files:**
- Create: `plugins/reasoning-semiformally/README.md`

- [ ] **Step 1: Write the README**

File: `plugins/reasoning-semiformally/README.md`

```markdown
# reasoning-semiformally

Apply semi-formal certificate reasoning to code analysis — patch verification, fault localization, and patch equivalence.

Use when reviewing patches, hunting bugs across scopes, comparing fixes, or when code reasoning requires tracing execution across files or modules. Triggers on code review, bug localization, patch comparison, name shadowing, scope analysis, and regression checking.

## Install

```
/plugin marketplace add antstanley/skills
/plugin install reasoning-semiformally@skills
```

## Skill content

The skill itself lives at [`skills/reasoning-semiformally/SKILL.md`](../../../skills/reasoning-semiformally/SKILL.md). Model-specific procedural detail is in [`haiku.md`](../../../skills/reasoning-semiformally/haiku.md) (Haiku-class) and [`sonnet.md`](../../../skills/reasoning-semiformally/sonnet.md) (Sonnet/Opus-class).
```

- [ ] **Step 2: Verify it exists**

Run:
```sh
test -f plugins/reasoning-semiformally/README.md && echo OK
```
Expected: `OK`

- [ ] **Step 3: Commit**

```sh
jj describe -m "Add README for reasoning-semiformally plugin"
jj new
```

---

### Task 7: Add `plugins/spec-creator/README.md`

**Files:**
- Create: `plugins/spec-creator/README.md`

- [ ] **Step 1: Write the README**

File: `plugins/spec-creator/README.md`

```markdown
# spec-creator

Create or expand formal design specifications for an app, package, or codebase — numbered, layered, cross-linked markdown that defines what exists in the current branch.

Triggers on phrases like "create a spec", "spec out this app", "write design docs", "formalize the architecture", or when the user references using another project's specs as a template. The output is a numbered directory of markdown files plus a JSON Schema sidecar, layered as repo-wide globals + per-app specs.

## Install

```
/plugin marketplace add antstanley/skills
/plugin install spec-creator@skills
```

## Skill content

The skill itself lives at [`skills/spec-creator/SKILL.md`](../../../skills/spec-creator/SKILL.md). Worked examples and templates are under [`skills/spec-creator/evals/`](../../../plugins/spec-creator/skills/spec-creator/evals/) and [`skills/spec-creator/references/`](../../../skills/spec-creator/references/).
```

- [ ] **Step 2: Verify it exists**

Run:
```sh
test -f plugins/spec-creator/README.md && echo OK
```
Expected: `OK`

- [ ] **Step 3: Commit**

```sh
jj describe -m "Add README for spec-creator plugin"
jj new
```

---

### Task 8: Create the marketplace manifest

**Files:**
- Create dir: `.claude-plugin/`
- Create: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Create the marketplace directory**

```sh
mkdir -p .claude-plugin
```

- [ ] **Step 2: Write the marketplace manifest**

File: `.claude-plugin/marketplace.json`

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

- [ ] **Step 3: Verify it parses as JSON**

Run:
```sh
python3 -c "import json; json.load(open('.claude-plugin/marketplace.json'))" && echo OK
```
Expected: `OK`

- [ ] **Step 4: Verify each `source` path resolves to an existing plugin directory with a manifest**

Run:
```sh
python3 -c "
import json, os
m = json.load(open('.claude-plugin/marketplace.json'))
for p in m['plugins']:
    path = os.path.join(p['source'], '.claude-plugin', 'plugin.json')
    assert os.path.isfile(path), f'Missing: {path}'
print('OK')
"
```
Expected: `OK`

- [ ] **Step 5: Commit**

```sh
jj describe -m "Add marketplace.json registering both plugins"
jj new
```

---

### Task 9: Replace the root `README.md` with the marketplace version

**Files:**
- Modify: `README.md`

The current `README.md` documents the pre-marketplace state with a "Status: migration pending" banner and an `ln -s` install path. Replace it with the marketplace-installable version.

- [ ] **Step 1: Overwrite `README.md`**

File: `README.md`

```markdown
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
| [reasoning-semiformally](../../../plugins/reasoning-semiformally/) | Apply semi-formal certificate reasoning to code analysis — patch verification, fault localization, and patch equivalence. |
| [spec-creator](../../../plugins/spec-creator/) | Create or expand formal design specifications — numbered, layered, cross-linked markdown that defines what exists in the current branch. |

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
└── .specs/spec.md                  # marketplace design spec
```

## Adding a new plugin

1. Create `plugins/<name>/skills/<name>/SKILL.md` (with YAML frontmatter).
2. Add `plugins/<name>/.claude-plugin/plugin.json` and `plugins/<name>/README.md`.
3. Append an entry for the plugin to `.claude-plugin/marketplace.json`.
```

- [ ] **Step 2: Verify the file**

Run:
```sh
head -3 README.md
```
Expected:
```
# skills

A Claude Code plugin marketplace by Ant Stanley.
```

- [ ] **Step 3: Commit**

```sh
jj describe -m "Update root README for marketplace install flow"
jj new
```

---

### Task 10: End-to-end verification

**Files:** No changes. This task is purely verification.

- [ ] **Step 1: Verify final directory layout**

Run:
```sh
find . -path ./.git -prune -o -path ./.jj -prune -o -type f -print | grep -E '\.(json|md)$' | grep -v -E '^\./.specs/' | sort
```

Expected output (exactly these files at minimum; `main.py` and other root files may also appear via separate filters):
```
./.claude-plugin/marketplace.json
./README.md
./plugins/reasoning-semiformally/.claude-plugin/plugin.json
./plugins/reasoning-semiformally/README.md
./plugins/reasoning-semiformally/skills/reasoning-semiformally/SKILL.md
./plugins/reasoning-semiformally/skills/reasoning-semiformally/haiku.md
./plugins/reasoning-semiformally/skills/reasoning-semiformally/sonnet.md
./plugins/spec-creator/.claude-plugin/plugin.json
./plugins/spec-creator/README.md
./plugins/spec-creator/skills/spec-creator/SKILL.md
```

(Plus whatever `*.md` files are under `spec-creator/skills/spec-creator/evals/` and `references/`.)

- [ ] **Step 2: Verify all JSON manifests parse**

Run:
```sh
python3 -c "
import json
for p in [
    '.claude-plugin/marketplace.json',
    'plugins/reasoning-semiformally/.claude-plugin/plugin.json',
    'plugins/spec-creator/.claude-plugin/plugin.json',
]:
    json.load(open(p))
    print(f'OK {p}')
"
```
Expected: three `OK` lines.

- [ ] **Step 3: Verify both `source` paths in marketplace.json point at real plugin directories with manifests**

Run:
```sh
python3 -c "
import json, os
m = json.load(open('.claude-plugin/marketplace.json'))
for p in m['plugins']:
    plug_json = os.path.join(p['source'], '.claude-plugin', 'plugin.json')
    skill_dir = os.path.join(p['source'], 'skills', p['name'])
    skill_md  = os.path.join(skill_dir, 'SKILL.md')
    assert os.path.isfile(plug_json), f'Missing: {plug_json}'
    assert os.path.isdir(skill_dir),  f'Missing: {skill_dir}'
    assert os.path.isfile(skill_md),  f'Missing: {skill_md}'
    print(f'OK {p[\"name\"]}')
"
```
Expected: two `OK` lines (one per plugin).

- [ ] **Step 4: Verify the empty `skills/` directory is gone**

Run:
```sh
test ! -e skills && echo OK
```
Expected: `OK`

- [ ] **Step 5: Check jj log shows the expected commits**

Run:
```sh
jj log -r '@-..|@-----------' --limit 12
```
Expected: working-copy commit on top, then nine descriptive commits from Tasks 1–9 (in reverse order), then the prior `main` tip (`Add README with plugin index and install instructions` at the time this plan was written — note: Task 9 overwrites that README's content, but the prior commit still exists in history).

This verification task has no commit of its own.

---

## Self-review

- **Spec coverage:** All ten "What still needs to happen" steps in the spec are covered: migrate `reasoning-semiformally` (Task 1), migrate `spec-creator` (Task 2), delete empty `skills/` (Task 3), create `marketplace.json` (Task 8), per-plugin `plugin.json` files (Tasks 4–5), per-plugin READMEs (Tasks 6–7), root README update (Task 9), and final verification (Task 10). Commits happen at the end of each task per spec's instruction to use jj.
- **Open questions from the spec:** `LICENSE` files and `main.py`/`pyproject.toml` disposition are explicitly **not** addressed by this plan — they were open questions, not requirements.
- **No placeholders.** Every file's content is fully written out. JSON content is verbatim from the spec.
