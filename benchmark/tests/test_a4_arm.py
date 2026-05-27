"""Tests for the A4 arm — parallel but unstructured (naive N-way split).

A4 (``02-arms.md`` §A4) is a budget-matched naive N-way parallel split with NO
``spec-*`` plugins, NO dependency-ordered DAG, NO per-task definition of done, and
NO gates. It is the naive-parallelism control for ``A1 − A4`` (structure vs
equal-budget concurrency). The container backend routes the A4 slug to a dedicated
``_run_a4`` path: N plain agents run CONCURRENTLY on the same problem with a
coordination-free framing (the pinned policy), and their per-agent diffs are
combined by a NAIVE merge that RECORDS — rather than resolves — conflicts.

These tests assert (non-gated, no API/Docker):

- the A4 arm record is configured correctly (no plugins, gates off, no spec,
  ``parallel-unstructured``);
- ``N`` is the documented constant matched to A1's task count, and the per-agent
  budget == A1's single-run cap / N (budget-matched by construction);
- dispatch routes A4 to ``_run_a4`` (its own path), NOT the plain-A0 or workflow
  path;
- the NAIVE-merge logic on synthetic per-agent diffs — driven through a REAL local
  ``git apply`` applier (no Docker) — merges non-overlapping diffs and RECORDS a
  conflicting pair (does not crash, does not cleverly resolve);
- telemetry aggregation across N synthetic agent results SUMS tokens/cost/turns
  and takes the parallel wall clock.

The LIVE test (``BENCHMARK_RUN_A4_LIVE=1``, skipped on CI) runs ONE bounded A4 on
the seed instance through the driver + ``ContainerScoringBackend``, asserting N
agents run and produce a scored merged patch, with any conflicts recorded. Its
evidence is SAVED so the gates inspect it without re-running the expensive arm.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

from benchmark.harness.arms.a0 import A0
from benchmark.harness.arms.a1 import A1_MAX_BUDGET_USD
from benchmark.harness.arms.a4 import (
    A4,
    A4_N,
    A4_PER_AGENT_MAX_BUDGET_USD,
    A4_TOTAL_MAX_BUDGET_USD,
    a4_slice_prompt,
)
from benchmark.harness.backends import ContainerRunBackend, RunBackend
from benchmark.harness.backends.container import (
    HOST_CREDENTIALS_PATH,
    _aggregate_a4_telemetry,
    _run_naive_merge,
)
from benchmark.harness.domain import Arm, ArtifactBundle, Campaign
from benchmark.harness.driver import run_campaign
from benchmark.harness.scoring import ContainerScoringBackend
from benchmark.suites import greenfield_images as images
from benchmark.suites.greenfield import TEXT_TOOLKIT_SLUG, load_instance

# --- gating ----------------------------------------------------------------

_DOCKER_UP = images.docker_available()
_CREDS_PRESENT = HOST_CREDENTIALS_PATH.is_file()

#: Opt-in env var gating the LIVE A4 run. N recursive plain-agent runs spend real
#: (user-authorized) budget capped at ``A4_TOTAL_MAX_BUDGET_USD`` TOTAL; this must
#: NOT fire on a routine ``check.sh`` / CI pass. Reviewers inspect the SAVED
#: evidence under :data:`LIVE_EVIDENCE_DIR` instead of paying to re-run.
_A4_LIVE_OPT_IN_ENV = "BENCHMARK_RUN_A4_LIVE"
_A4_LIVE_OPT_IN = os.environ.get(_A4_LIVE_OPT_IN_ENV) == "1"

_skip_no_live = pytest.mark.skipif(
    not (_A4_LIVE_OPT_IN and _DOCKER_UP and _CREDS_PRESENT),
    reason=(
        f"LIVE A4 run needs {_A4_LIVE_OPT_IN_ENV}=1 (N parallel agent runs spend "
        "real budget) + Docker + host claude credentials"
    ),
)

#: Where the live test SAVES its evidence (merged patch, score report, aggregated
#: telemetry, total cost, transcript with per-agent results, and the merge-conflict
#: record) so a reviewer can confirm N agents ran + the naive merge WITHOUT
#: re-running the expensive arm.
LIVE_EVIDENCE_DIR = Path(__file__).resolve().parent / "_a4_live_evidence"


# --- non-gated: the A4 arm record ------------------------------------------


def test_a4_arm_is_parallel_unstructured_no_plugins_no_gates() -> None:
    """A4: no plugins, gates OFF, no spec provided, parallel-unstructured."""
    assert A4.slug == "A4"
    assert A4.pluginsEnabled == []
    assert A4.gatesEnabled is False
    assert A4.specProvided is False
    assert A4.executionMode == "parallel-unstructured"


def test_a4_arm_round_trips_through_the_schema() -> None:
    assert Arm.from_dict(A4.to_dict()) == A4


def test_a4_n_matches_a1_task_count_on_the_seed() -> None:
    """N is the documented constant matched to A1's task count on text_toolkit (4)."""
    assert A4_N == 4


