"""Hidden acceptance suite for the ``topo`` component (failToPass).

Scoring-side ONLY. Depends on the graph contract.

Contract: ``topological_order`` returns every task exactly once with each task
appearing after all its prerequisites. Ties are broken deterministically by
the order tasks become ready (Kahn's algorithm seeded by insertion order),
so the output is stable.
"""

from __future__ import annotations

from task_scheduler.graph import DependencyGraph
from task_scheduler.topo import topological_order


def _is_valid_order(graph: DependencyGraph, order: list[str]) -> bool:
    position = {name: i for i, name in enumerate(order)}
    if sorted(order) != sorted(graph.tasks()):
        return False
    return all(
        position[prereq] < position[name]
        for name in graph.tasks()
        for prereq in graph.prerequisites(name)
    )


def test_orders_simple_chain() -> None:
    g = DependencyGraph()
    g.add_task("a")
    g.add_task("b", ["a"])
    g.add_task("c", ["b"])
    assert topological_order(g) == ["a", "b", "c"]


def test_respects_dependencies_in_diamond() -> None:
    g = DependencyGraph()
    g.add_task("root")
    g.add_task("left", ["root"])
    g.add_task("right", ["root"])
    g.add_task("merge", ["left", "right"])
    assert _is_valid_order(g, topological_order(g))


def test_is_deterministic_by_insertion_order() -> None:
    g = DependencyGraph()
    g.add_task("setup")
    g.add_task("b", ["setup"])
    g.add_task("a", ["setup"])
    # Both "a" and "b" become ready together; insertion order breaks the tie.
    assert topological_order(g) == ["setup", "b", "a"]
