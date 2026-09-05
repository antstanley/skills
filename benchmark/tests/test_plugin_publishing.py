"""Exercise dual manifests, catalog drift, and standalone plugin archives."""

import importlib.util
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest
from jsonschema import ValidationError

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "sync_plugins", ROOT / "scripts/sync-plugins.py"
)
assert SPEC is not None and SPEC.loader is not None
publishing = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publishing)


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    shutil.copytree(
        ROOT / "plugins",
        root / "plugins",
        ignore=shutil.ignore_patterns(
            "__pycache__",
            ".ruff_cache",
            "evals",
        ),
    )
    publishing.sync(root)
    return root


def test_catalogs_and_manifests_share_identity() -> None:
    publishing.sync(ROOT, check=True)
    claude = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
    codex = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text())
    assert [p["name"] for p in claude["plugins"]] == [
        p["name"] for p in codex["plugins"]
    ]
    for entry in codex["plugins"]:
        root = ROOT / entry["source"]["path"]
        a = json.loads((root / ".claude-plugin/plugin.json").read_text())
        b = json.loads((root / ".codex-plugin/plugin.json").read_text())
        assert all(b[key] == value for key, value in a.items())
        assert (root / b["skills"]).is_dir()
        assert b["name"] == root.name == entry["name"]
        assert entry["policy"]["installation"] == "AVAILABLE"


def test_check_rejects_drift_without_writing(repository: Path) -> None:
    path = repository / "plugins/spec-creator/.codex-plugin/plugin.json"
    path.write_text("{}\n")
    with pytest.raises(ValueError, match="out of sync"):
        publishing.sync(repository, check=True)
    assert path.read_text() == "{}\n"
    publishing.sync(repository)
    publishing.sync(repository, check=True)


@pytest.mark.parametrize(
    "change", ["duplicate", "semver", "escape", "unknown", "missing"]
)
def test_bad_catalog_is_rejected(repository: Path, change: str) -> None:
    path = repository / "plugins/catalog.json"
    catalog = json.loads(path.read_text())
    manifest = catalog["plugins"][0]["manifest"]
    if change == "duplicate":
        catalog["plugins"].append(catalog["plugins"][0])
    elif change == "semver":
        manifest["version"] = "01.2.3"
    elif change == "escape":
        manifest["name"] = "../outside"
    elif change == "unknown":
        manifest["hooks"] = "./hooks.json"
    else:
        catalog["plugins"].pop()
    path.write_text(json.dumps(catalog))
    with pytest.raises((ValueError, ValidationError)):
        publishing.load_catalog(repository)


def test_archives_include_both_formats_and_security_helpers(
    repository: Path,
    tmp_path: Path,
) -> None:
    plugin = repository / "plugins/security"
    cache = plugin / "scripts/__pycache__"
    cache.mkdir(exist_ok=True)
    (cache / "junk.pyc").write_bytes(b"cache")
    archives = publishing.build_archives(repository, tmp_path / "archives")
    assert len(archives) == 6
    for path in archives:
        with tarfile.open(path) as archive:
            names = archive.getnames()
            root = names[0].split("/")[0]
            assert f"{root}/.claude-plugin/plugin.json" in names
            assert f"{root}/.codex-plugin/plugin.json" in names
            assert any(n.endswith("/SKILL.md") for n in names)
            assert not any("/evals/" in n or "__pycache__" in n for n in names)
            assert all(not m.issym() and not m.islnk() for m in archive.getmembers())
            if root == "security":
                assert "security/scripts/preflight.py" in names
                assert "security/references/preflight.md" in names
                assert "security/LICENSE.md" in names


def test_archive_rejects_resource_symlinks(repository: Path, tmp_path: Path) -> None:
    (repository / "plugins/security/assets/external").symlink_to("/etc/hosts")
    with pytest.raises(ValueError, match="symlinks"):
        publishing.build_archives(repository, tmp_path / "archives")


@pytest.mark.parametrize("mode", ["--copy", "--symlink"])
def test_flat_install_keeps_security_resources_runnable(
    tmp_path: Path, mode: str
) -> None:
    subprocess.run(
        ["bash", str(ROOT / "install.sh"), "codex", "--project", str(tmp_path), mode],
        check=True,
        capture_output=True,
        text=True,
    )
    installed = tmp_path / ".agents/skills"
    assert len(list(installed.glob("*/SKILL.md"))) == 24
    bundle = installed / ".security-plugin"
    assert bundle.is_symlink() == (mode == "--symlink")
    result = subprocess.run(
        [sys.executable, str(bundle / "scripts/preflight.py"), "--help"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "--profile" in result.stdout
    entry = installed / "security-scan/SKILL.md"
    assert "../.security-plugin/references/runtime.md" in entry.read_text()
    assert (entry.parent / "../.security-plugin/references/runtime.md").is_file()


def test_flat_install_preserves_unmanaged_resources(tmp_path: Path) -> None:
    bundle = tmp_path / ".agents/skills/.security-plugin"
    bundle.mkdir(parents=True)
    marker = bundle / "user-data.txt"
    marker.write_text("keep")
    result = subprocess.run(
        ["bash", str(ROOT / "install.sh"), "codex", "--project", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert marker.read_text() == "keep"
