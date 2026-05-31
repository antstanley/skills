# skills

A collection of [Agent Skills](https://github.com/agentskills/agentskills) for
**spec-driven development** by Ant Stanley — define a spec, plan its
implementation, then build it task by task behind correctness and completeness
gates. Packaged as a Claude Code plugin marketplace, and installable into any
harness that supports the Agent Skills standard (Codex, Cursor, Pi, OpenCode,
Zed, Kiro).

## The spec → plan → build workflow

The core skills form a pipeline. Each stage hands a reviewable artifact to the
next, and the final stage refuses to mark work done unless it is proven correct
*and* complete by an agent other than the one that built it.

```
  spec-creator          spec-planner            spec-builder
   define ▶──────────────▶ decompose ▶───────────▶ implement
  the spec               into a task plan         task by task
      │                       │                        │
 spec-reviewer          done-certificates      semi-formal-review  (gate 1: correct)
 development-guidelines  (per-task proof)       validate-done-certificate (gate 2: complete)
                                                       │
                                                 using-jj-workspaces (isolation)

            reasoning-semiformally — the certificate method both gates build on
```

1. **Define** — `spec-creator` writes the canonical spec (what exists in the
   current branch). `spec-reviewer` checks it against the code or a change spec;
   `development-guidelines` adds the "rules of the road" page.
2. **Plan** — `spec-planner` decomposes the spec into a dependency-ordered graph
   of task packages, each with a definition of done. `done-certificates` authors
   a per-task verification protocol for a validator to run later.
3. **Build** — `spec-builder` executes the plan: one sub-agent per task in an
   isolated workspace, each gated by `semi-formal-review` (correctness) and
   `validate-done-certificate` (completeness) before it merges and is marked Done.
   `using-jj-workspaces` provides the isolation in jj repos.

`reasoning-semiformally` is the foundation — the semi-formal certificate
reasoning method the two build gates apply. It is also useful on its own for
patch verification, bug localization, and patch-equivalence checks.

## Skills

| Skill | Plugin | Role |
|---|---|---|
| [spec-creator](plugins/spec-creator/) | spec-creator | Create / expand / change a canonical design spec — numbered, layered, cross-linked markdown. |
| [spec-reviewer](plugins/spec-creator/) | spec-creator | Review a spec against the code, or a change spec against the canonical spec. |
| [development-guidelines](plugins/spec-creator/) | spec-creator | Add a development-guidelines page (toolchain, style, testing, DoD) to a spec. |
| [spec-planner](plugins/spec-planner/) | spec-planner | Decompose a spec into a dependency-ordered plan of task packages, each with a definition of done. |
| [done-certificates](plugins/spec-planner/) | spec-planner | Author a per-task semi-formal done certificate for a validating agent to discharge. |
| [spec-builder](plugins/spec-builder/) | spec-builder | Execute a plan — one sub-agent per task in an isolated workspace, gated and merged in dependency order. |
| [semi-formal-review](plugins/spec-builder/) | spec-builder | Build gate 1 — semi-formal correctness review of an implemented task. |
| [validate-done-certificate](plugins/spec-builder/) | spec-builder | Build gate 2 — discharge a task's done certificate to prove completeness. |
| [reasoning-semiformally](plugins/reasoning-semiformally/) | reasoning-semiformally | The semi-formal certificate reasoning method — patch verification, fault localization, patch equivalence. |
| [using-jj-workspaces](plugins/jj-workspaces/) | jj-workspaces | Isolated jj (jujutsu) workspaces for parallel / sub-agent work; intercepts git-worktree requests in jj repos. |

## Install

### Claude Code — plugin marketplace

Register the marketplace, then install whichever plugins you want:

```
/plugin marketplace add antstanley/skills
/plugin install spec-creator@skills
/plugin install spec-planner@skills
/plugin install spec-builder@skills
/plugin install reasoning-semiformally@skills
/plugin install jj-workspaces@skills
```

For the full spec → plan → build flow, install `spec-creator`, `spec-planner`,
and `spec-builder` (which bundles its two gate skills). Plugins are
self-contained, so any one can be installed on its own.

### Other harnesses — `install.sh`

For Codex, Cursor, Pi, OpenCode, Zed, and Kiro, run the installer. It places the
skills into each harness's discovery directory:

```
./install.sh all          # Codex, Cursor, Pi, OpenCode, Zed (~/.agents/skills) + Kiro (~/.kiro/skills)
./install.sh codex        # a single harness: agents/codex/zed | cursor | pi | opencode | kiro | claude
./install.sh cursor --project ~/work/myrepo   # per-project instead of global
```

Skills are **copied** by default (use `--symlink` for live updates). One path —
`~/.agents/skills/` — serves Codex, Cursor, Pi, OpenCode, and Zed at once; Kiro
uses `~/.kiro/skills/`. See [docs/multi-harness-skills.md](docs/multi-harness-skills.md)
for the full discovery-path matrix and the sub-agent portability notes (some
skills orchestrate sub-agents and degrade gracefully where a harness can't).

## Repo layout

`plugins/` is canonical. The flat [`skills/`](skills/) tree is a generated,
vendor-neutral copy of every skill (real files, no symlinks, internal `evals/`
omitted), produced from `plugins/` by `scripts/sync-skills.sh` — edit under
`plugins/`, then re-run the script (`scripts/check.sh` fails if `skills/` is stale).

```
.
├── .claude-plugin/marketplace.json     # marketplace manifest (Claude Code install)
├── install.sh                          # install skills into another harness
├── scripts/sync-skills.sh              # regenerate skills/ from plugins/ (+ --check)
├── skills/                             # GENERATED flat tree; plugins/ is canonical
├── plugins/
│   ├── reasoning-semiformally/
│   │   ├── .claude-plugin/plugin.json
│   │   ├── skills/reasoning-semiformally/
│   │   └── README.md
│   ├── spec-creator/
│   │   ├── .claude-plugin/plugin.json
│   │   ├── skills/{spec-creator,spec-reviewer,development-guidelines}/
│   │   └── README.md
│   ├── spec-planner/
│   │   ├── .claude-plugin/plugin.json
│   │   ├── skills/{spec-planner,done-certificates}/
│   │   └── README.md
│   ├── jj-workspaces/
│   │   ├── .claude-plugin/plugin.json
│   │   ├── skills/using-jj-workspaces/
│   │   └── README.md
│   └── spec-builder/
│       ├── .claude-plugin/plugin.json
│       ├── skills/spec-builder/                 # orchestrator
│       │   └── references/                       # orchestration, workspaces (jj+git), subagent-brief, build-loop, portability
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
