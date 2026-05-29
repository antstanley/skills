"""Skeleton smoke test (passToPass): the package and its components import.

Ships in the run-visible ``base/`` tree and PASSES on the skeleton as delivered;
must keep passing after the arm implements the scheduler.
"""

from __future__ import annotations

import task_scheduler


def test_public_api_is_exposed() -> None:
    for name in (
        "DependencyGraph",
        "topological_order",
        "missing_dependencies",
        "find_cycle",
        "schedule",
    ):
        assert hasattr(task_scheduler, name)


def test_component_modules_import() -> None:
    import task_scheduler.graph  # noqa: F401
    import task_scheduler.scheduler  # noqa: F401
    import task_scheduler.topo  # noqa: F401
    import task_scheduler.validators  # noqa: F401
