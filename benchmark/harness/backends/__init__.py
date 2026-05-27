"""Backends: pluggable RunBackend / ScoringBackend (container + local).

Defined by ``changes/2026-05-27-local_backends.md``; the driver, scorer rule,
and statistics are agnostic to how a Trial is run and scored.
"""

from __future__ import annotations

from benchmark.harness.backends.container import (
    AGENT_SOLVER,
    ContainerAuthError,
    ContainerRunBackend,
    ContainerRunError,
)
from benchmark.harness.backends.interfaces import (
    HIDDEN_TEST_FIELDS,
    ArmOrSolver,
    CandidatePatch,
    RunBackend,
    ScoringBackend,
)
from benchmark.harness.backends.local import (
    FIXTURE_SOLVER,
    RUN_DIR_PREFIX,
    RUN_TEMP_BASE,
    LocalRunBackend,
    LocalRunError,
)

__all__ = [
    "AGENT_SOLVER",
    "FIXTURE_SOLVER",
    "HIDDEN_TEST_FIELDS",
    "RUN_DIR_PREFIX",
    "RUN_TEMP_BASE",
    "ArmOrSolver",
    "CandidatePatch",
    "ContainerAuthError",
    "ContainerRunBackend",
    "ContainerRunError",
    "LocalRunBackend",
    "LocalRunError",
    "RunBackend",
    "ScoringBackend",
]