def test_a4_budget_is_matched_to_a1_total_and_split_per_agent() -> None:
    """A4 TOTAL cap == A1's single-run cap; per-agent == total / N (by construction)."""
    assert A4_TOTAL_MAX_BUDGET_USD == A1_MAX_BUDGET_USD
    assert A4_PER_AGENT_MAX_BUDGET_USD == A4_TOTAL_MAX_BUDGET_USD / A4_N
    # The sum of the N per-agent caps can never exceed A1's cap.
    assert A4_PER_AGENT_MAX_BUDGET_USD * A4_N == A4_TOTAL_MAX_BUDGET_USD


def test_a4_slice_prompt_is_coordination_free_and_carries_the_problem() -> None:
    """Every agent gets the SAME problem + the no-coordination framing (no plan)."""
    instance = load_instance(TEXT_TOOLKIT_SLUG)
    prompt = a4_slice_prompt(instance.problemStatement, agent_index=2, agent_count=A4_N)
    assert instance.problemStatement in prompt
    assert "agent 2 of 4" in prompt
    assert "NO coordination" in prompt
    assert "no shared plan" in prompt.lower() or "no plan" in prompt.lower()
    # No spec / plan / gate scaffolding (that is what the workflow arms add).
    assert "spec-creator" not in prompt
    assert "spec-planner" not in prompt
    assert "definition of done" in prompt.lower()  # ...to say there is none


def test_all_agents_get_the_same_problem_statement() -> None:
    """The naive split hands every agent IDENTICAL problem bytes (no decomposition)."""
    instance = load_instance(TEXT_TOOLKIT_SLUG)
    ps = instance.problemStatement
    for i in range(1, A4_N + 1):
        assert ps in a4_slice_prompt(ps, agent_index=i, agent_count=A4_N)


# --- non-gated: arm dispatch (A4 path, not plain-A0 or workflow) -----------


def test_a4_selects_its_own_path_not_agent_not_workflow() -> None:
    assert ContainerRunBackend._selects_a4(A4) is True
    assert ContainerRunBackend._selects_workflow(A4) is False
    # A4 must NOT fall into the single-agent A0 path (the bug the A4-first
    # dispatch fixes — A4 is, like A0, a no-plugin/gates-off/no-spec Arm).
    assert ContainerRunBackend._selects_agent(A4) is False


def test_a0_does_not_select_the_a4_path() -> None:
    assert ContainerRunBackend._selects_a4(A0) is False
    assert ContainerRunBackend._selects_agent(A0) is True


def test_backend_satisfies_run_protocol() -> None:
    assert isinstance(ContainerRunBackend(), RunBackend)


def test_backend_last_merge_conflicts_starts_empty() -> None:
    """Before any A4 run, the backend exposes no merge conflicts."""
    assert ContainerRunBackend().last_merge_conflicts == []


# --- non-gated: telemetry aggregation across N synthetic agent results ------


def test_aggregate_a4_telemetry_sums_counters_and_takes_parallel_wall_clock() -> None:
    """Tokens/cost/turns SUM across the N agents; wall clock is the parallel arm's."""
    results = [
        {
            "usage": {"input_tokens": 100, "output_tokens": 10},
            "total_cost_usd": 1.0,
            "num_turns": 3,
        },
        {
            "usage": {"input_tokens": 200, "output_tokens": 20},
            "total_cost_usd": 2.5,
            "num_turns": 5,
        },
        {
            "usage": {"input_tokens": 50, "output_tokens": 5},
            "total_cost_usd": 0.5,
            "num_turns": 1,
        },
    ]
    telemetry = _aggregate_a4_telemetry(results, wall_clock_seconds=42.0)
    assert telemetry.inputTokens == 350
    assert telemetry.outputTokens == 35
    assert telemetry.costUsd == 4.0
    assert telemetry.agentTurns == 9
    # Parallel wall clock = the measured arm elapsed (NOT the sum of per-agent).
    assert telemetry.wallClockSeconds == 42.0


