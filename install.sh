#!/usr/bin/env bash
#
# install.sh — make the skills in this repo discoverable by a coding harness.
#
# Every skill in this repo is a standard Agent Skill (a `SKILL.md` directory,
# https://github.com/agentskills/agentskills). Claude Code consumes them through
# the plugin marketplace (`.claude-plugin/marketplace.json`); this script wires
# them into the discovery directories used by other harnesses — Pi and OpenCode
# today, any standard-compliant harness via the shared `.agents/skills/` path.
#
# It does NOT move or restructure the repo: the skills stay where they live
# (plugins/<plugin>/skills/<name>/), and each is symlinked (or copied) into the
# target directory under its own name.
#
# Usage:
#   ./install.sh <harness> [--global | --project [DIR]] [--copy] [--dry-run] [--force]
#
#   <harness>  pi | opencode | claude | agents | all
#                pi       -> ~/.pi/agent/skills        (project: .pi/skills)
#                opencode -> ~/.config/opencode/skills (project: .opencode/skills)
#                claude   -> ~/.claude/skills          (project: .claude/skills)
#                agents   -> ~/.agents/skills          (project: .agents/skills)
#                all      -> ~/.agents/skills  — the standard-neutral path that
#                            BOTH Pi and OpenCode read; one target, both harnesses.
#
#   --global         install into the home-directory location (default)
#   --project [DIR]   install into DIR (default: current directory)
#   --copy           copy skill directories instead of symlinking
#   --dry-run        print what would happen, change nothing
#   --force          replace an existing non-symlink destination entry
#
# Examples:
#   ./install.sh all                 # ~/.agents/skills  (Pi + OpenCode, global)
#   ./install.sh pi --global
#   ./install.sh opencode --project ~/work/myrepo
#   ./install.sh claude --copy       # Claude also has the plugin marketplace
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

harness=""
scope="global"
project_dir="$PWD"
mode="symlink"
dry_run=0
force=0

die() { printf 'install.sh: %s\n' "$1" >&2; exit 1; }

# --- parse args --------------------------------------------------------------
while [ $# -gt 0 ]; do
  case "$1" in
    pi|opencode|claude|agents|all)
      [ -z "$harness" ] || die "harness already set to '$harness'"
      harness="$1"; shift ;;
    --global)  scope="global"; shift ;;
    --project)
      scope="project"; shift
      if [ $# -gt 0 ] && [ "${1#--}" = "$1" ]; then project_dir="$1"; shift; fi ;;
    --copy)    mode="copy"; shift ;;
    --dry-run) dry_run=1; shift ;;
    --force)   force=1; shift ;;
    -h|--help)
      sed -n '2,40p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown argument: $1 (try --help)" ;;
  esac
done

[ -n "$harness" ] || die "no harness given (pi | opencode | claude | agents | all). Try --help."

# --- resolve destination -----------------------------------------------------
if [ "$scope" = "global" ]; then
  case "$harness" in
    pi)       dest="$HOME/.pi/agent/skills" ;;
    opencode) dest="$HOME/.config/opencode/skills" ;;
    claude)   dest="$HOME/.claude/skills" ;;
    agents|all) dest="$HOME/.agents/skills" ;;
  esac
else
  base="$(cd "$project_dir" 2>/dev/null && pwd)" || die "project dir not found: $project_dir"
  case "$harness" in
    pi)       dest="$base/.pi/skills" ;;
    opencode) dest="$base/.opencode/skills" ;;
    claude)   dest="$base/.claude/skills" ;;
    agents|all) dest="$base/.agents/skills" ;;
  esac
fi

printf 'Installing skills from %s\n' "$REPO_ROOT"
printf '  harness: %s   scope: %s   mode: %s\n' "$harness" "$scope" "$mode"
printf '  target:  %s\n\n' "$dest"

[ "$dry_run" -eq 1 ] || mkdir -p "$dest"

# --- discover skills and link them in ----------------------------------------
# A skill is any plugins/<plugin>/skills/<name>/SKILL.md directory.
linked=0
seen=""
shopt -s nullglob
for skill_md in "$REPO_ROOT"/plugins/*/skills/*/SKILL.md; do
  skill_dir="$(dirname "$skill_md")"
  name="$(basename "$skill_dir")"

  # The standard requires the skill name to match its directory; guard against
  # two plugins shipping a same-named skill (would collide at the destination).
  case " $seen " in
    *" $name "*) die "duplicate skill name '$name' — two source dirs map to $dest/$name" ;;
  esac
  seen="$seen $name"

  target="$dest/$name"

  if [ "$dry_run" -eq 1 ]; then
    printf '  would %s  %s -> %s\n' "$mode" "$name" "$skill_dir"
    linked=$((linked + 1)); continue
  fi

  if [ -e "$target" ] || [ -L "$target" ]; then
    if [ -L "$target" ]; then
      rm -f "$target"                      # refresh our own (or a stale) symlink
    elif [ "$force" -eq 1 ]; then
      rm -rf "$target"
    else
      printf '  skip  %s  (exists, not a symlink — use --force to replace)\n' "$name"
      continue
    fi
  fi

  if [ "$mode" = "copy" ]; then
    cp -R "$skill_dir" "$target"
  else
    ln -s "$skill_dir" "$target"
  fi
  printf '  ok    %s\n' "$name"
  linked=$((linked + 1))
done
shopt -u nullglob

printf '\nDone. %d skill(s) %s.\n' "$linked" \
  "$( [ "$dry_run" -eq 1 ] && echo 'would be installed' || echo installed )"

if [ "$harness" = "pi" ] || [ "$harness" = "all" ]; then
  cat <<'EOF'

Note (Pi): spec-builder and using-jj-workspaces orchestrate sub-agents. Pi only
gains a sub-agent dispatch tool when a subagents extension is installed, e.g.:
    pi install npm:@tintinweb/pi-subagents
Reload/restart Pi afterwards so the dispatch tool registers. Without it, those
two skills fall back to a sequential, single-agent mode (see each skill's
references/portability.md). All other skills work unchanged.
EOF
fi
