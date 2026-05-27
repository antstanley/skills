"""Component 1: ``graph`` — the dependency-graph data structure.

Skeleton stub. The acceptance suite under ``hidden/`` is the oracle.
"""

from __future__ import annotations


class DependencyGraph:
    """A directed graph of tasks, each with a set of prerequisite tasks."""

    def add_task(self, name: str, depends_on: list[str] | None = None) -> None:
        """Register ``name`` with its prerequisite task names. (TODO.)"""
        raise NotImplementedError("DependencyGraph.add_task is not implemented yet")

    def tasks(self) -> list[str]:
        """Return all registered task names in insertion order. (TODO.)"""
        raise NotImplementedError("DependencyGraph.tasks is not implemented yet")

    def prerequisites(self, name: str) -> list[str]:
        """Return the prerequisite task names declared for ``name``. (TODO.)"""
        raise NotImplementedError(
            "DependencyGraph.prerequisites is not implemented yet"
        )
