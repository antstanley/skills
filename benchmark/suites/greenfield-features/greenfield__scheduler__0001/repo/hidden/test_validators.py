"""Hidden acceptance suite for the ``validators`` component (failToPass).

Scoring-side ONLY. Depends on the graph contract.

Contract:
- ``missing_dependencies`` returns the sorted, de-duplicated prerequisite names
  that are referenced but never registered as tasks.
- ``find_cycle`` returns a list of task names forming a cycle (in dependency
  order, the first node repeated implicitly), or ``None`` when the graph is
  acyclic.
"""

from __future__ import annotations

from task_scheduler.graph import DependencyGraph
from task_scheduler.validators import find_cycle, missing_dependencies


def test_missing_dependencies_sorted_and_unique() -> None:
    g = DependencyGraph()
    g.add_task("a", ["x", "y"])
    g.add_task("b", ["x"])
    assert missing_dependencies(g) == ["x", "y"]


def test_no_missing_dependencies() -> None:
    g = DependencyGraph()
    g.add_task("a")
    g.add_task("b", ["a"])
    assert missing_dependencies(g) == []


def test_find_cycle_returns_none_when_acyclic() -> None:
    g = DependencyGraph()
    g.add_task("a")
    g.add_task("b", ["a"])
    assert find_cycle(g) is None


def test_find_cycle_detects_a_cycle() -> None:
    g = DependencyGraph()
    g.add_task("a", ["b"])
    g.add_task("b", ["a"])
    cycle = find_cycle(g)
    assert cycle is not None
    assert set(cycle) == {"a", "b"}
