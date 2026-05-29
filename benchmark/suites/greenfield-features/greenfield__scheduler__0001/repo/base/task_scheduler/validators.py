"""Component 3: ``validators`` — detect malformed dependency graphs.

Depends on :mod:`task_scheduler.graph`. Skeleton stub.
"""

from __future__ import annotations

from task_scheduler.graph import DependencyGraph


def missing_dependencies(graph: DependencyGraph) -> list[str]:
    """Return prerequisite names referenced but never registered. (TODO.)"""
    raise NotImplementedError("missing_dependencies is not implemented yet")


def find_cycle(graph: DependencyGraph) -> list[str] | None:
    """Return a cycle as a task-name list, or ``None`` if acyclic. (TODO.)"""
    raise NotImplementedError("find_cycle is not implemented yet")
