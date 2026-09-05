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
export PATH="$HOME/.local/bin:$PATH"

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
    rm -rf "$out/$name/evals"   # evals/ are internal test artifacts, not part of the distributable skill
  done
  shopt -u nullglob

  # Security's helpers are shared by its skills. Keep one resource bundle in
  # the flat distribution; the installer copies it beside the skill folders.
  mkdir -p "$out/.security-plugin"
  for resource in scripts references schemas; do
    cp -R "plugins/security/$resource" "$out/.security-plugin/$resource"
  done
  cp plugins/security/LICENSE.md plugins/security/ruff.toml "$out/.security-plugin/"
  printf 'antstanley/skills\n' > "$out/.security-plugin/.managed-by-skills"
  find "$out/.security-plugin" -type d -name __pycache__ -prune -exec rm -rf {} +
  uv run python scripts/relocate-security-references.py "$out"

  cat > "$out/README.md" <<'EOF'
# skills/ — generated flat tree

**Do not edit anything in this directory.** It is generated from `plugins/` by
`scripts/sync-skills.sh`. The canonical source of every skill is its plugin under
`plugins/<plugin>/skills/<name>/`; this directory is a flat, vendor-neutral copy
of all skills in the layout the [Agent Skills standard](https://github.com/agentskills/agentskills)
expects, for harnesses or people who want them all in one place. The hidden `.security-plugin/` directory holds the shared security helpers and
references copied by the installer. Internal
`evals/` directories are omitted — they are test artifacts, not part of the skill.

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
  # Running bundled Python helpers or Ruff may create local caches. They are
  # not distribution content and must not make a second check fail.
  if ! diff -rq -x __pycache__ -x .ruff_cache "$tmp/skills" skills >/dev/null; then
    echo "sync-skills: skills/ is out of sync with plugins/ — run scripts/sync-skills.sh" >&2
    diff -rq -x __pycache__ -x .ruff_cache "$tmp/skills" skills || true
    exit 1
  fi
  echo "skills/ is in sync with plugins/."
else
  build skills
  count="$(find skills -mindepth 2 -maxdepth 2 -name SKILL.md -type f | wc -l | tr -d ' ')"
  echo "Regenerated skills/ — $count skill(s) copied from plugins/."
fi
