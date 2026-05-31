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
# (global) is read by Codex, Cursor, Pi, OpenCode, and Zed — so one target covers
# all five. Kiro reads only its own `.kiro/skills/`; Claude Code uses the
# marketplace (or its own `.claude/skills/`).
#
# It installs from the generated flat `skills/` tree (real copies, evals/
# excluded), which scripts/sync-skills.sh regenerates from the canonical
# plugins/. Each skill is copied (or, with --symlink, linked) into the target
# directory under its own name. Run scripts/sync-skills.sh if skills/ is missing.
#
# Usage:
#   ./install.sh <harness> [--global | --project [DIR]] [--copy] [--dry-run] [--force]
#
#   <harness>            global target(s)                project target(s)
#     agents             ~/.agents/skills               .agents/skills
#     codex              ~/.agents/skills               .agents/skills
#     zed                ~/.agents/skills               .agents/skills
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
#   --symlink         symlink skill directories instead of copying (live updates,
#                     but a moved/deleted repo leaves dangling links)
#   --copy            copy skill directories (the default)
#   --dry-run         print what would happen, change nothing
#   --force           overwrite a destination entry that isn't a managed skill
#
# Skills are copied by default; re-running refreshes the managed skill folders.
#
# Examples:
#   ./install.sh all                 # ~/.agents/skills + ~/.kiro/skills (global)
#   ./install.sh codex               # ~/.agents/skills (also serves Cursor/Pi/OpenCode/Zed)
#   ./install.sh cursor --project ~/work/myrepo
#   ./install.sh kiro --global
#   ./install.sh opencode --symlink  # link instead of copy
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

harness=""
scope="global"
project_dir="$PWD"
mode="copy"
dry_run=0
force=0

die() { printf 'install.sh: %s\n' "$1" >&2; exit 1; }

# --- parse args --------------------------------------------------------------
while [ $# -gt 0 ]; do
  case "$1" in
    agents|codex|zed|cursor|pi|opencode|kiro|claude|all)
      [ -z "$harness" ] || die "harness already set to '$harness'"
      harness="$1"; shift ;;
    --global)  scope="global"; shift ;;
    --project)
      scope="project"; shift
      if [ $# -gt 0 ] && [ "${1#--}" = "$1" ]; then project_dir="$1"; shift; fi ;;
    --symlink) mode="symlink"; shift ;;
    --copy)    mode="copy"; shift ;;
    --dry-run) dry_run=1; shift ;;
    --force)   force=1; shift ;;
    -h|--help)
      sed -n '2,50p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown argument: $1 (try --help)" ;;
  esac
done

[ -n "$harness" ] || die "no harness given (agents|codex|zed|cursor|pi|opencode|kiro|claude|all). Try --help."

# --- resolve destination directory(ies) --------------------------------------
dests=()
if [ "$scope" = "global" ]; then
  case "$harness" in
    agents|codex|zed) dests=("$HOME/.agents/skills") ;;
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
    agents|codex|zed) dests=("$base/.agents/skills") ;;
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

# --- install one skill into one destination ----------------------------------
install_one() {
  skill_dir="$1"; name="$2"; dest="$3"
  target="$dest/$name"

  if [ "$dry_run" -eq 1 ]; then
    printf '  would %s  %s -> %s\n' "$mode" "$name" "$skill_dir"; return 0
  fi

  # Refresh an existing entry that is ours to manage — our own symlink, or a
  # skill folder (a directory holding a SKILL.md). Anything else (a foreign file
  # or a non-skill directory of the same name) is left alone unless --force.
  if [ -L "$target" ]; then
    rm -f "$target"
  elif [ -d "$target" ] && [ -f "$target/SKILL.md" ]; then
    rm -rf "$target"
  elif [ -e "$target" ]; then
    if [ "$force" -eq 1 ]; then
      rm -rf "$target"
    else
      printf '  skip  %s  (exists, not a managed skill — use --force to replace)\n' "$name"
      return 0
    fi
  fi

  if [ "$mode" = "copy" ]; then cp -R "$skill_dir" "$target"; else ln -s "$skill_dir" "$target"; fi
  printf '  ok    %s\n' "$name"
  linked=$((linked + 1))
}

# --- discover skills and install them into every destination -----------------
# Install from the generated flat skills/ tree (real copies, evals/ excluded).
# It is regenerated from the canonical plugins/ by scripts/sync-skills.sh.
shopt -s nullglob
sources=("$REPO_ROOT"/skills/*/SKILL.md)
shopt -u nullglob
[ ${#sources[@]} -gt 0 ] || die "skills/ is empty or missing — run scripts/sync-skills.sh first."

linked=0
for dest in "${dests[@]}"; do
  [ ${#dests[@]} -gt 1 ] && printf '%s\n' "-> $dest"
  [ "$dry_run" -eq 1 ] || mkdir -p "$dest"
  for skill_md in "${sources[@]}"; do
    skill_dir="$(dirname "$skill_md")"
    name="$(basename "$skill_dir")"
    install_one "$skill_dir" "$name" "$dest"
  done
done

printf '\nDone. %d skill(s) %s.\n' "$linked" \
  "$( [ "$dry_run" -eq 1 ] && echo 'would be installed' || echo installed )"

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
