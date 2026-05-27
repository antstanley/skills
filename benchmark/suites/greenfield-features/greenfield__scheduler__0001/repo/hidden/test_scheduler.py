"""Hidden acceptance suite for the ``scheduler`` component (failToPass).

Scoring-side ONLY. Exercises composition of validators + topo.

Contract: ``schedule(graph)`` raises ``ScheduleError`` if the graph has missing
dependencies or a cycle; otherwise it returns ``topological_order(graph)``.
"""

from __future__ import annotations

import pytest
from task_scheduler.graph import DependencyGraph
from task_scheduler.scheduler import ScheduleError, schedule


def test_schedule_returns_topological_order() -> None:
    g = DependencyGraph()
    g.add_task("a")
    g.add_task("b", ["a"])
    g.add_task("c", ["b"])
    assert schedule(g) == ["a", "b", "c"]


def test_schedule_rejects_missing_dependency() -> None:
    g = DependencyGraph()
    g.add_task("a", ["ghost"])
    with pytest.raises(ScheduleError):
        schedule(g)


def test_schedule_rejects_cycle() -> None:
    g = DependencyGraph()
    g.add_task("a", ["b"])
    g.add_task("b", ["a"])
    with pytest.raises(ScheduleError):
        schedule(g)
