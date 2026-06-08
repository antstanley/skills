"""Doc-hygiene guards for the spec-* plugins.

These tests are the enforceable half of three review recommendations:

* installed/published descriptions must not drift back to the pre-``.specs/``
  paths (``docs/specs`` / ``docs/plans``) or the old ``per-app`` vocabulary;
* the semi-formal "method" is deliberately vendored into two copies, so their
  shared core (the ``<!-- shared:... -->`` blocks) must stay byte-identical;
* every ``evals/evals.json`` fixture must stay well-formed -- nothing executes
  them, so a malformed or stale fixture would otherwise pass silently.

Run via ``scripts/check.sh`` (the ``pytest`` step) -- the same gate CI and the
pre-push hook use.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Tokens that must never reappear in a skill description or eval fixture: the
# spec-* plugins moved their artefacts to .specs/ and renamed per-app layers
# to per-package.
STALE_TOKENS = ("docs/specs", "docs/plans", "per-app")

# The two vendored copies of the semi-formal method; their shared blocks
# (wrapped in <!-- shared:NAME start/end -->) must be byte-identical.
METHOD_COPIES = (
    "plugins/spec-builder/skills/semi-formal-review/references/method.md",
    "plugins/spec-planner/skills/done-certificates/references/semiformal-method.md",
)
SHARED_BLOCKS = ("function-resolution", "execution-trace", "regression-check")

# A third, hand-written description surface that is not generated from the
# plugin frontmatter, so it can drift independently.
MARKETPLACE = ".claude-plugin/marketplace.json"


def _skill_files() -> list[Path]:
    return sorted(ROOT.glob("plugins/*/skills/*/SKILL.md"))


def _eval_files() -> list[Path]:
    return sorted(ROOT.glob("plugins/*/skills/*/evals/evals.json"))


def _description(skill_md: Path) -> str:
    """Return the single-line frontmatter ``description:`` value."""
    for line in skill_md.read_text(encoding="utf-8").splitlines():
        if line.startswith("description:"):
            return line.removeprefix("description:").strip()
    return ""


def _shared_block(text: str, name: str) -> str | None:
    start = f"<!-- shared:{name} start -->"
    end = f"<!-- shared:{name} end -->"
    match = re.search(re.escape(start) + r"(.*?)" + re.escape(end), text, re.DOTALL)
    return match.group(1) if match else None


def test_skill_files_exist() -> None:
    """Sanity: the glob finds the three spec-* plugins' skills."""
    names = {p.parent.parent.parent.name for p in _skill_files()}
    assert {"spec-creator", "spec-planner", "spec-builder"} <= names


def test_descriptions_have_no_stale_paths() -> None:
    """No SKILL description names a pre-migration path or the old per-app term."""
    for skill_md in _skill_files():
        description = _description(skill_md).lower()
        for token in STALE_TOKENS:
            assert token not in description, f"{skill_md}: stale token {token!r}"


def test_eval_fixtures_wellformed() -> None:
    """Every evals.json parses and carries the expected shape."""
    for eval_file in _eval_files():
        data = json.loads(eval_file.read_text(encoding="utf-8"))
        assert isinstance(data.get("skill_name"), str), eval_file
        cases = data.get("evals")
        assert isinstance(cases, list) and cases, eval_file
        for case in cases:
            for field in ("id", "name", "prompt", "expected_output"):
                assert field in case, f"{eval_file}: case missing {field!r}"


def test_eval_fixtures_have_no_stale_paths() -> None:
    """Eval fixtures use the migrated .specs/ paths and per-package vocabulary."""
    for eval_file in _eval_files():
        blob = eval_file.read_text(encoding="utf-8").lower()
        for token in STALE_TOKENS:
            assert token not in blob, f"{eval_file}: stale token {token!r}"


def test_marketplace_descriptions_have_no_stale_paths() -> None:
    """The hand-written marketplace descriptions stay free of stale tokens."""
    data = json.loads((ROOT / MARKETPLACE).read_text(encoding="utf-8"))
    for plugin in data.get("plugins", []):
        description = plugin.get("description", "").lower()
        for token in STALE_TOKENS:
            assert token not in description, f"{plugin.get('name')}: {token!r}"


def test_shared_method_blocks_are_byte_identical() -> None:
    """The vendored semi-formal method copies share a byte-identical core."""
    texts = [
        (path, (ROOT / path).read_text(encoding="utf-8")) for path in METHOD_COPIES
    ]
    for name in SHARED_BLOCKS:
        blocks = [(path, _shared_block(text, name)) for path, text in texts]
        for path, block in blocks:
            assert block is not None, f"{path}: missing shared block {name!r}"
        reference = blocks[0][1]
        for path, block in blocks[1:]:
            assert block == reference, f"{path}: shared block {name!r} drifted"
