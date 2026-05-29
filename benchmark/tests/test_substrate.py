"""Substrate tests: the BenchFlow ``bench`` SDK is wired and its gate works.

Task 01 layers the BenchFlow substrate (``05-harness-architecture.md``
§Substrate) onto the M0 skeleton. These tests assert what was actually wired:

- the locked ``benchflow`` distribution imports and reports its version;
- ``bench tasks check`` (BenchFlow's own structural validator) passes on the
  in-repo trivial probe task — the spec's ``bench tasks check`` gate holds;
- the recorded substrate finding (``benchmark.harness.substrate``) is internally
  consistent with the probe's layout.

The deeper finding — that BenchFlow does NOT natively express the two-container
run/scoring split, which stays on the benchmark's own backend seam — is recorded
in ``benchmark.harness.substrate`` and the plan's Open questions; here it is
pinned only as the substrate constants.
"""

from __future__ import annotations

from pathlib import Path

from benchflow._utils.task_authoring import check_task

from benchmark.harness import substrate

#: The in-repo throwaway task ``bench tasks init`` scaffolded; ``bench tasks
#: check`` must validate it. Relative to the repo root (two levels above this
#: ``benchmark/tests`` file).
_PROBE_TASK = (
    Path(__file__).resolve().parents[2]
    / "benchmark"
    / "suites"
    / "benchflow-probe"
    / "trivial-probe"
)


def test_benchflow_imports_and_is_locked() -> None:
    """The locked ``benchflow`` substrate imports and reports its version."""
    version = substrate.benchflow_version()
    assert version, "benchflow distribution must report a version"
    # Pinned major.minor the task investigated; patch left free.
    assert version.startswith("0.4"), version


def test_bench_tasks_check_passes_on_trivial_probe() -> None:
    """``bench tasks check`` validates the in-repo trivial probe task.

    This is the spec's ``bench tasks check`` gate, run through BenchFlow's own
    validator (the same code path the ``bench`` CLI invokes). Empty issue list
    == valid.
    """
    assert _PROBE_TASK.is_dir(), f"probe task missing: {_PROBE_TASK}"
    issues = check_task(_PROBE_TASK)
    assert issues == [], f"bench tasks check reported issues: {issues}"


def test_probe_has_benchflow_required_layout() -> None:
    """The probe carries every file/dir BenchFlow's ``check`` requires."""
    for required_file in substrate.REQUIRED_TASK_FILES:
        assert (_PROBE_TASK / required_file).is_file(), required_file
    for required_dir in substrate.REQUIRED_TASK_DIRS:
        assert (_PROBE_TASK / required_dir).is_dir(), required_dir


def test_substrate_finding_constants() -> None:
    """The recorded substrate decision matches what was investigated.

    ``bench tasks check`` is available; the two-container split is NOT native to
    BenchFlow's eval model (it stays on the benchmark's backend seam); and
    ``check`` does not validate the benchmark's ``TaskInstance`` schema.
    """
    assert substrate.BENCH_TASKS_CLI_AVAILABLE is True
    assert substrate.BENCH_NATIVE_TWO_CONTAINER_SPLIT is False
    assert substrate.BENCH_VALIDATES_TASKINSTANCE_SCHEMA is False
