"""Hidden acceptance suite for the ``graph`` component (failToPass).

Scoring-side ONLY.

Contract: ``DependencyGraph`` records tasks in insertion order; ``add_task``
defaults ``depends_on`` to an empty list; re-adding a task replaces its
prerequisites; ``prerequisites`` returns the declared list (copy).
"""

from __future__ import annotations

from task_scheduler.graph import DependencyGraph


def test_tasks_preserve_insertion_order() -> None:
    g = DependencyGraph()
    g.add_task("c")
    g.add_task("a")
    g.add_task("b")
    assert g.tasks() == ["c", "a", "b"]


def test_prerequisites_default_to_empty() -> None:
    g = DependencyGraph()
    g.add_task("solo")
    assert g.prerequisites("solo") == []


def test_prerequisites_round_trip() -> None:
    g = DependencyGraph()
    g.add_task("build", ["compile", "lint"])
    assert g.prerequisites("build") == ["compile", "lint"]


def test_re_adding_replaces_prerequisites() -> None:
    g = DependencyGraph()
    g.add_task("x", ["old"])
    g.add_task("x", ["new"])
    assert g.prerequisites("x") == ["new"]
    assert g.tasks().count("x") == 1
