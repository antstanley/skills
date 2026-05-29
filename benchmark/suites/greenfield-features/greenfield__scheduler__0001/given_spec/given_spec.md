# Given Spec — `task_scheduler`

> **Frozen A2/A3 asset.** This spec is the ready-made specification handed to
> arms **A2** (plan + build, gates on) and **A3** (build without gates). It is
> authored ONCE to the fixed quality bar documented in
> `benchmark/harness/arms/a2_a3.py` (`GIVEN_SPEC_QUALITY_BAR`) and is consumed
> **identically** by both arms, so that spec variance never leaks into the
> A1−A2 or A2−A3 deltas. It is the spec-creator stage's output, replaced by a
> fixed authored artifact; the only difference between A2 and A3 is the gates.
> Do not regenerate per run.

## 1. Overview

`task_scheduler` is a tiny dependency-aware task scheduler with four
interlocking components. The package's `__init__` re-exports
`DependencyGraph`, `topological_order`, `missing_dependencies`, `find_cycle`,
and `schedule`. Standard library only. The dependency graph (each component
consumes the one above it):

```
graph ──► topo ──► scheduler
   └────► validators ──► scheduler
```

## 2. Domain model and invariants

- **Task.** A named node with an ordered list of prerequisite task names.
- **Insertion order.** `tasks()` returns task names in the order first added;
  topological ties break by insertion order so results are deterministic.
- **Invariants.**
  1. Re-adding a task replaces its prerequisites without duplicating the task
     or changing its insertion position.
  2. `topological_order` returns every task exactly once, each after all its
     prerequisites (Kahn's algorithm), deterministic by insertion order.
  3. A missing dependency is a prerequisite name never registered as a task.

## 3. Components (contracts)

### Component 1 — `graph.DependencyGraph`

- `add_task(name, depends_on=None)` registers a task and its prerequisite names
  (default none). Re-adding replaces prerequisites without duplicating the task
  (invariant 1).
- `tasks() -> list[str]` returns task names in insertion order.
- `prerequisites(name) -> list[str]` returns the declared prerequisite list
  (empty list by default).

### Component 2 — `topo.topological_order(graph) -> list[str]`

Consumes the graph. Return every task once, each after all its prerequisites,
breaking ties by insertion order (Kahn's algorithm) so the result is
deterministic. A simple chain `a→b→c` yields `[a, b, c]`; a diamond respects all
edges.

### Component 3 — `validators.missing_dependencies(graph) -> list[str]` and `validators.find_cycle(graph) -> list[str] | None`

Use the graph.

- `missing_dependencies` returns the SORTED, de-duplicated prerequisite names
  never registered as tasks. Empty list when every prerequisite is a task.
- `find_cycle` returns a task-name list forming a cycle, or `None` when acyclic.

### Component 4 — `scheduler.schedule(graph) -> list[str]`

Composes topo + validators. Raise `scheduler.ScheduleError` if the graph has
missing dependencies OR a cycle; otherwise return `topological_order(graph)`.

## 4. Definition of done (acceptance bar)

- Every public function/class is implemented (no `NotImplementedError`),
  standard library only.
- The package `__init__` re-exports all five names.
- Each component honours its contract and the invariants above; `schedule`
  raises `ScheduleError` on missing-dependency and cyclic graphs.
- The existing `test_smoke.py` continues to pass (public API importable).
- A withheld acceptance suite (never shown to the arms) decides resolution.
