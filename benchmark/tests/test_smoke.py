"""Smoke test: the benchmark package and its harness sub-packages import.

Asserts the Docker-free skeleton named in ``05-harness-architecture.md``
§Implementation layout (plus the backend seam from the local-backends change
spec) is importable. As of Task 01 the BenchFlow substrate (§Substrate) is now
wired, so this also asserts ``benchflow`` is installed (the detailed substrate
finding lives in ``benchmark.harness.substrate`` / ``test_substrate.py``).
"""

import importlib
import importlib.util

# The harness sub-packages the skeleton must expose, per the spec's
# §Implementation layout and the local-backends change spec.
HARNESS_SUBPACKAGES = (
    "driver",
    "arms",
    "scoring",
    "backends",
    "telemetry",
    "stats",
)


def test_harness_package_imports() -> None:
    """``benchmark.harness`` resolves as a package."""
    harness = importlib.import_module("benchmark.harness")
    assert harness is not None


def test_harness_subpackages_resolve() -> None:
    """Every named harness sub-package imports cleanly."""
    for name in HARNESS_SUBPACKAGES:
        module = importlib.import_module(f"benchmark.harness.{name}")
        assert module is not None, name


def test_suites_package_imports() -> None:
    """``benchmark.suites`` resolves as a package."""
    suites = importlib.import_module("benchmark.suites")
    assert suites is not None


def test_benchflow_substrate_installed() -> None:
    """The BenchFlow substrate (Task 01, §Substrate) is installed and locked."""
    spec = importlib.util.find_spec("benchflow")
    assert spec is not None, "BenchFlow must be wired as of Task 01"
