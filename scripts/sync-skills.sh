#!/usr/bin/env bash
#
# sync-skills.sh — regenerate the flat, standard-layout `skills/` tree from the
# plugins, using real file copies (no symlinks).
#
# The plugins under `plugins/<plugin>/skills/<name>/` are the CANONICAL source of
# truth: they are self-contained so individual skills/plugins can be installed on
# their own. `skills/<name>/` is a generated, vendor-neutral aggregation of all
# skills in one flat directory — the layout the Agent Skills standard expects
# (https://github.com/agentskills/agentskills) — for harnesses or users that want
# to browse or consume every skill from one place.
#
# Because the copy is generated, never edit `skills/` by hand. Edit the skill
# under `plugins/`, then re-run this script.
#
# Usage:
#   scripts/sync-skills.sh           regenerate ./skills from ./plugins
#   scripts/sync-skills.sh --check   verify ./skills is in sync; exit 1 on drift
#
set -euo pipefail

cd "$(dirname "$0")/.."

check=0
[ "${1:-}" = "--check" ] && check=1

SRC_GLOB="plugins/*/skills/*/SKILL.md"

# Build the flat tree into $out (a real directory of copies).
build() {
  out="$1"
  rm -rf "$out"
  mkdir -p "$out"
  seen=""
  shopt -s nullglob
  for skill_md in $SRC_GLOB; do
    skill_dir="$(dirname "$skill_md")"
    name="$(basename "$skill_dir")"
    case " $seen " in
      *" $name "*) echo "sync-skills: duplicate skill name '$name'" >&2; exit 2 ;;
    esac
    seen="$seen $name"
    cp -R "$skill_dir" "$out/$name"
  done
  shopt -u nullglob

  cat > "$out/README.md" <<'EOF'
# skills/ — generated flat tree

**Do not edit anything in this directory.** It is generated from `plugins/` by
`scripts/sync-skills.sh`. The canonical source of every skill is its plugin under
`plugins/<plugin>/skills/<name>/`; this directory is a flat, vendor-neutral copy
of all skills in the layout the [Agent Skills standard](https://github.com/agentskills/agentskills)
expects, for harnesses or people who want them all in one place.

To change a skill, edit it under `plugins/`, then run `scripts/sync-skills.sh`.
EOF
}

if [ "$check" -eq 1 ]; then
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  build "$tmp/skills"
  if [ ! -d skills ]; then
    echo "sync-skills: skills/ is missing — run scripts/sync-skills.sh" >&2
    exit 1
  fi
  if ! diff -rq "$tmp/skills" skills >/dev/null; then
    echo "sync-skills: skills/ is out of sync with plugins/ — run scripts/sync-skills.sh" >&2
    diff -rq "$tmp/skills" skills || true
    exit 1
  fi
  echo "skills/ is in sync with plugins/."
else
  build skills
  count="$(find skills -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')"
  echo "Regenerated skills/ — $count skill(s) copied from plugins/."
fi
