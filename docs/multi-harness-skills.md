# Recommendation: Making these skills installable across coding harnesses

**Goal:** distribute the skills in this repo to harnesses that implement the
[Agent Skills standard](https://github.com/agentskills/agentskills) —
specifically **Pi** ([pi.dev](https://pi.dev/docs/latest/skills)) and
**OpenCode** ([opencode.ai](https://opencode.ai/docs/skills/)) — without
abandoning the existing Claude Code plugin packaging.

Date: 2026-05-31.

---

## TL;DR

1. **The skills are already in the right format.** All 10 `SKILL.md` files have
   standard-compliant frontmatter (`name` matches the parent directory,
   lowercase-hyphen, `description` present), use only `references/` subdirs, and
   contain **no `${CLAUDE_PLUGIN_ROOT}` interpolation** or other hard
   Claude-Code path coupling. Packaging — not format — is the gap.

2. **`.agents/skills/` is the universal path.** Both Pi and OpenCode discover
   skills under the vendor-neutral `.agents/skills/` (project) and
   `~/.agents/skills/` (global) directories defined by the standard. Targeting
   that one location covers both harnesses at once, and any future
   standard-compliant harness for free.

3. **Recommended approach:** keep the Claude Code plugins as-is, add a flat
   canonical `skills/` tree as the single source of truth, and ship a tiny
   installer that symlinks skills into each harness's discovery directory — the
   same "native packaging + shared skill bodies" model that
   [obra/superpowers](https://github.com/obra/superpowers) uses. No content is
   duplicated.

4. **The real work is semantic, not structural.** A few skills assume Claude
   Code's sub-agent orchestration (`spec-builder` most of all). They install
   everywhere but only *behave* correctly where the harness can dispatch
   sub-agents. Classify and gate these; ship the portable skills first.

---

## 1. Current state

```
plugins/
  reasoning-semiformally/  .claude-plugin/plugin.json   skills/reasoning-semiformally/SKILL.md
  spec-creator/            .claude-plugin/plugin.json   skills/{spec-creator,spec-reviewer,development-guidelines}/SKILL.md
  spec-planner/            .claude-plugin/plugin.json   skills/{spec-planner,done-certificates}/SKILL.md
  spec-builder/            .claude-plugin/plugin.json   skills/{spec-builder,semi-formal-review,validate-done-certificate}/SKILL.md
  jj-workspaces/           .claude-plugin/plugin.json   skills/using-jj-workspaces/SKILL.md
.claude-plugin/marketplace.json
```

- **10 skills**, each a standard `skill-name/SKILL.md (+ references/)` directory.
- These plugins ship **skills only** — no `commands/`, `agents/`, or `hooks/`
  components, and no executable `scripts/`. That makes them unusually portable:
  the payload is markdown + reference markdown.
- Frontmatter audit: every `name:` equals its parent directory name and is
  lowercase-hyphen — already passes the standard's strict naming rule. No
  changes required to satisfy `agentskills validate`.

The Claude-Code-specific surface is therefore just:

- the `plugins/<p>/skills/<s>/` **nesting** (Claude plugins group skills under a
  plugin; the standard wants a flat skills directory), and
- the `.claude-plugin/plugin.json` + `marketplace.json` **manifests** (Claude
  Code's distribution mechanism, ignored by other harnesses).

## 2. How each target discovers skills

All three consume the identical `SKILL.md` format. They differ only in *where*
they look.

| Harness | Project paths | Global paths |
|---|---|---|
| **Agent Skills standard** | `.agents/skills/<name>/SKILL.md` | `~/.agents/skills/<name>/SKILL.md` |
| **OpenCode** | `.opencode/skills/`, `.claude/skills/`, **`.agents/skills/`** | `~/.config/opencode/skills/`, `~/.claude/skills/`, **`~/.agents/skills/`** |
| **Pi** | `.pi/skills/`, **`.agents/skills/`** (+ ancestors), npm-package `skills/`, settings `skills[]`, `--skill <path>` | `~/.pi/agent/skills/`, **`~/.agents/skills/`** |
| **Claude Code** | `.claude/skills/` + plugins | `~/.claude/skills/` + installed plugins |

Three observations drive the design:

- **`.agents/skills/` is read by Pi *and* OpenCode** (project and global). One
  target satisfies both.
- **`.claude/skills/` is also read by OpenCode** (project and global) — Claude
  Code and OpenCode already overlap, so a `.claude/skills/` install reaches both.
- **Pi relaxes the name-must-match-directory rule**; OpenCode and the strict
  standard do not. Keep names matching directories (we already do) so every
  consumer is happy.

## 3. Recommended architecture

Adopt the superpowers model, scoped to our skills-only repo:

> **One canonical, flat, standard-compliant `skills/` tree is the source of
> truth. Every harness — including Claude Code — consumes it through its own
> native mechanism via symlinks. Nothing is copied or forked.**

### 3a. Canonical source of truth

Create a flat top-level directory holding the real skill content:

```
skills/                         # canonical, agent-skills-standard layout
  reasoning-semiformally/  SKILL.md  references/...
  spec-creator/            SKILL.md  references/...
  spec-reviewer/           SKILL.md  references/...
  development-guidelines/  SKILL.md  references/...
  spec-planner/            SKILL.md  references/...
  done-certificates/       SKILL.md  references/...
  spec-builder/            SKILL.md  references/...
  semi-formal-review/      SKILL.md  references/...
  validate-done-certificate/ SKILL.md references/...
  using-jj-workspaces/     SKILL.md  references/...
```

Two ways to reconcile this with the existing `plugins/` tree — pick one:

- **Option A (recommended): `skills/` is canonical, plugins symlink in.**
  Move the skill directories to `skills/` and replace each
  `plugins/<p>/skills/<s>` with a symlink to `../../../skills/<s>`. Claude Code
  plugins keep working unchanged; the flat tree becomes the portable artifact.
  *Risk:* Claude Code's plugin loader must follow symlinks (it does for plugin
  contents on macOS/Linux; verify on the install target).

- **Option B (lowest risk to Claude Code): `plugins/` stays canonical, `skills/`
  is generated.** Keep skills where they are; a build/install step symlinks each
  `plugins/<p>/skills/<s>` into the flat `skills/<s>` tree (and onward into each
  harness). No change to how Claude Code resolves anything today.

Both end at the same place. **Option A** is cleaner long-term (the standard's
flat layout is the primary artifact and Claude is the adapter); **Option B** is
safer if you don't want to touch the working plugin install at all yet. Given
the skills are pure markdown with no `${CLAUDE_PLUGIN_ROOT}` references,
Option A's symlink risk is low — recommend A, fall back to B if the Claude Code
plugin loader on the target doesn't traverse symlinks.

### 3b. Per-harness install

A single `install.sh` (**shipped at the repo root**) symlinks every skill — each
discovered as a `plugins/*/skills/*/SKILL.md` directory, so no repo restructure is
required — into the requested harness's discovery directory:

```sh
# ./install.sh <harness> [--global | --project [DIR]] [--copy] [--dry-run] [--force]
#   pi        -> ~/.pi/agent/skills/<name>        (project: .pi/skills)
#   opencode  -> ~/.config/opencode/skills/<name> (project: .opencode/skills)
#   claude    -> ~/.claude/skills/<name>          (project: .claude/skills)
#   agents    -> ~/.agents/skills/<name>          (project: .agents/skills)
#   all       -> ~/.agents/skills/<name>          (the standard path Pi + OpenCode both read)
```

It is idempotent (refreshes its own symlinks), refuses to clobber non-symlink
entries without `--force`, supports `--copy` for symlink-less environments, and
prints the Pi subagents-extension hint after a `pi`/`all` install.

Mechanism per harness:

- **Pi & OpenCode — preferred:** symlink each `skills/<name>` into
  `~/.agents/skills/<name>` (global) or `<repo>/.agents/skills/` (project,
  committed to the consuming repo). One target, both harnesses, standard path.
- **Pi — alternatives if you publish to npm:** Pi auto-discovers `skills/` inside
  npm packages, so `pi` users could also `npm i @antstanley/skills` and Pi finds
  them with zero install step. Worth doing if you want frictionless `pi` adoption.
- **OpenCode — gate with permissions** in `opencode.json` if desired:
  ```json
  { "permission": { "skill": { "*": "allow" } } }
  ```
- **Claude Code — unchanged:** keep `/plugin install` against the existing
  `marketplace.json`. (Symlinking into `~/.claude/skills/` also works and is what
  reaches OpenCode's `~/.claude/skills/` lookup, but the plugin path is the
  idiomatic Claude distribution and should stay the headline install.)

Symlinks (not copies) keep a single editable source; a `--copy` flag for
environments without symlink support (some Windows setups — cf. superpowers'
`node_modules` workaround).

### 3c. Resulting repo shape

```
skills/                     # canonical, portable (the artifact other harnesses consume)
plugins/                    # Claude Code plugins (symlink/point into skills/)
.claude-plugin/marketplace.json
.agents/skills/             # optional: committed project-level install for this repo's own use
install.sh                  # fan-out installer
docs/multi-harness-skills.md
```

## 4. Frontmatter additions (optional, cheap, recommended)

The standard defines optional fields worth adding now that consumers vary:

- **`compatibility`** — flag the orchestration-dependent skills, e.g.
  `compatibility: Best in harnesses that can dispatch sub-agents (Claude Code).`
  on `spec-builder`. Purely informational but honest.
- **`license`** — add the repo license so redistributed skills carry it.
- **`metadata.version`** / **`metadata.author`** — Claude `plugin.json` carries
  `version`/`author` today; mirror them into skill `metadata` so the data
  survives once skills are consumed outside the plugin wrapper.
- **`allowed-tools`** (experimental) — leave unset; support varies by harness.

These are additive and don't affect Claude Code.

## 5. The real work: semantic portability

Format portability is essentially free. **Behavioural** portability is the work,
because some skills assume Claude Code capabilities. Classification:

| Skill | Portability | Notes |
|---|---|---|
| `reasoning-semiformally` | **Drop-in** | Pure reasoning methodology; no harness coupling. |
| `spec-creator` | **Drop-in** | Investigate→write workflow; no sub-agents. |
| `spec-reviewer` | **Drop-in** | Review methodology. |
| `development-guidelines` | **Drop-in** | Authoring guidance. |
| `spec-planner` | **Drop-in** | Produces plan files; no orchestration. |
| `done-certificates` | **Mostly** | References a "validating agent" but is single-agent authoring. |
| `semi-formal-review` | **Mostly** | Single-agent review protocol. |
| `validate-done-certificate` | **Mostly** | Single-agent validation protocol. |
| `using-jj-workspaces` | **Conditional** | Workspace creation is harness-agnostic jj; only the sub-agent-per-workspace pattern needs a dispatch tool. Now carries a preflight note + `compatibility:` field. |
| `spec-builder` | **Per-harness** | Core value is dispatching one sub-agent per task. See the sub-agent matrix below — drop-in on OpenCode, extension-gated on Pi. Now carries a Preflight step, `references/portability.md`, and a `compatibility:` field. |

### Sub-agent dispatch: the deciding capability

`spec-builder` (and the parallel path of `using-jj-workspaces`) live or die on whether
the host harness can **dispatch sub-agents**. The three targets differ:

| Capability | Claude Code | OpenCode | Pi |
|---|---|---|---|
| Dispatch tool | `Task` (core) | `Task` (core) | `Agent` — **extension only** (`@tintinweb/pi-subagents` et al.) |
| Isolated context | own window | child sessions | child sessions |
| Parallel | yes | yes | yes (extension) |
| Agent definitions | markdown frontmatter | markdown frontmatter / JSON | TS extension config |
| Stable target for a portable skill? | yes | yes | **no** — varies by fork |

Design consequences, now implemented in the skills:

- **Gate on the capability, not the harness.** There is no reliable runtime
  "which harness am I" signal, and you don't need one — the skill checks its own
  toolset for a dispatch tool (`Task`/`Agent`/equivalent). This single gate lets
  Claude Code and OpenCode proceed and only drops bare Pi into the fallback.
- **OpenCode** is a near-clone of Claude Code's model, so `spec-builder` is
  drop-in there once installed.
- **Pi** needs a subagents extension; competing forks register different tool
  names, so the skill depends on *some* dispatch tool, never a specific API. When
  absent it offers the install command (`pi install npm:@tintinweb/pi-subagents`,
  then reload) or a **sequential single-agent fallback** that keeps both gates as
  separate review passes and reports which mode ran.

See `plugins/spec-builder/skills/spec-builder/references/portability.md` for the
full matrix, the detection ladder, and the fallback protocol.

Recommended sequencing:

1. **Phase 1 — ship the 8 drop-in/mostly skills** to Pi and OpenCode via
   `.agents/skills/`. Immediate value, zero behavioural risk.
2. **Phase 2 — port `using-jj-workspaces` and `spec-builder`.** Either (a) add a
   harness-neutral "if your harness can't dispatch sub-agents, run tasks
   sequentially in-context" fallback section, or (b) keep them Claude-Code-only
   and mark `compatibility:` accordingly. Don't block Phase 1 on this.

A `references/portability.md` per ported skill (rather than littering the body
with "in Claude Code, do X; in Pi, do Y") keeps the main `SKILL.md` clean and
under the standard's 500-line guidance.

## 6. Validation & CI

- Add the standard's validator to `scripts/check.sh`:
  ```sh
  npx -y @agentskills/skills-ref validate ./skills/*   # or the published equivalent
  ```
- Keep a test that asserts `name:` == parent dir for every `SKILL.md` (already
  passing) so the strict OpenCode/standard rule never regresses.
- Optionally a smoke check that the symlink fan-out resolves (no dangling links).

## 7. Risks & open questions

- **Symlink traversal** by the Claude Code plugin loader (Option A) — verify on
  the target OS before committing; fall back to Option B otherwise.
- **`spec-builder` semantics** on Pi/OpenCode — needs a decision: degraded mode
  vs. Claude-Code-only. (Recommend: mark Claude-Code-only initially, port later.)
- **Pi npm auto-discovery** — only worth wiring if you intend to publish to npm;
  otherwise the `.agents/skills/` symlink covers Pi already.
- **Global vs project install** — global (`~/.agents/skills/`) is best for the
  author's own machines; committing a project-level `.agents/skills/` into a
  *consuming* repo is best for teams. Support both via the installer flag.
- **Standard maturity** — `allowed-tools` is experimental and the `skills-ref`
  validator API may move; pin versions in CI.

## Bottom line

The skills are already standard-shaped. Make a flat canonical `skills/` tree the
source of truth, symlink it into each harness (`.agents/skills/` reaches Pi and
OpenCode in one move; the existing plugin marketplace stays the Claude Code
path), ship the 8 portable skills first, and treat `spec-builder` /
`using-jj-workspaces` as a follow-up porting task because their value depends on
sub-agent orchestration the other harnesses implement differently.
