"""Component 4: ``scheduler`` — compose validation and ordering.

Depends on :mod:`task_scheduler.topo` and :mod:`task_scheduler.validators`.
Skeleton stub.
"""

from __future__ import annotations

from task_scheduler.graph import DependencyGraph


class ScheduleError(ValueError):
    """Raised when a graph cannot be scheduled (missing deps or a cycle)."""


def schedule(graph: DependencyGraph) -> list[str]:
    """Validate ``graph`` then return a runnable task order. (TODO.)"""
    raise NotImplementedError("schedule is not implemented yet")
