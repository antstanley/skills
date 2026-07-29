# skills

A collection of [Agent Skills](https://github.com/agentskills/agentskills) by Ant
Stanley, in two families:

- **Spec-driven development** — define a spec, plan its implementation, then
  build it task by task behind correctness and completeness gates.
- **Security review** — repository, diff, and deep multi-pass scans that produce
  a sealed, machine-readable scan contract plus a generated report and SARIF.
  A fork of OpenAI's [codex-security](https://github.com/openai/codex-security),
  ported from Codex to Claude Code.

Packaged as a Claude Code plugin marketplace, and installable into any harness
that supports the Agent Skills standard (Codex, Cursor, Pi, OpenCode, Zed, Kiro).

## Install

### Claude Code — plugin marketplace

Register the marketplace once, then install whichever plugins you want. Plugins
are self-contained, so any one works on its own.

```
/plugin marketplace add antstanley/skills
```

| Plugin | Skills | Provides |
|---|---|---|
| `/plugin install spec-creator@skills` | 3 | Write, review, and add guidelines to a canonical design spec. |
| `/plugin install spec-planner@skills` | 2 | Decompose a spec into a dependency-ordered task plan with done certificates. |
| `/plugin install spec-builder@skills` | 3 | Execute a plan, one sub-agent per task, behind two gates. |
| `/plugin install reasoning-semiformally@skills` | 1 | The semi-formal certificate reasoning method both gates build on. |
| `/plugin install jj-workspaces@skills` | 1 | Isolated jj workspaces for parallel and sub-agent work. |
| `/plugin install security@skills` | 13 | Security scans, triage, remediation, and reporting. Forked from [codex-security](https://github.com/openai/codex-security). |

For the full spec → plan → build flow install `spec-creator`, `spec-planner`, and
`spec-builder`. For security review, `security` alone is enough.

### Every other harness — `install.sh`

The installer copies the generated flat [`skills/`](skills/) tree into a
harness's discovery directory. All 23 skills are installed together; there is no
per-plugin selection outside Claude Code.

```
./install.sh all                              # every harness except Claude Code, global
./install.sh codex                            # one target
./install.sh cursor --project ~/work/myrepo   # per-project instead of global
./install.sh opencode --symlink               # link instead of copy (live updates)
./install.sh all --dry-run                    # print what would happen, change nothing
```

| Target | Global (default) | `--project [DIR]` |
|---|---|---|
| `all` | `~/.agents/skills` + `~/.kiro/skills` | `.agents/skills` + `.kiro/skills` |
| `agents`, `codex`, `zed` | `~/.agents/skills` | `.agents/skills` |
| `cursor` | `~/.cursor/skills` | `.cursor/skills` |
| `pi` | `~/.pi/agent/skills` | `.pi/skills` |
| `opencode` | `~/.config/opencode/skills` | `.opencode/skills` |
| `kiro` | `~/.kiro/skills` | `.kiro/skills` |
| `claude` | `~/.claude/skills` | `.claude/skills` |

`~/.agents/skills` is the neutral standard path read by Codex, Cursor, Pi,
OpenCode, and Zed, so `all` — that path plus Kiro's own — covers every harness
except Claude Code, which uses the marketplace above. The per-harness targets are
there when you would rather install into a harness's native directory.

Skills are **copied** by default; re-running refreshes them. `--symlink` links
instead, which live-updates but leaves dangling links if the repo moves.
`--force` replaces a destination entry that is not a managed skill.

> **Pi:** `spec-builder` and `using-jj-workspaces` dispatch sub-agents, which Pi
> only supports with a subagents extension (`pi install npm:@tintinweb/pi-subagents`).
> Without it those two fall back to sequential single-agent mode; every other
> skill works unchanged.

If `skills/` is missing or stale, run `scripts/sync-skills.sh` first.

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

### Spec-driven development

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

### Security

All thirteen ship in the [`security`](plugins/security/) plugin — a fork of
[codex-security](https://github.com/openai/codex-security), OpenAI's built-in
security plugin for Codex, ported to Claude Code.

The port replaces the host integration rather than shimming it. The Codex desktop
MCP server, its connector manifest, and the Codex `config.toml` capability
preflight are gone; sub-agent fan-out, `AskUserQuestion`, the task list, and MCP
servers take their place. Artifact identifiers were renamed to match, so scan
bundles produced by upstream `codex-security` are not readable here.

Licensed Apache-2.0, retaining OpenAI's copyright notice. See
[`plugins/security/LICENSE.md`](plugins/security/LICENSE.md) for the full
statement of changes.

Every scan mode writes the same canonical JSON, which a deterministic finalizer
seals and projects into `report.md` and SARIF.

| Skill | Role |
|---|---|
| [security-scan](plugins/security/skills/security-scan/) | Standard single-pass audit of a repository or scoped path. |
| [security-diff-scan](plugins/security/skills/security-diff-scan/) | Review a pull request, commit, branch diff, or working-tree patch. |
| [deep-security-scan](plugins/security/skills/deep-security-scan/) | Exhaustive audit — repeats discovery across parallel sub-agents until it saturates. |
| [threat-model](plugins/security/skills/threat-model/) | Phase 1 — build or reuse the repository threat model. |
| [finding-discovery](plugins/security/skills/finding-discovery/) | Phase 2 — surface candidate findings across the in-scope files. |
| [validation](plugins/security/skills/validation/) | Phase 3 — decide whether each candidate is real. |
| [attack-path-analysis](plugins/security/skills/attack-path-analysis/) | Phase 4 — trace source to sink and calibrate severity. |
| [triage-finding](plugins/security/skills/triage-finding/) | Static repo-impact triage of findings you already have (SARIF, CVEs, scanner tickets, Jira/Linear issues). |
| [fix-finding](plugins/security/skills/fix-finding/) | Generate, apply, and verify a minimal remediation patch. |
| [vulnerability-writeup](plugins/security/skills/vulnerability-writeup/) | Write the detailed per-finding report. |
| [propose-security-hardening](plugins/security/skills/propose-security-hardening/) | Structural hardening options across the whole finding set. |
| [track-findings](plugins/security/skills/track-findings/) | File findings as Linear, Jira, or GitHub issues, or draft GitHub security advisories. |
| [define-security-policy](plugins/security/skills/define-security-policy/) | Author a repository's `SECURITY.md` policy. |

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
│   ├── spec-builder/
│   │   ├── .claude-plugin/plugin.json
│   │   ├── skills/spec-builder/                 # orchestrator
│   │   │   └── references/                       # orchestration, workspaces (jj+git), subagent-brief, build-loop, portability
│   │   ├── skills/semi-formal-review/           # gate 1 — correctness
│   │   ├── skills/validate-done-certificate/    # gate 2 — completeness
│   │   └── README.md
│   └── security/
│       ├── .claude-plugin/plugin.json
│       ├── skills/                              # 13 skills — scans, phases, triage, remediation
│       ├── references/                          # scan contract, artifact paths, report + preflight specs
│       ├── schemas/                             # JSON Schemas for the sealed scan contract
│       ├── scripts/                             # finalizer, SARIF export, preflight, target identity
│       ├── examples/completed-scan/             # worked canonical bundle
│       ├── LICENSE.md                           # Apache-2.0 (forked from openai/codex-security)
│       └── README.md
└── .specs/                         # generated design specs & plans
```

## Adding a new plugin

1. Create `plugins/<name>/skills/<name>/SKILL.md` (with YAML frontmatter).
2. Add `plugins/<name>/.claude-plugin/plugin.json` and `plugins/<name>/README.md`.
3. Append an entry for the plugin to `.claude-plugin/marketplace.json`.
4. Run `scripts/sync-skills.sh` to refresh the generated `skills/` tree.
