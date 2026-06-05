"""Plan-coverage and DAG-validity metrics over captured plan artifacts.

Implements ``.specs/benchmark/specs/04-metrics.md`` §Bucket 3 for the two
plan-artifact metrics that apply to the PLAN-PRODUCING arms (A1, A2, A3):

- **Plan coverage** — the fraction of in-scope spec sections mapped to at least
  one plan task. Pure computation over the bundle's ``specArtifacts`` (the
  in-scope sections) and ``planArtifacts`` (the per-task ``Implements:`` line
  that names the section each task builds).
- **DAG validity** — whether the plan's dependency graph is acyclic AND every
  dependency edge resolves to a real task in the plan. Pure computation over the
  plan's dependency table (``| Task | File | Depends on | ...``).

These read the SAME ``"<relpath>\\n<contents>"`` bundle-entry shape the capture
step produces (see ``benchmark.harness.backends.container`` and
``benchmark.harness.arms.a2_a3._split_capture_entry``). No API, no I/O — given a
captured bundle they are deterministic.

Section -> task mapping (documented)
------------------------------------
The benchmark's specs put each public component's contract under a
``## Component N: <name>`` heading in ``.specs/02-components.md`` (see the
greenfield suite). Those component sections are the IN-SCOPE spec sections: each
is a contract a plan task must implement. Each plan task file carries an
``**Implements:** `.specs/...` § <section>`` line naming the section it
builds (see the captured A1 plan, e.g. ``01-tokenizer.md`` ->
``§ Component 1: tokenizer``). A section is COVERED when at least one task's
``Implements`` line references it. We match on the component's stable identity
-- its number and its name -- so a task that writes ``§ Component 1: tokenizer``
or just ``tokenizer`` both count, tolerant of the exact heading punctuation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# --- named limits / constants ----------------------------------------------

#: Separator the capture step puts between a captured file's relpath and its
#: body (mirrors ``a2_a3._CAPTURE_PATH_BODY_SEP`` / ``container``).
_CAPTURE_PATH_BODY_SEP = "\n"

#: The spec file (suffix) that carries the in-scope component contracts. The
#: greenfield specs put one contract-bearing section per public component here.
_COMPONENTS_SPEC_SUFFIX = "02-components.md"

#: Heading that opens an in-scope component section in the components spec:
#: ``## Component <n>: <name>`` (level-2). Captures the number and the name.
_COMPONENT_HEADING_RE = re.compile(
    r"^##\s+Component\s+(\d+)\s*:\s*(.+?)\s*$", re.MULTILINE
)

#: A plan TASK file's ``Implements`` line, naming the spec section it builds:
#: ``**Implements:** `.specs/...` § <section text>``. The section text is
#: everything after the section marker (``§`` or ``Section``).
_IMPLEMENTS_RE = re.compile(
    r"\*\*Implements:\*\*.*?(?:§|Section)\s*(.+?)\s*$", re.MULTILINE
)

#: A plan's dependency-table row:
#: ``| 01 | [..](..) | <deps> | <edge> | <produces> |``. The first cell is the
#: task id, the third cell its ``Depends on`` list. Header/rule rows are skipped
#: by requiring the first cell to be a task id (digits-led token).
_DEP_TABLE_ROW_RE = re.compile(r"^\|(?P<cells>.+)\|\s*$", re.MULTILINE)

#: A plan task id in the dependency table's first cell (e.g. ``01``, ``04``).
_TASK_ID_RE = re.compile(r"^\d+[a-z0-9_-]*$", re.IGNORECASE)

#: The "no dependencies" placeholder a dependency cell may carry (em dash, en
#: dash, hyphen, or the literal word ``none``).
_NO_DEPS_TOKENS = frozenset({"", "-", "—", "–", "none", "(none)", "n/a"})

#: Plan-file stem of the plan index document itself (``plan.md``), distinguished
#: from the per-task files. The index carries the dependency table.
_PLAN_INDEX_STEM = "plan"


# --- result records ----------------------------------------------------------


@dataclass(frozen=True)
class PlanCoverage:
    """Plan-coverage result: which in-scope spec sections a plan's tasks map to.

    ``covered`` are the in-scope section keys referenced by >= 1 task;
    ``uncovered`` are the in-scope sections no task implements. ``fraction`` is
    ``len(covered) / len(in_scope)`` (0.0 when there are no in-scope sections).
    """

    in_scope: tuple[str, ...]
    covered: tuple[str, ...]
    uncovered: tuple[str, ...]
    fraction: float


@dataclass(frozen=True)
class DagValidity:
    """DAG-validity result over a plan's parsed dependency graph.

    ``valid`` iff the graph is ``acyclic`` AND every edge resolves
    (``dangling_edges`` empty). ``nodes`` are the declared task ids; ``edges``
    map a task to the task ids it depends on; ``cycle`` is a witnessing cycle (a
    list of task ids) when one exists, else empty.
    """

    nodes: tuple[str, ...]
    edges: dict[str, tuple[str, ...]]
    acyclic: bool
    dangling_edges: tuple[tuple[str, str], ...]
    cycle: tuple[str, ...]

    @property
    def valid(self) -> bool:
        """A plan's DAG is valid iff it has nodes, is acyclic, and every edge resolves.

        An empty graph (no parseable dependency table) is NOT valid: a
        plan-producing arm must produce a parseable plan with at least one task.
        """
        return bool(self.nodes) and self.acyclic and not self.dangling_edges


# --- capture-entry helpers ---------------------------------------------------


def _split_capture_entry(entry: str) -> tuple[str, str]:
    """Split a captured ``"<relpath>\\n<contents>"`` entry into (relpath, body)."""
    relpath, _, body = entry.partition(_CAPTURE_PATH_BODY_SEP)
    return relpath.strip(), body


def _relpath_stem(relpath: str) -> str:
    """The file stem of a captured relpath (``a/b/01-x.md`` -> ``01-x``)."""
    name = relpath.rsplit("/", 1)[-1]
    if name.endswith(".md"):
        name = name[: -len(".md")]
    return name


# --- plan coverage -----------------------------------------------------------


def _normalize_section_key(text: str) -> str:
    """Canonicalise a section label to a stable comparison key.

    Lower-cases, collapses whitespace, and strips a leading ``component <n>:``
    marker so an ``Implements`` reference and a heading compare on the component
    NAME (and number when present). Keeps the number as a ``c<n>`` prefix when
    the label carries one so two same-named-but-different-numbered sections stay
    distinct.
    """
    label = " ".join(text.strip().lower().split())
    match = re.match(r"component\s+(\d+)\s*:\s*(.+)$", label)
    if match:
        number, name = match.group(1), match.group(2).strip()
        return f"c{number}:{name}"
    return label


def in_scope_spec_sections(spec_artifacts: list[str]) -> tuple[str, ...]:
    """The in-scope spec-section keys: the components-spec ``Component`` headings.

    Parses the captured ``specArtifacts`` for the components spec
    (:data:`_COMPONENTS_SPEC_SUFFIX`) and returns one normalized key per
    ``## Component <n>: <name>`` heading — the contract-bearing sections a plan
    must cover. Order follows the headings' order in the spec.
    """
    sections: list[str] = []
    for entry in spec_artifacts:
        relpath, body = _split_capture_entry(entry)
        if not relpath.endswith(_COMPONENTS_SPEC_SUFFIX):
            continue
        for match in _COMPONENT_HEADING_RE.finditer(body):
            number, name = match.group(1), match.group(2)
            sections.append(_normalize_section_key(f"Component {number}: {name}"))
    # De-duplicate while preserving first-seen order.
    seen: dict[str, None] = {}
    for key in sections:
        seen.setdefault(key, None)
    return tuple(seen)


def implemented_section_keys(plan_artifacts: list[str]) -> tuple[str, ...]:
    """Section keys the plan's TASK files claim via their ``Implements`` lines.

    Each per-task plan file (every plan artifact except the ``plan.md`` index)
    may carry an ``**Implements:** ... § <section>`` line; this returns the
    normalized key of every section so referenced, in first-seen order.
    """
    keys: list[str] = []
    for entry in plan_artifacts:
        relpath, body = _split_capture_entry(entry)
        if not relpath.endswith(".md"):
            continue
        if _relpath_stem(relpath) == _PLAN_INDEX_STEM:
            continue
        for match in _IMPLEMENTS_RE.finditer(body):
            keys.append(_normalize_section_key(match.group(1)))
    seen: dict[str, None] = {}
    for key in keys:
        seen.setdefault(key, None)
    return tuple(seen)


def plan_coverage(spec_artifacts: list[str], plan_artifacts: list[str]) -> PlanCoverage:
    """Compute plan coverage: in-scope sections mapped to >= 1 plan task.

    A section is covered when at least one task's ``Implements`` key matches its
    key (exact normalized match, or the implemented key contains the section's
    component NAME — so ``§ Component 1: tokenizer`` and a bare ``tokenizer``
    both cover the tokenizer section). ``fraction`` = covered / in-scope; 0.0
    when the spec declares no in-scope sections.
    """
    in_scope = in_scope_spec_sections(spec_artifacts)
    implemented = implemented_section_keys(plan_artifacts)
    implemented_set = set(implemented)

    covered: list[str] = []
    uncovered: list[str] = []
    for section in in_scope:
        if _section_is_covered(section, implemented_set):
            covered.append(section)
        else:
            uncovered.append(section)

    fraction = len(covered) / len(in_scope) if in_scope else 0.0
    return PlanCoverage(
        in_scope=in_scope,
        covered=tuple(covered),
        uncovered=tuple(uncovered),
        fraction=fraction,
    )


def _section_name(section_key: str) -> str:
    """The bare component name of a section key (``c1:tokenizer`` -> ``tokenizer``)."""
    return section_key.split(":", 1)[1] if ":" in section_key else section_key


def _section_is_covered(section_key: str, implemented: set[str]) -> bool:
    """Whether any implemented key covers ``section_key``.

    Covered by an exact normalized match, or by an implemented key that names
    the section's component (the name appears as a whole word in the key) — so a
    task that references the component by name without the ``Component N:``
    prefix still counts.
    """
    if section_key in implemented:
        return True
    name = _section_name(section_key)
    name_word = re.compile(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])")
    return any(name_word.search(_section_name(key)) for key in implemented)


# --- DAG validity ------------------------------------------------------------


def _parse_dependency_table(plan_index_body: str) -> dict[str, tuple[str, ...]]:
    """Parse a plan index's dependency table into ``task -> (dep task ids)``.

    Reads each ``| <task> | <file> | <depends-on> | ...`` row whose first cell is
    a task id; the third cell lists the task ids it depends on (split on commas /
    whitespace), with a no-dependency placeholder yielding an empty tuple.
    """
    edges: dict[str, tuple[str, ...]] = {}
    for row_match in _DEP_TABLE_ROW_RE.finditer(plan_index_body):
        cells = [c.strip() for c in row_match.group("cells").split("|")]
        if len(cells) < 3:
            continue
        task = cells[0]
        if not _TASK_ID_RE.match(task):
            continue
        deps = _parse_dep_cell(cells[2])
        edges[task] = deps
    return edges


def _parse_dep_cell(cell: str) -> tuple[str, ...]:
    """Parse a ``Depends on`` cell into the task ids it references (or empty)."""
    if cell.strip().lower() in _NO_DEPS_TOKENS:
        return ()
    tokens = re.split(r"[,\s]+", cell.strip())
    return tuple(t for t in tokens if t and t.lower() not in _NO_DEPS_TOKENS)


def _find_cycle(edges: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    """Return a witnessing cycle in the dependency graph, or () if acyclic.

    Iterative depth-first search over the resolvable edges (dangling edges are
    ignored here — :func:`dag_validity` reports them separately). Returns the
    cycle as the ordered task ids closing the loop, e.g. ``("a", "b", "a")``.
    """
    WHITE, GREY, BLACK = 0, 1, 2
    color: dict[str, int] = {node: WHITE for node in edges}

    for root in edges:
        if color[root] != WHITE:
            continue
        # Each stack frame is (node, path-to-node).
        stack: list[tuple[str, tuple[str, ...]]] = [(root, (root,))]
        color[root] = GREY
        while stack:
            node, path = stack[-1]
            progressed = False
            for dep in edges.get(node, ()):
                if dep not in color:
                    continue  # dangling edge; handled elsewhere
                if color[dep] == GREY:
                    # Found a back-edge: the cycle is path[from dep] + dep.
                    start = path.index(dep)
                    return (*path[start:], dep)
                if color[dep] == WHITE:
                    color[dep] = GREY
                    stack.append((dep, (*path, dep)))
                    progressed = True
                    break
            if not progressed:
                color[node] = BLACK
                stack.pop()
    return ()


def dag_validity(plan_artifacts: list[str]) -> DagValidity:
    """Compute DAG validity for a plan from its captured artifacts.

    Locates the ``plan.md`` index among ``plan_artifacts``, parses its
    dependency table into nodes + edges, and decides validity: the graph must be
    ACYCLIC and every edge must reference a declared task (no dangling edges).
    When no dependency table is found the plan has no nodes and is reported
    invalid (a plan-producing arm must produce a parseable plan).
    """
    edges: dict[str, tuple[str, ...]] = {}
    for entry in plan_artifacts:
        relpath, body = _split_capture_entry(entry)
        if relpath.endswith(".md") and _relpath_stem(relpath) == _PLAN_INDEX_STEM:
            edges = _parse_dependency_table(body)
            break

    nodes = tuple(edges)
    node_set = set(nodes)
    dangling: list[tuple[str, str]] = [
        (task, dep)
        for task, deps in edges.items()
        for dep in deps
        if dep not in node_set
    ]
    cycle = _find_cycle(edges)
    return DagValidity(
        nodes=nodes,
        edges=edges,
        acyclic=not cycle,
        dangling_edges=tuple(dangling),
        cycle=cycle,
    )