def test_aggregate_a4_telemetry_tolerates_a_failed_agent() -> None:
    """An agent that failed (error marker, no usage) contributes zeros, no crash."""
    results = [
        {
            "usage": {"input_tokens": 100, "output_tokens": 10},
            "total_cost_usd": 1.0,
            "num_turns": 2,
        },
        {"error": "A4 agent run failed"},  # failed agent: no usage/cost/turns
    ]
    telemetry = _aggregate_a4_telemetry(results, wall_clock_seconds=10.0)
    assert telemetry.inputTokens == 100
    assert telemetry.costUsd == 1.0
    assert telemetry.agentTurns == 2


# --- non-gated: the NAIVE-merge logic on synthetic diffs (real local git) ----


def _init_repo(repo: Path, files: dict[str, str]) -> None:
    """Init a git repo with ``files`` as the base commit."""
    repo.mkdir(parents=True, exist_ok=True)
    for rel, body in files.items():
        (repo / rel).write_text(body)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    for cmd in (
        ["git", "init", "-q"],
        ["git", "add", "-A"],
        ["git", "commit", "-q", "-m", "base"],
    ):
        subprocess.run(cmd, cwd=repo, env=env, check=True, capture_output=True)


def _diff_after_edit(repo: Path, rel: str, new_body: str) -> str:
    """Return the unified diff of editing ``rel`` to ``new_body`` (working tree)."""
    (repo / rel).write_text(new_body)
    out = subprocess.run(
        ["git", "diff"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout
    # Reset the working tree so the next synthetic diff is independent.
    subprocess.run(
        ["git", "checkout", "--", rel], cwd=repo, capture_output=True, check=True
    )
    return out


class _LocalGitMerger:
    """A real-git applier/committer/extractor over a temp repo (no Docker).

    Mirrors what the container methods do (PLAIN ``git apply --index``, commit,
    final diff vs base) but in a LOCAL temp repo, so the PURE
    :func:`_run_naive_merge` loop — the same one the live arm uses — can be
    exercised without Docker. Plain apply (NOT ``--3way``) is atomic: a conflict
    fails and leaves NO markers, matching the container's naive merge.
    """

    def __init__(self, repo: Path) -> None:
        self.repo = repo
        self.env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
        }
        self.base = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    def apply_diff(self, diff: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "apply", "--index", "--whitespace=nowarn"],
            cwd=self.repo,
            input=diff,
            capture_output=True,
            text=True,
        )

    def commit_step(self, idx: int) -> None:
        subprocess.run(
            ["git", "add", "-A"],
            cwd=self.repo,
            env=self.env,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-q", "-m", f"_a4_merge_agent_{idx}", "--allow-empty"],
            cwd=self.repo,
            env=self.env,
            check=True,
            capture_output=True,
        )

    def extract_merged(self) -> str | None:
        out = subprocess.run(
            ["git", "diff", self.base, "HEAD"],
            cwd=self.repo,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        return out if out.strip() else None


def test_naive_merge_combines_non_overlapping_diffs(tmp_path: Path) -> None:
    """Two agents editing DIFFERENT files merge cleanly into one patch, no conflict."""
    repo = tmp_path / "repo"
    _init_repo(repo, {"a.py": "x = 1\n", "b.py": "y = 1\n"})
    diff_a = _diff_after_edit(repo, "a.py", "x = 42\n")
    diff_b = _diff_after_edit(repo, "b.py", "y = 99\n")
    merger = _LocalGitMerger(repo)

    merged, conflicts = _run_naive_merge(
        [diff_a, diff_b],
        apply_diff=merger.apply_diff,
        commit_step=merger.commit_step,
        extract_merged=merger.extract_merged,
    )
    assert conflicts == []
    assert isinstance(merged, str)
    assert "x = 42" in merged and "y = 99" in merged


def test_naive_merge_records_a_conflicting_pair_without_crashing(
    tmp_path: Path,
) -> None:
    """Two agents editing the SAME line conflict: first wins, second is RECORDED."""
    repo = tmp_path / "repo"
    _init_repo(repo, {"shared.py": "value = 0\n"})
    diff_0 = _diff_after_edit(repo, "shared.py", "value = 111\n")
    diff_1 = _diff_after_edit(repo, "shared.py", "value = 222\n")
    merger = _LocalGitMerger(repo)

    merged, conflicts = _run_naive_merge(
        [diff_0, diff_1],
        apply_diff=merger.apply_diff,
        commit_step=merger.commit_step,
        extract_merged=merger.extract_merged,
    )
    # Naive: agent 0 applied; agent 1 conflicted and was RECORDED (not resolved).
    assert isinstance(merged, str)
    assert "value = 111" in merged
    assert "value = 222" not in merged  # NOT cleverly merged in
    assert len(conflicts) == 1
    assert conflicts[0]["agentIndex"] == 1
    assert isinstance(conflicts[0]["stderr"], str)


def test_naive_merge_of_all_empty_diffs_is_a_noop(tmp_path: Path) -> None:
    """All agents produced nothing -> no-op patch (None), no conflicts."""
    repo = tmp_path / "repo"
    _init_repo(repo, {"a.py": "x = 1\n"})
    merger = _LocalGitMerger(repo)
    merged, conflicts = _run_naive_merge(
        ["", "   ", ""],
        apply_diff=merger.apply_diff,
        commit_step=merger.commit_step,
        extract_merged=merger.extract_merged,
    )
    assert merged is None
    assert conflicts == []


# --- LIVE: one bounded A4 run through the driver ----------------------------


def _apply_check(patch: str, run_image_tag: str) -> subprocess.CompletedProcess[str]:
    """``git apply --check`` the merged patch against a FRESH base checkout."""
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
def test_live_a4_runs_n_agents_and_produces_a_scored_merged_patch() -> None:
    """LIVE: bounded A4 (N parallel plain agents) on the seed instance.

    Runs end to end through ``run_campaign`` + the container backends (the
    production path). Asserts the arm produces a scored merged CODE patch within
    the matched TOTAL budget, and SAVES all evidence (merged patch, score report,
    aggregated telemetry, transcript with per-agent results, merge conflicts) under
    :data:`LIVE_EVIDENCE_DIR` for review. Honest about partial/conflict outcomes.
    """
    instance = load_instance(TEXT_TOOLKIT_SLUG)
    campaign = Campaign(
        id="camp_00000000-0000-7000-8000-000000000040",
        createdAt="2026-05-27T00:00:00+00:00",
        model="sonnet",
        arms=[A4.slug],
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
        arms=[A4],
        instances=[instance],
        run_backend=run_backend,
        scoring_backend=scoring_backend,
        pool_size=1,
    )
    wall_clock = time.monotonic() - started
    assert len(campaign_run.results) == 1
    result = campaign_run.results[0]
    conflicts = run_backend.last_merge_conflicts

    out = LIVE_EVIDENCE_DIR
    out.mkdir(parents=True, exist_ok=True)
    patch = result.trial.candidatePatch
    bundle = result.bundle
    report = result.report
    (out / "candidate_patch.diff").write_text(patch or "")
    if bundle is not None:
        (out / "artifact_bundle.json").write_text(
            json.dumps(bundle.to_dict(), indent=2, sort_keys=True)
        )
        if bundle.transcript is not None:
            (out / "transcript.json").write_text(bundle.transcript)
    if report is not None:
        (out / "score_report.json").write_text(
            json.dumps(report.to_dict(), indent=2, sort_keys=True)
        )
    (out / "merge_conflicts.json").write_text(
        json.dumps(conflicts, indent=2, sort_keys=True)
    )
    (out / "run_summary.json").write_text(
        json.dumps(
            {
                "arm": A4.slug,
                "n_agents": A4_N,
                "per_agent_budget_usd": A4_PER_AGENT_MAX_BUDGET_USD,
                "total_budget_usd": A4_TOTAL_MAX_BUDGET_USD,
                "trial_status": result.trial.status,
                "fault": result.fault,
                "wall_clock_seconds": wall_clock,
                "cost_usd": (bundle.telemetry.costUsd if bundle is not None else None),
                "resolved": report.resolved if report is not None else None,
                "regressed": report.regressed if report is not None else None,
                "merge_conflict_count": len(conflicts),
            },
            indent=2,
            sort_keys=True,
        )
    )

    assert not result.is_failed, f"A4 hit an infra fault: {result.fault}"
    assert isinstance(bundle, ArtifactBundle)
    # Budget matched: total spend across the N agents <= A1's single-run cap.
    assert bundle.telemetry.costUsd <= A4_TOTAL_MAX_BUDGET_USD
    assert isinstance(patch, str) and patch.strip() != ""
    run_tag = images.build_run_image(images.get_spec(TEXT_TOOLKIT_SLUG))
    check = _apply_check(patch, run_tag)
    assert check.returncode == 0, f"merged patch did not apply:\n{check.stderr}"
    assert result.report is not None
