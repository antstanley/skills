"""Tests for the A1 — Full pipeline arm (creator -> planner -> builder).

A1 is the system under test (``docs/benchmark/specs/02-arms.md`` §A1). The
``container`` RunBackend dispatches an ``Arm`` with a non-empty ``pluginsEnabled``
to a NEW A1 path: it read-only mounts the host ``spec-*`` plugins, loads them with
``--plugin-dir``, and drives ONE orchestrating ``claude -p`` through the whole
pipeline to an integration tip. The candidate patch is the CODE diff of that tip
against the base commit, EXCLUDING the workflow artifacts (``docs/``), which are
captured into the ``ArtifactBundle`` instead.

These tests assert:

- the A1 arm record is the configured full-pipeline arm (plugins, gates on, no
  spec, structured parallel execution);
- the A1 path is selected for an A1-style plugin arm (and NOT for A0/agent);
- ARTIFACT/PATCH SEPARATION — the docs/ workflow artifacts are excluded from the
  code diff and classified into the spec/plan/certificate buckets — proven on a
  SYNTHETIC integration tip with NO API and NO Docker (a real git repo + the same
  exclude pathspec the backend uses, plus the pure ``_classify_artifacts``);
- [LIVE, gated on Docker+creds+plugins] ONE bounded A1 run on the seed instance
  through the driver, scored via ``ContainerScoringBackend``, yielding an
  apply-able CODE patch and a bundle with spec+plan+certificate artifacts. The
  live evidence is SAVED so a reviewer need not re-run the expensive A1.

The LIVE test spends real (user-authorized) API budget on a RECURSIVE workflow:
ONE run, model ``sonnet``, HARD ``--max-budget-usd`` cap + wall-clock timeout. It
is OPT-IN (``BENCHMARK_RUN_A1_LIVE=1``) so it never fires on a routine
``check.sh`` / CI pass, and ``skipif``s cleanly when the opt-in, Docker, host
creds, OR the spec-* plugins are absent. Its outputs are SAVED so the gates
inspect the evidence instead of re-running the expensive A1.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

from benchmark.harness.arms.a1 import (
    A1,
    A1_ARTIFACT_DIR,
    A1_MAX_BUDGET_USD,
    A1_PLUGIN_DIR_NAMES,
    HOST_PLUGIN_MARKETPLACE_DIR,
    a1_prompt,
)
from benchmark.harness.backends import (
    AGENT_SOLVER,
    ContainerRunBackend,
    RunBackend,
)
from benchmark.harness.backends import container as container_mod
from benchmark.harness.backends.container import (
    _ARTIFACT_EXCLUDE_PATHSPEC,
    HOST_CREDENTIALS_PATH,
)
from benchmark.harness.domain import Arm, ArtifactBundle, Campaign, Telemetry
from benchmark.harness.driver import run_campaign
from benchmark.harness.scoring import ContainerScoringBackend
from benchmark.suites import greenfield_images as images
from benchmark.suites.greenfield import TEXT_TOOLKIT_SLUG, load_instance

# --- gating ----------------------------------------------------------------

_DOCKER_UP = images.docker_available()
_CREDS_PRESENT = HOST_CREDENTIALS_PATH.is_file()
_PLUGINS_PRESENT = all(
    (HOST_PLUGIN_MARKETPLACE_DIR / name / ".claude-plugin" / "plugin.json").is_file()
    for name in A1_PLUGIN_DIR_NAMES
)

#: Opt-in env var gating the LIVE A1 run. A1 is a RECURSIVE workflow with a HARD
#: ``$20`` cap per run; unlike the cheap A0 live test it must NOT fire on every
#: ``check.sh`` / CI pass. The reviewer/validator inspect the SAVED evidence under
#: :data:`LIVE_EVIDENCE_DIR` instead of paying to re-run it; set this var to ``1``
#: to actually execute the bounded run.
_A1_LIVE_OPT_IN_ENV = "BENCHMARK_RUN_A1_LIVE"
_A1_LIVE_OPT_IN = os.environ.get(_A1_LIVE_OPT_IN_ENV) == "1"

_skip_no_live = pytest.mark.skipif(
    not (_A1_LIVE_OPT_IN and _DOCKER_UP and _CREDS_PRESENT and _PLUGINS_PRESENT),
    reason=(
        f"LIVE A1 run needs {_A1_LIVE_OPT_IN_ENV}=1 (the recursive run spends real "
        "budget) + Docker + host claude credentials + spec-* plugins"
    ),
)

#: Where the live test SAVES its evidence so a reviewer can inspect the run
#: WITHOUT re-running the expensive A1 (the patch, score report, captured
#: artifacts, telemetry, cost, wall-clock, transcript).
LIVE_EVIDENCE_DIR = Path(__file__).resolve().parent / "_a1_live_evidence"


# --- non-gated: the A1 arm record ------------------------------------------


def test_a1_arm_is_the_full_pipeline_arm() -> None:
    """A1: creator+planner+builder, gates ON, no spec given, structured parallel."""
    assert A1.slug == "A1"
    assert A1.pluginsEnabled == ["spec-creator", "spec-planner", "spec-builder"]
    assert A1.gatesEnabled is True
    assert A1.specProvided is False
    assert A1.executionMode == "parallel-structured"


def test_a1_arm_round_trips_through_the_schema() -> None:
    assert Arm.from_dict(A1.to_dict()) == A1


def test_a1_prompt_carries_the_problem_statement_and_the_three_stages() -> None:
    instance = load_instance(TEXT_TOOLKIT_SLUG)
    prompt = a1_prompt(instance.problemStatement)
    assert instance.problemStatement in prompt
    # Names the three pipeline skills the orchestrator must drive in order.
    assert "spec-creator" in prompt
    assert "spec-planner" in prompt
    assert "spec-builder" in prompt


# --- non-gated: arm dispatch (A1 path vs A0/agent path) ---------------------


def test_a1_path_is_selected_for_a_plugin_arm() -> None:
    # A1 is a workflow arm; dispatch routes it to the parameterized workflow path.
    assert ContainerRunBackend._selects_workflow(A1) is True


def test_a1_path_not_selected_for_agent_or_a0() -> None:
    from benchmark.harness.arms.a0 import A0

    assert ContainerRunBackend._selects_workflow(AGENT_SOLVER) is False
    assert ContainerRunBackend._selects_workflow(A0) is False
    # A0 still selects the plain agent path.
    assert ContainerRunBackend._selects_agent(A0) is True


def test_backend_still_satisfies_run_protocol() -> None:
    assert isinstance(ContainerRunBackend(), RunBackend)


# --- non-gated: artifact/patch separation (synthetic tip, no API/Docker) ----


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )


def _build_synthetic_integration_tip(repo: Path) -> None:
    """A synthetic integration tip: a base commit + CODE change + docs/ artifacts.

    Mirrors what the A1 path's container holds after the workflow: the package
    code is implemented (the scored change) AND the workflow wrote its spec/plan/
    certificate files under ``docs/``. No API, no Docker — just a real git repo.
    """
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    # Base commit: a stub module.
    (repo / "pkg").mkdir()
    (repo / "pkg" / "core.py").write_text("def f():\n    raise NotImplementedError\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    # The CODE change (what should be scored).
    (repo / "pkg" / "core.py").write_text("def f():\n    return 42\n")
    # The workflow artifacts under docs/ (what must be EXCLUDED from the diff).
    specs = repo / A1_ARTIFACT_DIR / "specs"
    plans = repo / A1_ARTIFACT_DIR / "plans" / "2026-05-27-feature"
    certs = plans / "certificates"
    specs.mkdir(parents=True)
    certs.mkdir(parents=True)
    (specs / "00-overview.md").write_text("# spec\n")
    (plans / "plan.md").write_text("# plan\n")
    (plans / "01-task.md").write_text("# task 1\n")
    (certs / "01-task.md").write_text("# certificate 1\n")
    (repo / A1_ARTIFACT_DIR / "README.md").write_text("# docs index\n")


def _diff_excluding_artifacts(repo: Path) -> str:
    """The same CODE-only diff the backend extracts: ``docs/`` excluded."""
    _git(repo, "add", "-A")
    result = _git(
        repo,
        "diff",
        "--cached",
        "--",
        ".",
        _ARTIFACT_EXCLUDE_PATHSPEC,
    )
    return result.stdout


def test_workflow_artifacts_are_excluded_from_the_code_diff(tmp_path: Path) -> None:
    """The candidate (code) diff carries the CODE change but NO docs/ artifacts."""
    repo = tmp_path / "tip"
    repo.mkdir()
    _build_synthetic_integration_tip(repo)

    code_diff = _diff_excluding_artifacts(repo)

    # The code change is present...
    assert "pkg/core.py" in code_diff
    assert "return 42" in code_diff
    # ...and NONE of the workflow artifacts leaked into the scored diff.
    assert f"{A1_ARTIFACT_DIR}/" not in code_diff
    assert "spec" not in code_diff.lower() or "pkg/core.py" in code_diff
    assert "plan.md" not in code_diff
    assert "certificate" not in code_diff
    assert "00-overview.md" not in code_diff


def test_classify_artifacts_sorts_into_spec_plan_certificate_buckets() -> None:
    """``_classify_artifacts`` buckets a docs/ walk by path: spec/plan/cert."""
    fs = container_mod._ARTIFACT_FIELD_SEP
    rs = container_mod._ARTIFACT_RECORD_SEP
    records = [
        f"docs/specs/00-overview.md{fs}# spec body",
        f"docs/plans/2026-05-27-x/plan.md{fs}# plan body",
        f"docs/plans/2026-05-27-x/01-task.md{fs}# task body",
        f"docs/plans/2026-05-27-x/certificates/01-task.md{fs}# cert body",
        f"docs/README.md{fs}# index",
    ]
    raw = rs.join(records) + rs

    specs, plans, certs = ContainerRunBackend._classify_artifacts(raw)

    assert any("docs/specs/00-overview.md" in s and "# spec body" in s for s in specs)
    assert any("plan.md" in p for p in plans)
    assert any("01-task.md" in p for p in plans)
    # The README under docs/ is kept (with the plan bucket), never dropped.
    assert any("docs/README.md" in p for p in plans)
    # The certificate goes to the certificate bucket, NOT the plan bucket.
    assert any("certificates/01-task.md" in c for c in certs)
    assert not any("certificates/" in p for p in plans)


def test_classify_artifacts_handles_empty_walk() -> None:
    """No docs/ artifacts -> three empty lists (an honest partial outcome)."""
    specs, plans, certs = ContainerRunBackend._classify_artifacts("")
    assert specs == []
    assert plans == []
    assert certs == []


# --- LIVE: one bounded A1 run through the driver (Docker+creds+plugins) -----


def _apply_check(patch: str, run_image_tag: str) -> subprocess.CompletedProcess[str]:
    """``git apply --check`` the CODE patch against a FRESH base checkout."""
    command = (
        f"set -e; cd {images.IMAGE_WORKDIR}; "
        "git init -q; git add -A; "
        "git -c user.email=t@t -c user.name=t commit -q -m base; "
        "git apply --check -"
    )
    return subprocess.run(
        ["docker", "run", "--rm", "-i", run_image_tag, "sh", "-c", command],
        input=patch,
        capture_output=True,
        text=True,
        timeout=120,
    )


@_skip_no_live
def test_live_a1_pipeline_through_driver_yields_patch_and_artifacts() -> None:
    """LIVE: ONE bounded A1 run on the seed instance, end to end through the driver.

    Spends real budget on the recursive workflow (capped at ``A1_MAX_BUDGET_USD``
    + a wall-clock timeout). Runs through ``run_campaign`` with the container
    RunBackend + ``ContainerScoringBackend`` (the same path A1 runs in production),
    then asserts the candidate CODE patch applies cleanly against a fresh base and
    the bundle carries spec+plan+certificate artifacts + telemetry. ALL live
    evidence is saved under :data:`LIVE_EVIDENCE_DIR` for offline review.
    """
    instance = load_instance(TEXT_TOOLKIT_SLUG)
    campaign = Campaign(
        id="camp_00000000-0000-7000-8000-000000000001",
        createdAt="2026-05-27T00:00:00+00:00",
        model="sonnet",
        arms=[A1.slug],
        suites=[instance.suite],
        trialsPerInstance=1,
        backend="container",
        solver="agent",
    )
    run_backend = ContainerRunBackend()
    scoring_backend = ContainerScoringBackend()

    started = time.monotonic()
    campaign_run = run_campaign(
        campaign,
        arms=[A1],
        instances=[instance],
        run_backend=run_backend,
        scoring_backend=scoring_backend,
        pool_size=1,
    )
    wall_clock = time.monotonic() - started

    assert len(campaign_run.results) == 1
    result = campaign_run.results[0]

    # Save evidence FIRST (even on a partial/failed outcome) for offline review.
    LIVE_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    patch = result.trial.candidatePatch
    bundle = result.bundle
    report = result.report
    (LIVE_EVIDENCE_DIR / "candidate_patch.diff").write_text(patch or "")
    if bundle is not None:
        (LIVE_EVIDENCE_DIR / "artifact_bundle.json").write_text(
            json.dumps(bundle.to_dict(), indent=2, sort_keys=True)
        )
        if bundle.transcript is not None:
            (LIVE_EVIDENCE_DIR / "transcript.json").write_text(bundle.transcript)
    if report is not None:
        (LIVE_EVIDENCE_DIR / "score_report.json").write_text(
            json.dumps(report.to_dict(), indent=2, sort_keys=True)
        )
    (LIVE_EVIDENCE_DIR / "run_summary.json").write_text(
        json.dumps(
            {
                "trial_status": result.trial.status,
                "fault": result.fault,
                "wall_clock_seconds": wall_clock,
                "cost_usd": (bundle.telemetry.costUsd if bundle is not None else None),
                "resolved": report.resolved if report is not None else None,
                "regressed": report.regressed if report is not None else None,
                "spec_artifact_count": (
                    len(bundle.specArtifacts)
                    if bundle is not None and bundle.specArtifacts is not None
                    else 0
                ),
                "plan_artifact_count": (
                    len(bundle.planArtifacts)
                    if bundle is not None and bundle.planArtifacts is not None
                    else 0
                ),
                "certificate_artifact_count": (
                    len(bundle.certificateArtifacts)
                    if bundle is not None and bundle.certificateArtifacts is not None
                    else 0
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )

    # A scored (not infra-failed) outcome with a genuine bundle.
    assert not result.is_failed, f"A1 run hit an infra fault: {result.fault}"
    assert isinstance(bundle, ArtifactBundle)
    assert isinstance(bundle.telemetry, Telemetry)
    assert bundle.telemetry.costUsd <= A1_MAX_BUDGET_USD

    # A genuine, non-empty CODE patch that applies against a fresh base checkout.
    assert isinstance(patch, str) and patch.strip() != ""
    assert f"{A1_ARTIFACT_DIR}/" not in patch  # workflow artifacts excluded
    run_tag = images.build_run_image(images.get_spec(TEXT_TOOLKIT_SLUG))
    check = _apply_check(patch, run_tag)
    assert check.returncode == 0, (
        f"A1 code patch did not apply cleanly:\n{check.stderr}"
    )

    # The workflow artifacts were captured into the bundle.
    assert bundle.specArtifacts and len(bundle.specArtifacts) >= 1
    assert bundle.planArtifacts and len(bundle.planArtifacts) >= 1
    assert bundle.certificateArtifacts and len(bundle.certificateArtifacts) >= 1

    # Scored through the oracle.
    assert report is not None
