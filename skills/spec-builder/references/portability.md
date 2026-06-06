# Portability — running spec-builder across harnesses

spec-builder's core mechanic is **dispatching one sub-agent per task** into an
isolated workspace, gated by two reviews run by an agent other than the builder.
That mechanic depends on the host harness exposing a **sub-agent dispatch tool**.
Harnesses differ here, so confirm the capability before orchestrating — and
degrade gracefully when it is absent.

This file backs the *Preflight* step in `SKILL.md`. Read it before Phase 1 when
you are unsure whether the current harness can dispatch sub-agents.

## What each harness provides

| Harness | Dispatch tool | Isolated context | Parallel | Notes |
|---|---|---|---|---|
| **Claude Code** | `Task` (core) | yes — own context window | yes | The skill's native target. |
| **OpenCode** | `Task` (core) | yes — child sessions | yes | Subagents defined in `~/.config/opencode/agents/` or `.opencode/agents/`; gated by `permission.task`. Maps almost 1:1 to Claude Code. |
| **Cursor** | core subagents (since 2.4) | yes | yes | Native subagent support; gate on the dispatch tool as elsewhere. |
| **Codex** | subagents via plugins | yes | yes | Sub-agent / plugin ecosystem; confirm a dispatch tool is present before relying on it. |
| **Zed** | core subagents (since v0.227.1) | yes | yes | Agent Panel spawns subagents to parallelize; subagent model configurable, else inherits the parent thread's. |
| **Pi** | `Agent` — **extension only** | yes — child sessions | yes | Not in Pi core. Provided by a subagents extension, e.g. `@tintinweb/pi-subagents` (registers `Agent`, `get_subagent_result`, `steer_subagent`). Competing forks exist and may name the tool differently. |

There is **no standard runtime API** for "which harness am I in." Do not try to
detect the harness by name. Gate on the **capability** instead — it is the thing
you actually need, and it makes harness identity irrelevant.

## Preflight: gate on the dispatch tool, not the harness

Before Phase 3 (the wave scheduler), confirm you can dispatch sub-agents:

1. **Check your own toolset** for a sub-agent dispatch tool. Match on capability,
   not one exact name — `Task` (Claude Code, OpenCode) or `Agent` (Pi +
   pi-subagents) or an equivalent `delegate`/`spawn` tool.
   - **Present** → proceed with the parallel, gated build as written.
   - **Absent** → you are most likely in Pi without a subagents extension (or a
     harness that cannot dispatch). Do **not** fake parallelism or grade work
     with the builder. Take the *Tool absent* branch below.

2. *(Optional confirmation only)* a deterministic probe, if you want certainty
   beyond your tool list — check Pi's extension locations
   (`~/.pi/agent/extensions/`, `.pi/extensions/`, the `packages`/`extensions`
   arrays in `~/.pi/settings.json` or `.pi/settings.json`) or `npm ls
   @tintinweb/pi-subagents`. Treat this as confirmation, never the primary gate:
   forks install differently and register different tool names.

## Tool absent — two honest paths

When no dispatch tool is available, surface the situation and offer the user a
choice. Never silently install anything, and never pretend the gates ran.

**(a) Enable sub-agents (recommended on Pi).** Tell the user the orchestrated
build needs a dispatch tool and offer the install command:

```
pi install npm:@tintinweb/pi-subagents
```

Then **reload/restart Pi** so the `Agent` tool registers, and re-run the build.
Name this fork as the default but note alternatives exist
(`nicobailon/pi-subagents`, `HazAT/pi-interactive-subagents`); the skill does not
depend on a specific one — only on *some* dispatch tool being present.

**(b) Sequential single-agent fallback.** If the user declines, run the build
**in-context, one task at a time**, preserving every invariant except physical
sub-agent isolation:

- Walk the same dependency order from the plan's dependency table; `max_parallel`
  is effectively 1.
- Build each task directly in the integration workspace (still branch a workspace
  per task if the VCS supports it — workspace isolation is independent of
  sub-agent dispatch; see `references/workspaces.md`).
- **Keep both gates.** Run semi-formal-review (correctness) and
  validate-done-certificate (completeness) as separate review *passes* with fresh
  framing — explicitly adopt a reviewer stance distinct from the implementer's,
  and judge only against the task's definition of done. This is weaker than a
  different agent grading the work (it cannot fully prevent self-grading bias),
  so **say so in the report**: note that gates ran in single-agent mode.
- Merge and **move the task (with its `-certificate.md`) into `done/`** exactly as in the
  normal loop — or into `blocked/` on a park — performed by the orchestrator on the main tree,
  then recompute `plan.md`'s `Status` from the subfolders.

State plainly in the build summary which mode ran. The whole point of the skill —
two gates, neither self-reported — is best honoured by real sub-agents; the
fallback keeps the *workflow* working where the harness can't dispatch, and is
transparent about the reduced isolation.
