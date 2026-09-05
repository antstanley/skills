#!/usr/bin/env python3
"""Generate Claude and Codex publishing metadata from plugins/catalog.json."""

import argparse
import json
import tarfile
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SEMVER = (
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
TEXT = {"type": "string", "minLength": 1, "pattern": r"\S"}


def object_schema(properties: dict, required: list[str] | None = None) -> dict:
    """Declare a closed metadata object, requiring all fields unless specified."""
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties) if required is None else required,
        "additionalProperties": False,
    }


AUTHOR = object_schema({"name": TEXT, "email": TEXT, "url": TEXT}, ["name"])
MANIFEST = object_schema(
    {
        "name": {"type": "string", "pattern": r"^[a-z0-9]+(?:-[a-z0-9]+)*$"},
        "version": {"type": "string", "pattern": SEMVER},
        "description": TEXT,
        "author": AUTHOR,
        "repository": {"type": "string", "pattern": r"^https://"},
        "homepage": {"type": "string", "pattern": r"^https://"},
        "license": TEXT,
        "keywords": {"type": "array", "items": TEXT, "uniqueItems": True},
    },
    ["name", "version", "description", "author", "repository", "keywords"],
)
CATALOG_SCHEMA = object_schema(
    {
        "name": {"type": "string", "pattern": r"^[A-Za-z0-9_-]+$"},
        "displayName": TEXT,
        "owner": AUTHOR,
        "description": TEXT,
        "plugins": {
            "type": "array",
            "minItems": 1,
            "items": object_schema(
                {
                    "manifest": MANIFEST,
                    "displayName": TEXT,
                    "shortDescription": TEXT,
                    "defaultPrompt": {**TEXT, "maxLength": 128},
                    "claudeCategory": TEXT,
                }
            ),
        },
    }
)
ARCHIVE_ROOTS = {
    ".claude-plugin",
    ".codex-plugin",
    "skills",
    "scripts",
    "references",
    "schemas",
    "examples",
    "assets",
    "README.md",
    "LICENSE.md",
    "LICENSE",
}
ARCHIVE_EXCLUDES = {"evals", "__pycache__", ".ruff_cache", ".DS_Store"}


def load_catalog(root: Path) -> dict:
    """Validate metadata and the exact set of publishable plugin directories."""
    catalog = json.loads((root / "plugins/catalog.json").read_text())
    Draft202012Validator(CATALOG_SCHEMA).validate(catalog)
    names = [entry["manifest"]["name"] for entry in catalog["plugins"]]
    if len(set(names)) != len(names):
        raise ValueError("Duplicate plugin name in catalog")
    installed = {p.parent.name for p in (root / "plugins").glob("*/skills")}
    if set(names) != installed:
        raise ValueError("Catalog must list every plugin with a skills directory")
    for name in names:
        plugin = root / "plugins" / name
        if plugin.is_symlink() or not plugin.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Plugin escapes repository: {name}")
        if not list((plugin / "skills").glob("*/SKILL.md")):
            raise ValueError(f"Plugin has no skills: {name}")
    return catalog


def generated_files(catalog: dict) -> dict[str, str]:
    """Produce both manifests and catalogs without writing to disk."""
    files = {}
    claude_entries, codex_entries = [], []
    for entry in catalog["plugins"]:
        manifest = entry["manifest"]
        name = manifest["name"]
        path = f"./plugins/{name}"
        files[f"plugins/{name}/.claude-plugin/plugin.json"] = manifest
        files[f"plugins/{name}/.codex-plugin/plugin.json"] = {
            **manifest,
            "skills": "./skills/",
            "interface": {
                "displayName": entry["displayName"],
                "shortDescription": entry["shortDescription"],
                "longDescription": manifest["description"],
                "developerName": manifest["author"]["name"],
                "category": "Productivity",
                "capabilities": ["Read", "Write"],
                "defaultPrompt": [entry["defaultPrompt"]],
            },
        }
        claude_entries.append(
            {
                "name": name,
                "source": path,
                "description": manifest["description"],
                "category": entry["claudeCategory"],
                "homepage": manifest.get("homepage", manifest["repository"]),
            }
        )
        codex_entries.append(
            {
                "name": name,
                "source": {"source": "local", "path": path},
                "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                "category": "Productivity",
            }
        )
    files[".claude-plugin/marketplace.json"] = {
        "name": catalog["name"],
        "metadata": {"description": catalog["description"]},
        "owner": catalog["owner"],
        "plugins": claude_entries,
    }
    files[".agents/plugins/marketplace.json"] = {
        "name": catalog["name"],
        "interface": {"displayName": catalog["displayName"]},
        "plugins": codex_entries,
    }
    return {path: json.dumps(data, indent=2) + "\n" for path, data in files.items()}


def sync(root: Path, check: bool = False) -> None:
    """Regenerate publishing files, or fail without writing if any have drifted."""
    expected = generated_files(load_catalog(root))
    drift = []
    for name, content in expected.items():
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Generated path escapes repository: {name}")
        if not path.exists() or path.read_text() != content:
            drift.append(name)
    if check and drift:
        raise ValueError("Publishing metadata is out of sync: " + ", ".join(drift))
    if not check:
        for name in drift:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(expected[name])


def build_archives(root: Path, destination: Path) -> list[Path]:
    """Package each plugin with both manifests and only distributable resources."""
    sync(root, check=True)
    destination.mkdir(parents=True, exist_ok=True)
    archives = []
    for entry in load_catalog(root)["plugins"]:
        manifest = entry["manifest"]
        name = manifest["name"]
        plugin = root / "plugins" / name
        output = destination / f"{name}-{manifest['version']}.tar.gz"
        with tarfile.open(output, "w:gz") as archive:
            for path in sorted(plugin.rglob("*")):
                relative = path.relative_to(plugin)
                if relative.parts[0] not in ARCHIVE_ROOTS:
                    continue
                if ARCHIVE_EXCLUDES.intersection(relative.parts):
                    continue
                if path.is_symlink():
                    raise ValueError(f"Plugin archive cannot contain symlinks: {path}")
                if path.is_file() and path.suffix not in {".pyc", ".pyo"}:
                    archive.add(path, arcname=f"{name}/{relative}", recursive=False)
        archives.append(output)
    return archives


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--archive-dir", type=Path)
    args = parser.parse_args()
    sync(ROOT, check=args.check)
    if args.archive_dir:
        for path in build_archives(ROOT, args.archive_dir):
            print(path)
    print("Claude and Codex publishing metadata is in sync.")


if __name__ == "__main__":
    main()
