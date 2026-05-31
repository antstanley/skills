#!/usr/bin/env bash
# Repo checks for the benchmark harness: format, lint, type-check, tests.
# Single source of truth shared by the pre-push hook (.githooks/pre-push) and
# CI (.github/workflows/ci.yml). Run from anywhere; it cd's to the repo root.
# Uses uv with the locked toolchain.
set -euo pipefail

# Local installs put uv under ~/.local/bin; harmless if already on PATH (CI).
export PATH="$HOME/.local/bin:$PATH"

cd "$(dirname "$0")/.."

echo "==> skills/ in sync with plugins/"
scripts/sync-skills.sh --check

echo "==> uv sync"
uv sync --frozen

echo "==> ruff format --check"
uv run ruff format --check

echo "==> ruff check"
uv run ruff check

echo "==> pyright"
uv run pyright

echo "==> pytest"
uv run pytest -q

echo "All checks passed."
