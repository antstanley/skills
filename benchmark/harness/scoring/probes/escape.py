"""False-``Done`` escape-rate accounting over organic gated trials.

Implements the **false-``Done`` escape rate** of
``.specs/benchmark/specs/04-metrics.md`` §Bucket 3 and the **false-``Done``
escapes** half of ``.specs/benchmark/specs/06-scoring-and-statistics.md``
§Gate-efficacy probes, for the GATED arms (A1, A2).

Definition: across organic gated trials, the fraction of ``Done`` tasks whose
hidden tests fail. A gated workflow marks a task ``Done`` only when its gates
pass; an ESCAPE is a task the gates passed (so the workflow called it Done) that
nonetheless fails the hidden oracle. The signal lives on
``ScoreReport.gateEscape``.

Two granularities, per the spec:

- **Per-task** — when the instance carries ``testTags`` (the greenfield suite
  does), each failing hidden selector maps to a spec section/component, and a
  ``Done`` task that claims that component but whose tests fail is an escape at
  task granularity (:func:`per_task_escapes`).
- **Instance** — where ``testTags`` are absent, fall back to instance
  granularity: the whole instance is one ``Done`` unit, and it escapes iff it is
  ``Done`` (gates passed) yet unresolved (:func:`derive_gate_escape`).

The escape rate (:func:`escape_rate`) aggregates these over the gated trials.
Pure computation over ``ScoreReport``s + the instance ``testTags``; no API.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from benchmark.harness.domain import ScoreReport, TaskInstance

# --- applicable arms ---------------------------------------------------------

#: The gated arms the escape rate applies to (A1, A2). A3 disables its gates;
#: A0 / A4 have none. Mirrors ``04-metrics.md`` §Bucket 3 applicability.
GATED_ARMS: tuple[str, ...] = ("A1", "A2")


# --- result records ----------------------------------------------------------


@dataclass(frozen=True)
class TaskEscape:
    """One ``Done``-task escape: a component the gates passed but tests fail.

    ``component`` is the spec section/component (the ``testTags`` value); the
    failing selectors are the hidden ``failToPass`` tests for it that did not
    pass. ``trial`` is the originating trial id.
    """

    trial: str
    component: str
    failing_selectors: tuple[str, ...]


@dataclass(frozen=True)
class EscapeRate:
    """The false-``Done`` escape-rate accounting.

    ``escaped`` = ``Done`` units whose hidden tests fail; ``total`` = all
    ``Done`` units considered; ``rate`` = ``escaped / total`` (0.0 when
    ``total == 0``). ``granularity`` records whether the units are per-``task``
    (``testTags`` present) or per-``instance`` (fallback); ``task_escapes`` holds
    the per-task escapes when at task granularity.
    """

    escaped: int
    total: int
    rate: float
    granularity: str
    task_escapes: tuple[TaskEscape, ...] = field(default_factory=tuple)


# --- granularity tags --------------------------------------------------------

GRANULARITY_TASK = "task"
GRANULARITY_INSTANCE = "instance"


# --- instance-granularity escape ---------------------------------------------


def derive_gate_escape(report: ScoreReport) -> bool:
    """Derive instance-granularity ``gateEscape`` for a gated trial's report.

    A gated trial whose workflow reached an integration tip is, by construction,
    one the gates passed (it marked its tasks ``Done`` — that is what produced a
    scored candidate). An ESCAPE at instance granularity is therefore a scored
    trial that is NOT resolved: the gates passed it as Done, yet the hidden
    oracle fails. This is exactly ``not report.resolved`` for a gated trial — the
    derivation the spec calls for where ``testTags`` are absent.
    """
    return not report.resolved


def _with_gate_escape(report: ScoreReport, value: bool | None) -> ScoreReport:
    """Return a new ``ScoreReport`` equal to ``report`` but with ``gateEscape``.

    The canonical write site for ``ScoreReport.gateEscape``. The field is the
    gated-arm escape signal (``06-scoring-and-statistics.md`` §The test oracle):
    populated on GATED arms (A1, A2 — :data:`GATED_ARMS`) and LEFT UNSET on
    non-gated arms (A0, A4, and A3 whose gates are disabled), so a future reader
    is not tempted to populate the field on a non-gated arm. The driver enforces
    that gating; this helper only writes the value the caller computed.

    Rebuilds from ``to_dict`` (preserving any already-set optional fields) so the
    result re-validates against the canonical schema — mirrors
    :func:`benchmark.harness.scoring.conformance.judge._with_conformance`.
    """
    payload = report.to_dict()
    payload["gateEscape"] = value
    return ScoreReport.from_dict(payload)


def _failing_selectors(report: ScoreReport) -> tuple[str, ...]:
    """The hidden ``failToPass`` selectors this report records as NOT passing."""
    results = report.failToPassResults
    if not isinstance(results, Mapping):
        return ()
    return tuple(selector for selector, passed in results.items() if not passed)


# --- per-task (testTags) attribution -----------------------------------------


def per_task_escapes(
    report: ScoreReport, instance: TaskInstance
) -> tuple[TaskEscape, ...]:
    """Attribute a report's hidden-test failures to ``Done`` tasks via testTags.

    ``instance.testTags`` maps each hidden selector to the spec section/component
    a ``Done`` task claims. A failing selector whose component a task marked
    ``Done`` (the gated workflow produced this scored candidate) is an escape for
    that component. Returns one :class:`TaskEscape` per component with at least
    one failing tagged selector. When the instance carries no ``testTags`` this
    returns ``()`` (the caller falls back to instance granularity).
    """
    tags = instance.testTags
    if not isinstance(tags, Mapping) or not tags:
        return ()

    failing = set(_failing_selectors(report))
    by_component: dict[str, list[str]] = {}
    for selector, component in tags.items():
        if selector in failing:
            by_component.setdefault(component, []).append(selector)

    return tuple(
        TaskEscape(
            trial=report.trial,
            component=component,
            failing_selectors=tuple(sorted(selectors)),
        )
        for component, selectors in sorted(by_component.items())
    )


def _instance_done_units(instance: TaskInstance) -> int:
    """The number of ``Done`` task units an instance exposes via its testTags.

    Each distinct ``testTags`` component is one ``Done`` task unit (the task that
    built that component). Falls back to 1 (the whole instance) when no testTags.
    """
    tags = instance.testTags
    if not isinstance(tags, Mapping) or not tags:
        return 1
    return len(set(tags.values()))


# --- aggregate escape rate ---------------------------------------------------


def escape_rate(
    reports: Iterable[ScoreReport],
    instances_by_trial: Mapping[str, TaskInstance],
) -> EscapeRate:
    """Compute the false-``Done`` escape rate over gated trials' reports.

    Each report's instance (``instances_by_trial[report.trial]``) decides the
    granularity: with ``testTags`` the ``Done`` units are the per-component tasks
    and an escape is a component whose tagged hidden tests fail; without
    ``testTags`` the unit is the whole instance and it escapes iff it is ``Done``
    yet unresolved (:func:`derive_gate_escape`). The rate is escaped units over
    total ``Done`` units across all reports. ``granularity`` is ``task`` when
    EVERY report's instance carried testTags, else ``instance`` (the conservative
    fallback the spec names).
    """
    report_list: Sequence[ScoreReport] = list(reports)

    total = 0
    escaped = 0
    task_escapes: list[TaskEscape] = []
    all_tagged = bool(report_list)

    for report in report_list:
        instance = instances_by_trial.get(report.trial)
        if instance is None:
            raise KeyError(f"no instance for trial {report.trial!r}")
        tags = instance.testTags
        if isinstance(tags, Mapping) and tags:
            total += _instance_done_units(instance)
            escapes = per_task_escapes(report, instance)
            escaped += len(escapes)
            task_escapes.extend(escapes)
        else:
            all_tagged = False
            total += 1
            if derive_gate_escape(report):
                escaped += 1

    rate = escaped / total if total else 0.0
    granularity = GRANULARITY_TASK if all_tagged else GRANULARITY_INSTANCE
    return EscapeRate(
        escaped=escaped,
        total=total,
        rate=rate,
        granularity=granularity,
        task_escapes=tuple(task_escapes),
    )
