"""Plan-coverage and DAG-validity tests (NON-LIVE, pure computation).

Covers ``benchmark.harness.stats.artifact_metrics`` against (a) a synthetic plan
with a KNOWN section->task mapping and known dependency graph, and (b) the
CAPTURED A1 live evidence (a real plan.md + task files). DAG validity is checked
on a valid graph (true), a cyclic graph (false), and a dangling-edge graph
(false). Restricted-to-arms applicability (A1/A2/A3) is documented in the module.
"""

from __future__ import annotations

import json
from pathlib import Path

from benchmark.harness.stats.artifact_metrics import (
    dag_validity,
    implemented_section_keys,
    in_scope_spec_sections,
    plan_coverage,
)

# --- captured A1 evidence ----------------------------------------------------

_A1_BUNDLE = (
    Path(__file__).resolve().parent / "_a1_live_evidence" / "artifact_bundle.json"
)


def _load_a1_bundle() -> dict:
    return json.loads(_A1_BUNDLE.read_text(encoding="utf-8"))


# --- synthetic captured-entry builders --------------------------------------


def _entry(relpath: str, body: str) -> str:
    """Build a captured ``"<relpath>\\n<contents>"`` bundle entry."""
    return f"{relpath}\n{body}"


def _components_spec(*names: str) -> str:
    """A synthetic components spec with one ``## Component N: <name>`` per name."""
    body = "\n\n".join(
        f"## Component {i}: {name}\n### Contract\nsome contract."
        for i, name in enumerate(names, start=1)
    )
    return _entry(".specs/02-components.md", f"# Components\n\n{body}\n")


def _task_file(stem: str, implements: str) -> str:
    """A synthetic per-task plan file with an ``Implements`` line."""
    body = (
        f"# Task {stem}\n\n## Structure\n\n"
        f"**Implements:** `.specs/02-components.md` § {implements}\n"
    )
    return _entry(f".specs/plans/p/{stem}.md", body)


def _plan_index(rows: list[tuple[str, str]]) -> str:
    """A synthetic plan.md index carrying a dependency table.

    ``rows`` are ``(task_id, depends_on_cell)`` pairs.
    """
    lines = [
        "# Plan",
        "",
        "### Dependency table",
        "",
        "| Task | File | Depends on | Edge | Produces |",
        "| --- | --- | --- | --- | --- |",
    ]
    for task, deps in rows:
        lines.append(f"| {task} | [{task}]({task}.md) | {deps} | build | x |")
    return _entry(".specs/plans/p/plan.md", "\n".join(lines) + "\n")


# --- plan coverage: known-answer on a synthetic plan ------------------------


def test_in_scope_sections_are_the_component_headings() -> None:
    specs = [_components_spec("alpha", "beta", "gamma")]
    sections = in_scope_spec_sections(specs)
    assert sections == ("c1:alpha", "c2:beta", "c3:gamma")


def test_plan_coverage_full_mapping_is_one() -> None:
    specs = [_components_spec("alpha", "beta")]
    plans = [
        _plan_index([("01", "—"), ("02", "01")]),
        _task_file("01", "Component 1: alpha"),
        _task_file("02", "Component 2: beta"),
    ]
    result = plan_coverage(specs, plans)
    assert result.fraction == 1.0
    assert set(result.covered) == {"c1:alpha", "c2:beta"}
    assert result.uncovered == ()


def test_plan_coverage_partial_mapping_is_fraction() -> None:
    # Three in-scope sections, only two implemented -> 2/3.
    specs = [_components_spec("alpha", "beta", "gamma")]
    plans = [
        _plan_index([("01", "—"), ("02", "01")]),
        _task_file("01", "Component 1: alpha"),
        _task_file("02", "Component 3: gamma"),
    ]
    result = plan_coverage(specs, plans)
    assert result.fraction == 2 / 3
    assert "c2:beta" in result.uncovered
    assert set(result.covered) == {"c1:alpha", "c3:gamma"}


def test_plan_coverage_matches_bare_component_name() -> None:
    # A task that references the component by NAME (no "Component N:" prefix)
    # still covers the section.
    specs = [_components_spec("tokenizer")]
    plans = [
        _plan_index([("01", "—")]),
        _task_file("01", "tokenizer"),
    ]
    result = plan_coverage(specs, plans)
    assert result.fraction == 1.0


def test_plan_index_implements_line_is_not_a_task() -> None:
    # The plan.md index is skipped when gathering implemented sections.
    plans = [_plan_index([("01", "—")])]
    assert implemented_section_keys(plans) == ()


# --- plan coverage: captured A1 evidence ------------------------------------


def test_plan_coverage_on_captured_a1_evidence_is_full() -> None:
    bundle = _load_a1_bundle()
    result = plan_coverage(bundle["specArtifacts"], bundle["planArtifacts"])
    # The A1 plan maps all four text_toolkit component sections to tasks.
    assert result.in_scope == (
        "c1:tokenizer",
        "c2:normalizer",
        "c3:frequency",
        "c4:pipeline",
    )
    assert result.fraction == 1.0
    assert result.uncovered == ()


# --- DAG validity: valid / cyclic / dangling --------------------------------


def test_dag_validity_valid_graph_is_valid() -> None:
    plans = [_plan_index([("01", "—"), ("02", "01"), ("03", "01, 02")])]
    dv = dag_validity(plans)
    assert dv.nodes == ("01", "02", "03")
    assert dv.edges == {"01": (), "02": ("01",), "03": ("01", "02")}
    assert dv.acyclic is True
    assert dv.dangling_edges == ()
    assert dv.valid is True


def test_dag_validity_cyclic_graph_is_invalid() -> None:
    plans = [_plan_index([("01", "02"), ("02", "01")])]
    dv = dag_validity(plans)
    assert dv.acyclic is False
    assert dv.valid is False
    # The cycle witnesses a closed loop over the two tasks.
    assert set(dv.cycle) == {"01", "02"}
    assert dv.cycle[0] == dv.cycle[-1]


def test_dag_validity_self_loop_is_a_cycle() -> None:
    plans = [_plan_index([("01", "01")])]
    dv = dag_validity(plans)
    assert dv.acyclic is False
    assert dv.valid is False


def test_dag_validity_dangling_edge_is_invalid() -> None:
    # Task 02 depends on 99, which is not a declared task.
    plans = [_plan_index([("01", "—"), ("02", "99")])]
    dv = dag_validity(plans)
    assert dv.acyclic is True  # no cycle, but...
    assert dv.dangling_edges == (("02", "99"),)
    assert dv.valid is False


def test_dag_validity_no_plan_index_is_invalid() -> None:
    # A plan-producing arm must produce a parseable plan; no table -> no nodes.
    plans = [_task_file("01", "Component 1: alpha")]
    dv = dag_validity(plans)
    assert dv.nodes == ()
    assert dv.valid is False


# --- DAG validity: captured A1 evidence -------------------------------------


def test_dag_validity_on_captured_a1_evidence_is_valid() -> None:
    bundle = _load_a1_bundle()
    dv = dag_validity(bundle["planArtifacts"])
    assert dv.nodes == ("01", "02", "03", "04")
    assert dv.edges["04"] == ("01", "02", "03")
    assert dv.valid is True
