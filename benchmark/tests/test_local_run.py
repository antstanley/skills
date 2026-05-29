"""Tests for the ``local`` RunBackend (temp working dir + fixture solver).

These drive ``LocalRunBackend.run`` on the bundled ``local-fixture`` instance
with the ``fixture`` solver and assert:

- the emitted ``candidatePatch`` is exactly the instance ``goldPatch``,
  deterministically (two runs agree), with no Docker/LLM/network;
- the returned ``ArtifactBundle`` is schema-valid and carries a populated
  ``Telemetry`` record (real ``wallClockSeconds``; tokens/cost/turns zero);
- the integrity rule on the RUN side — the run working directory is checked out
  from ``base/`` ONLY (no hidden tests), and its temp base is DISTINCT from the
  scoring backend's temp base;
- a non-fixture solver is out of scope and raises ``NotImplementedError``.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from benchmark.harness.backends import (
    FIXTURE_SOLVER,
    RUN_TEMP_BASE,
    LocalRunBackend,
    RunBackend,
)
from benchmark.harness.backends.local import RUN_DIR_PREFIX
from benchmark.harness.domain import ArtifactBundle, Telemetry
from benchmark.harness.scoring import SCORING_TEMP_BASE
from benchmark.harness.scoring.local import REPO_BASE_SUBDIR, REPO_HIDDEN_SUBDIR
from benchmark.suites.local_fixture import FAIL_TO_PASS, PASS_TO_PASS, load_instance


def test_backend_satisfies_run_protocol() -> None:
    assert isinstance(LocalRunBackend(), RunBackend)


def test_fixture_solver_emits_gold_patch_and_bundle() -> None:
    instance = load_instance()

    bundle, patch = LocalRunBackend().run(instance, FIXTURE_SOLVER)

    # The fixture solver emits the real gold patch verbatim.
    assert patch == instance.goldPatch
    assert patch is not None

    # A schema-valid bundle with a populated Telemetry record.
    assert isinstance(bundle, ArtifactBundle)
    assert isinstance(bundle.telemetry, Telemetry)
    assert bundle.telemetry.wallClockSeconds >= 0.0
    assert bundle.telemetry.inputTokens == 0
    assert bundle.telemetry.outputTokens == 0
    assert bundle.telemetry.costUsd == 0.0
    assert bundle.telemetry.agentTurns == 0
    # Round-trips through the schema (validates on construct + load).
    assert ArtifactBundle.from_dict(bundle.to_dict()) == bundle


def test_fixture_solver_is_deterministic() -> None:
    instance = load_instance()
    _b1, p1 = LocalRunBackend().run(instance, FIXTURE_SOLVER)
    _b2, p2 = LocalRunBackend().run(instance, FIXTURE_SOLVER)
    assert p1 == p2 == instance.goldPatch


def test_run_output_carries_no_hidden_tests() -> None:
    """The run side (bundle + patch) must not leak the hidden suite."""
    instance = load_instance()

    bundle, patch = LocalRunBackend().run(instance, FIXTURE_SOLVER)

    run_blob = repr(bundle.to_dict()) + repr(patch)
    for selector in (*FAIL_TO_PASS, *PASS_TO_PASS):
        assert selector not in run_blob
    # The hidden test files themselves are named test_add.py / test_identity.py.
    assert "test_add" not in run_blob
    assert "test_identity" not in run_blob


def test_run_dir_is_distinct_from_scoring_dir() -> None:
    """Integrity rule: the run temp base is a different tree from scoring's."""
    assert RUN_TEMP_BASE != SCORING_TEMP_BASE
    assert RUN_TEMP_BASE not in SCORING_TEMP_BASE.parents
    assert SCORING_TEMP_BASE not in RUN_TEMP_BASE.parents


def test_run_dir_checks_out_base_only_never_hidden(tmp_path: Path) -> None:
    """The working directory is checked out from base/ ONLY (no hidden/).

    Drives the backend's checkout against a controlled repo source so the exact
    contents of the run working directory can be inspected, asserting the hidden
    suite never lands there.
    """
    repo = tmp_path / "repo"
    base = repo / REPO_BASE_SUBDIR
    hidden = repo / REPO_HIDDEN_SUBDIR
    base.mkdir(parents=True)
    hidden.mkdir(parents=True)
    (base / "mod.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    (hidden / "test_secret.py").write_text(
        "def test_secret():\n    assert True\n", encoding="utf-8"
    )

    workdir = tmp_path / "workdir"
    # Exercise the checkout in a known location (run() deletes its own temp dir).
    instance = SimpleNamespace(repo=str(repo), baseCommit="0000000")
    LocalRunBackend._checkout_base(instance, workdir)

    names = {p.name for p in workdir.rglob("*") if p.is_file()}
    assert "mod.py" in names
    assert "test_secret.py" not in names
    blob = "\n".join(
        p.read_text(encoding="utf-8") for p in workdir.rglob("*") if p.is_file()
    )
    assert "test_secret" not in blob


def test_run_temp_dir_is_cleaned_up() -> None:
    """No run working directory leaks under RUN_TEMP_BASE after a run."""
    instance = load_instance()
    LocalRunBackend().run(instance, FIXTURE_SOLVER)
    if RUN_TEMP_BASE.exists():
        leftover = [
            p for p in RUN_TEMP_BASE.iterdir() if p.name.startswith(RUN_DIR_PREFIX)
        ]
        assert leftover == []


def test_non_fixture_solver_is_out_of_scope() -> None:
    instance = load_instance()
    backend = LocalRunBackend()
    for solver in ("agent", object()):
        try:
            backend.run(instance, solver)
        except NotImplementedError:
            continue
        raise AssertionError(f"expected NotImplementedError for solver {solver!r}")
