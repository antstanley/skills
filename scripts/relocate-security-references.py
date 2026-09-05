"""Rewrite shared security references for the generated flat skill distribution."""

import os
import sys
from pathlib import Path


def relocate(output: Path) -> None:
    source = Path(__file__).resolve().parents[1] / "plugins/security/skills"
    for skill in source.iterdir():
        if not (skill / "SKILL.md").is_file():
            continue
        for original in skill.rglob("*.md"):
            if "evals" in original.parts:
                continue
            target = output / skill.name / original.relative_to(skill)
            text = target.read_text()
            for resource in ("references", "scripts", "schemas"):
                old = os.path.relpath(source.parent / resource, original.parent)
                new = os.path.relpath(
                    output / ".security-plugin" / resource, target.parent
                )
                text = text.replace(old + "/", new + "/")
            target.write_text(text)


if __name__ == "__main__":
    relocate(Path(sys.argv[1]))
