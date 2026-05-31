#!/usr/bin/env bash
#
# install.sh — make the skills in this repo discoverable by a coding harness.
#
# Every skill in this repo is a standard Agent Skill (a `SKILL.md` directory,
# https://github.com/agentskills/agentskills). Claude Code consumes them through
# the plugin marketplace (`.claude-plugin/marketplace.json`); this script wires
# them into the discovery directories used by other harnesses.
#
# The neutral standard path `.agents/skills/` (project) and `~/.agents/skills/`
# (global) is read by Codex, Cursor, Pi, and OpenCode — so one target covers all
# four. Kiro reads only its own `.kiro/skills/`; Claude Code uses the marketplace
# (or its own `.claude/skills/`).
#
# It does NOT move or restructure the repo: the skills stay where they live
# (plugins/<plugin>/skills/<name>/), and each is symlinked (or copied) into the
# target directory under its own name.
#
# Usage:
#   ./install.sh <harness> [--global | --project [DIR]] [--copy] [--dry-run] [--force]
#
#   <harness>            global target(s)                project target(s)
#     agents             ~/.agents/skills               .agents/skills
#     codex              ~/.agents/skills               .agents/skills
#     cursor             ~/.cursor/skills               .cursor/skills
#     pi                 ~/.pi/agent/skills             .pi/skills
#     opencode           ~/.config/opencode/skills      .opencode/skills
#     kiro               ~/.kiro/skills                 .kiro/skills
#     claude             ~/.claude/skills               .claude/skills
#     all                ~/.agents/skills + ~/.kiro/skills   (covers every harness
#                        above except Claude, which uses the plugin marketplace)
#
#   --global          install into the home-directory location(s) (default)
#   --project [DIR]    install into DIR (default: current directory)
#   --copy            copy skill directories instead of symlinking
#   --dry-run         print what would happen, change nothing
#   --force           replace an existing non-symlink destination entry
#
# Examples:
#   ./install.sh all                 # ~/.agents/skills + ~/.kiro/skills (global)
#   ./install.sh codex               # ~/.agents/skills (also serves Cursor/Pi/OpenCode)
#   ./install.sh cursor --project ~/work/myrepo
#   ./install.sh kiro --global
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
    agents|codex|cursor|pi|opencode|kiro|claude|all)
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
      sed -n '2,52p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown argument: $1 (try --help)" ;;
  esac
done

[ -n "$harness" ] || die "no harness given (agents|codex|cursor|pi|opencode|kiro|claude|all). Try --help."

# --- resolve destination directory(ies) --------------------------------------
dests=()
if [ "$scope" = "global" ]; then
  case "$harness" in
    agents|codex) dests=("$HOME/.agents/skills") ;;
    cursor)       dests=("$HOME/.cursor/skills") ;;
    pi)           dests=("$HOME/.pi/agent/skills") ;;
    opencode)     dests=("$HOME/.config/opencode/skills") ;;
    kiro)         dests=("$HOME/.kiro/skills") ;;
    claude)       dests=("$HOME/.claude/skills") ;;
    all)          dests=("$HOME/.agents/skills" "$HOME/.kiro/skills") ;;
  esac
else
  base="$(cd "$project_dir" 2>/dev/null && pwd)" || die "project dir not found: $project_dir"
  case "$harness" in
    agents|codex) dests=("$base/.agents/skills") ;;
    cursor)       dests=("$base/.cursor/skills") ;;
    pi)           dests=("$base/.pi/skills") ;;
    opencode)     dests=("$base/.opencode/skills") ;;
    kiro)         dests=("$base/.kiro/skills") ;;
    claude)       dests=("$base/.claude/skills") ;;
    all)          dests=("$base/.agents/skills" "$base/.kiro/skills") ;;
  esac
fi

printf 'Installing skills from %s\n' "$REPO_ROOT"
printf '  harness: %s   scope: %s   mode: %s\n' "$harness" "$scope" "$mode"
printf '  target(s): %s\n\n' "${dests[*]}"

# --- link one skill into one destination -------------------------------------
link_one() {
  skill_dir="$1"; name="$2"; dest="$3"
  target="$dest/$name"

  if [ "$dry_run" -eq 1 ]; then
    printf '  would %s  %s -> %s\n' "$mode" "$name" "$skill_dir"; return 0
  fi

  if [ -e "$target" ] || [ -L "$target" ]; then
    if [ -L "$target" ]; then
      rm -f "$target"                      # refresh our own (or a stale) symlink
    elif [ "$force" -eq 1 ]; then
      rm -rf "$target"
    else
      printf '  skip  %s  (exists, not a symlink — use --force to replace)\n' "$name"
      return 0
    fi
  fi

  if [ "$mode" = "copy" ]; then cp -R "$skill_dir" "$target"; else ln -s "$skill_dir" "$target"; fi
  printf '  ok    %s\n' "$name"
  linked=$((linked + 1))
}

# --- discover skills and install them into every destination -----------------
# A skill is any plugins/<plugin>/skills/<name>/SKILL.md directory.
linked=0
shopt -s nullglob
for dest in "${dests[@]}"; do
  [ ${#dests[@]} -gt 1 ] && printf '%s\n' "-> $dest"
  [ "$dry_run" -eq 1 ] || mkdir -p "$dest"
  seen=""
  for skill_md in "$REPO_ROOT"/plugins/*/skills/*/SKILL.md; do
    skill_dir="$(dirname "$skill_md")"
    name="$(basename "$skill_dir")"
    # The standard requires name == directory; guard against two plugins
    # shipping a same-named skill (would collide at the destination).
    case " $seen " in
      *" $name "*) die "duplicate skill name '$name' — two source dirs map to $dest/$name" ;;
    esac
    seen="$seen $name"
    link_one "$skill_dir" "$name" "$dest"
  done
done
shopt -u nullglob

printf '\nDone. %d link(s) %s.\n' "$linked" \
  "$( [ "$dry_run" -eq 1 ] && echo 'would be created' || echo created )"

case "$harness" in
  pi|all)
    cat <<'EOF'

Note (Pi): spec-builder and using-jj-workspaces orchestrate sub-agents. Pi only
gains a sub-agent dispatch tool when a subagents extension is installed, e.g.:
    pi install npm:@tintinweb/pi-subagents
Reload/restart Pi afterwards so the dispatch tool registers. Without it, those
two skills fall back to a sequential, single-agent mode (see each skill's
references/portability.md). All other skills work unchanged.
EOF
  ;;
esac
