"""Injected-defect taxonomy, generation, and catch-rate accounting.

Implements the **gate catch rate** of ``.specs/benchmark/specs/04-metrics.md``
§Bucket 3 and the **injected defects** half of
``.specs/benchmark/specs/06-scoring-and-statistics.md`` §Gate-efficacy probes.

A probe takes a KNOWN-bad patch — a small, classified mutation of a correct
solution — injects it into a gated build, and records whether a gate flagged it
(``InjectedDefect.caughtBy`` set to the gate kind) or it escaped (``caughtBy``
None). The **catch rate** is ``caught / total`` over a set of such defects.

This module is PURE computation:

- :data:`DEFECT_KINDS` is the taxonomy as named constants;
- :data:`DEFECT_MUTATIONS` gives one concrete, classified mutation per kind (a
  ``before -> after`` text substitution a probe applies to a correct solution to
  manufacture a known-bad patch);
- :func:`make_injected_defect` mints an ``InjectedDefect`` record;
- :func:`catch_rate` is the accounting over a set of defects.

The actual injection-into-a-gated-build that POPULATES ``caughtBy`` is the live
part and lives behind an opt-in env in
:mod:`benchmark.harness.scoring.probes.live`.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from benchmark.harness.domain import (
    INJECTED_DEFECT_ID_PREFIX,
    InjectedDefect,
    new_record_id,
)

# --- the defect taxonomy (named constants) ----------------------------------

#: An off-by-one error: a boundary/index/limit shifted by one (e.g. ``<=`` for
#: ``<``, ``n + 1`` for ``n``). The classic fault a careful review should catch.
DEFECT_KIND_OFF_BY_ONE = "off-by-one"

#: A dropped branch: a conditional arm or guard removed, so a case is mishandled
#: (e.g. a stop-word filter or an empty-input guard deleted).
DEFECT_KIND_DROPPED_BRANCH = "dropped-branch"

#: A wrong return: the function returns the wrong value/shape (e.g. returns the
#: input unmodified, or an empty container, instead of the computed result).
DEFECT_KIND_WRONG_RETURN = "wrong-return"

#: The closed defect taxonomy, in a stable order. A probe classifies every
#: injected defect by one of these kinds (``InjectedDefect.defectKind``).
DEFECT_KINDS: tuple[str, ...] = (
    DEFECT_KIND_OFF_BY_ONE,
    DEFECT_KIND_DROPPED_BRANCH,
    DEFECT_KIND_WRONG_RETURN,
)


# --- concrete classified mutations ------------------------------------------


@dataclass(frozen=True)
class DefectMutation:
    """One concrete, classified mutation a probe applies to a correct solution.

    ``defect_kind`` is the taxonomy member; ``component`` is the spec
    section/component the mutation targets (so the live probe can scope its
    injection and the catch can be attributed); ``before`` / ``after`` are the
    exact text substitution that turns a correct solution into the known-bad
    patch (``before`` MUST occur in the target component's correct source).
    ``rationale`` documents why the change is a genuine fault of its kind.
    """

    defect_kind: str
    component: str
    before: str
    after: str
    rationale: str

    def apply(self, source: str) -> str:
        """Return ``source`` with the first ``before`` replaced by ``after``.

        Raises ``ValueError`` when ``before`` is absent — the mutation does not
        apply to this source, so a probe must not silently inject nothing.
        """
        if self.before not in source:
            raise ValueError(
                f"{self.defect_kind} mutation target not found in source: "
                f"{self.before!r}"
            )
        return source.replace(self.before, self.after, 1)


#: One classified mutation per taxonomy kind, targeting a named component of the
#: greenfield ``text_toolkit`` reference solution. Each turns a correct line into
#: a genuine fault of its kind that a correctness gate ought to flag. Kept as a
#: named table so the probe's known-bad patches are auditable and reproducible.
DEFECT_MUTATIONS: tuple[DefectMutation, ...] = (
    DefectMutation(
        defect_kind=DEFECT_KIND_OFF_BY_ONE,
        component="frequency",
        before="return ranked[:limit]",
        after="return ranked[: limit + 1]",
        rationale=(
            "top_terms must return at most `limit` terms; `limit + 1` returns "
            "one too many — an off-by-one on the result bound."
        ),
    ),
    DefectMutation(
        defect_kind=DEFECT_KIND_DROPPED_BRANCH,
        component="normalizer",
        before="return [token for token in folded if token not in _STOP_WORDS]",
        after="return [token for token in folded]",
        rationale=(
            "normalize must drop stop words; removing the stop-word guard keeps "
            "them — a dropped conditional branch."
        ),
    ),
    DefectMutation(
        defect_kind=DEFECT_KIND_WRONG_RETURN,
        component="tokenizer",
        before="return _TOKEN_RE.findall(text)",
        after="return text.split()",
        rationale=(
            "tokenize must split on runs of non-alphanumeric chars and drop "
            "punctuation; returning a bare whitespace split keeps punctuation — "
            "the wrong return value."
        ),
    ),
)


# --- generation --------------------------------------------------------------


def make_injected_defect(
    task_instance: str,
    defect_kind: str,
    *,
    caught_by: str | None = None,
) -> InjectedDefect:
    """Mint an :class:`InjectedDefect` for ``task_instance`` of ``defect_kind``.

    ``defect_kind`` MUST be a member of :data:`DEFECT_KINDS`. ``caught_by`` is
    the gate kind that flagged the defect (set by the live probe) or ``None``
    when it escaped / has not yet been run through the gates.
    """
    if defect_kind not in DEFECT_KINDS:
        raise ValueError(
            f"unknown defectKind {defect_kind!r}; expected one of {DEFECT_KINDS}"
        )
    return InjectedDefect(
        id=new_record_id(INJECTED_DEFECT_ID_PREFIX),
        taskInstance=task_instance,
        defectKind=defect_kind,
        caughtBy=caught_by,
    )


# --- catch-rate accounting ---------------------------------------------------


@dataclass(frozen=True)
class CatchRate:
    """The gate catch-rate accounting over a set of injected defects.

    ``caught`` = defects with ``caughtBy`` set (a gate flagged them); ``total``
    = all defects; ``escaped`` = ``total - caught``; ``rate`` = ``caught /
    total`` (0.0 when ``total == 0``). ``by_kind`` breaks the rate out per
    taxonomy kind so a probe can report which fault classes the gates catch.
    """

    caught: int
    escaped: int
    total: int
    rate: float
    by_kind: dict[str, float]

    @property
    def caught_fraction(self) -> float:
        """Alias for ``rate`` — the true-positive rate the gates achieved."""
        return self.rate


def catch_rate(defects: Iterable[InjectedDefect]) -> CatchRate:
    """Compute the catch rate over ``defects`` (caught / total).

    A defect counts as CAUGHT iff its ``caughtBy`` is set (some gate flagged it);
    otherwise it ESCAPED. The overall rate is ``caught / total`` and the per-kind
    breakdown is the same ratio within each ``defectKind`` present. Pure
    accounting: it reads the ``caughtBy`` field the (live) injection populated.
    """
    items: Sequence[InjectedDefect] = list(defects)
    total = len(items)
    caught = sum(1 for d in items if d.caughtBy is not None)
    escaped = total - caught
    rate = caught / total if total else 0.0

    by_kind: dict[str, float] = {}
    for kind in DEFECT_KINDS:
        kind_items = [d for d in items if d.defectKind == kind]
        if kind_items:
            kind_caught = sum(1 for d in kind_items if d.caughtBy is not None)
            by_kind[kind] = kind_caught / len(kind_items)
    return CatchRate(
        caught=caught,
        escaped=escaped,
        total=total,
        rate=rate,
        by_kind=by_kind,
    )
