"""``task_scheduler`` — a tiny dependency-aware task scheduler (skeleton).

SKELETON the arms start from: every public function is a stub raising
:class:`NotImplementedError`. The prose specification and the withheld
acceptance suite define the contracts.

Components and dependency graph (width + depth):

    graph  ──►  topo  ──►  scheduler
      └──────────────────►  validators  ──►  scheduler

``graph`` is the foundational data structure; ``topo`` and ``validators`` both
depend on it; ``scheduler`` composes ``topo`` and ``validators``.
"""

from __future__ import annotations

from task_scheduler.graph import DependencyGraph
from task_scheduler.scheduler import schedule
from task_scheduler.topo import topological_order
from task_scheduler.validators import find_cycle, missing_dependencies

__all__ = [
    "DependencyGraph",
    "find_cycle",
    "missing_dependencies",
    "schedule",
    "topological_order",
]
