"""Calibration harness for the conformance judge.

The judge is *"not taken on faith. It is calibrated against human labels on a
sample of trials, and its score is reported with a stated agreement figure against
those labels."* (``06-scoring-and-statistics.md`` §The conformance judge.) This
module supplies (1) a SMALL, hand-authored human-labelled sample drawn from the
saved live-arm patches, each label authored to the same rubric the judge applies;
(2) an agreement computation that buckets continuous scores and reports both
exact-bucket agreement and Cohen's kappa; and (3) a runner that scores the sample
with a given judge and returns the agreement figure.

Agreement metric (documented choice)
====================================
Continuous ``[0, 1]`` scores are bucketed into three conformance bands —
``low`` ``[0, 0.34)``, ``partial`` ``[0.34, 0.67)``, ``high`` ``[0.67, 1.0]`` —
and agreement is the FRACTION of items where the judge's band equals the human's
band (exact-bucket agreement), reported alongside **Cohen's kappa** on the same
bands (kappa corrects for chance agreement, the honest figure for a tiny sample).
Buckets are used because a continuous judge score and a human label will rarely be
bit-identical, but a *band* disagreement (e.g. the judge says "high" where a human
says "low") is the meaningful miscalibration.

Honesty about sample size
=========================
The seeded sample is DELIBERATELY SMALL (the saved live-arm patches for the one
``text_toolkit`` self-test instance). The resolved threshold below is set modestly
to match. A production-grade calibration needs a much larger human-labelled sample
spanning many instances and arms; this seed proves the mechanism and reports an
honest figure, not a publishable agreement statistic.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from benchmark.harness.scoring.conformance.judge import (
    JudgeCallable,
    cli_judge,
    score_conformance,
)
from benchmark.suites.greenfield import (
    TEXT_TOOLKIT_PROBLEM_STATEMENT,
    TEXT_TOOLKIT_SLUG,
)

# --- named constants: bucketing + the resolved calibration threshold --------

#: Band boundaries for bucketing a continuous ``[0, 1]`` score. A score ``s`` is
#: ``"low"`` if ``s < LOW_BAND_MAX``, ``"high"`` if ``s >= HIGH_BAND_MIN``, else
#: ``"partial"``. Three bands keep the agreement test robust to the inevitable
#: small numeric gap between a human label and a judge score.
LOW_BAND_MAX = 0.34
HIGH_BAND_MIN = 0.67

#: The ordered conformance bands (used as the kappa category set).
BANDS: tuple[str, ...] = ("low", "partial", "high")

#: RESOLVED calibration Open question (documented honestly given the tiny seed):
#: the conformance score is reportable when the calibration sample has at least
#: :data:`MIN_CALIBRATION_SAMPLE_SIZE` human-labelled items AND the judge's
#: exact-bucket agreement is at least :data:`MIN_CALIBRATION_AGREEMENT`. These are
#: MODEST on purpose — a small seed cannot support a strong claim. A production
#: calibration would raise both substantially over a larger, multi-instance sample.
MIN_CALIBRATION_SAMPLE_SIZE = 4
MIN_CALIBRATION_AGREEMENT = 0.75


@dataclass(frozen=True)
class CalibrationItem:
    """One human-labelled calibration item.

    ``spec_text`` and ``code`` are the judge inputs; ``human_label`` is a
    hand-authored conformance score in ``[0, 1]`` (the human's verdict, authored to
    the same rubric the judge applies); ``rationale`` is the one-line justification
    documenting WHY a human assigned that label.
    """

    name: str
    spec_text: str
    code: str
    human_label: float
    rationale: str


@dataclass(frozen=True)
class AgreementReport:
    """The computed agreement between judge scores and human labels."""

    n: int
    exact_bucket_agreement: float
    cohens_kappa: float
    judge_scores: tuple[float, ...]
    human_labels: tuple[float, ...]
    judge_bands: tuple[str, ...]
    human_bands: tuple[str, ...]

    @property
    def meets_threshold(self) -> bool:
        """Whether this report clears the resolved sample-size + agreement bar."""
        return (
            self.n >= MIN_CALIBRATION_SAMPLE_SIZE
            and self.exact_bucket_agreement >= MIN_CALIBRATION_AGREEMENT
        )


def bucket_of(score: float) -> str:
    """Map a continuous ``[0, 1]`` score to its conformance band."""
    if score < LOW_BAND_MAX:
        return "low"
    if score >= HIGH_BAND_MIN:
        return "high"
    return "partial"


def cohens_kappa(a_bands: Sequence[str], b_bands: Sequence[str]) -> float:
    """Cohen's kappa between two band sequences over :data:`BANDS`.

    ``kappa = (p_o - p_e) / (1 - p_e)`` where ``p_o`` is observed agreement and
    ``p_e`` is the chance agreement from each rater's marginal band frequencies.
    Returns ``1.0`` when both raters are constant and identical (``p_e == 1``); the
    standard degenerate convention.
    """
    if len(a_bands) != len(b_bands):
        raise ValueError("band sequences must be the same length")
    n = len(a_bands)
    if n == 0:
        raise ValueError("cannot compute kappa over an empty sample")
    p_o = sum(1 for x, y in zip(a_bands, b_bands, strict=True) if x == y) / n
    p_e = 0.0
    for band in BANDS:
        a_freq = sum(1 for x in a_bands if x == band) / n
        b_freq = sum(1 for y in b_bands if y == band) / n
        p_e += a_freq * b_freq
    if p_e >= 1.0:
        return 1.0
    return (p_o - p_e) / (1.0 - p_e)


def compute_agreement(
    human_labels: Sequence[float], judge_scores: Sequence[float]
) -> AgreementReport:
    """Compute the agreement report from paired human labels and judge scores."""
    if len(human_labels) != len(judge_scores):
        raise ValueError("human_labels and judge_scores must be the same length")
    n = len(human_labels)
    if n == 0:
        raise ValueError("cannot compute agreement over an empty sample")
    human_bands = tuple(bucket_of(s) for s in human_labels)
    judge_bands = tuple(bucket_of(s) for s in judge_scores)
    exact = sum(1 for h, j in zip(human_bands, judge_bands, strict=True) if h == j) / n
    return AgreementReport(
        n=n,
        exact_bucket_agreement=exact,
        cohens_kappa=cohens_kappa(human_bands, judge_bands),
        judge_scores=tuple(judge_scores),
        human_labels=tuple(human_labels),
        judge_bands=judge_bands,
        human_bands=human_bands,
    )


def run_calibration(
    sample: Sequence[CalibrationItem] = (),
    *,
    judge: JudgeCallable = cli_judge,
) -> AgreementReport:
    """Score ``sample`` with ``judge`` and return the agreement against human labels.

    Defaults to the seeded :data:`CALIBRATION_SAMPLE`. ``judge`` is the live
    :func:`cli_judge` by default; tests inject a deterministic mock.
    """
    items = tuple(sample) if sample else CALIBRATION_SAMPLE
    judge_scores = [
        score_conformance(item.spec_text, item.code, judge=judge).score
        for item in items
    ]
    human_labels = [item.human_label for item in items]
    return compute_agreement(human_labels, judge_scores)


# --- the seeded human-labelled sample ---------------------------------------

_EVIDENCE_DIR = Path(__file__).resolve().parents[3] / "tests"


def _load_patch(*relative: str) -> str:
    """Read a saved live-arm candidate patch from ``benchmark/tests/``."""
    return (_EVIDENCE_DIR.joinpath(*relative)).read_text(encoding="utf-8")


#: A small, fully stubbed (no-op) patch standing in for an arm that produced no
#: real implementation — anchors the ``low`` band. Authored inline (not a saved
#: arm) because every saved live arm happened to fully implement the spec, so a
#: genuine low-conformance exemplar is needed to span the label range honestly.
_EMPTY_IMPLEMENTATION = (
    "diff --git a/text_toolkit/tokenizer.py b/text_toolkit/tokenizer.py\n"
    "(no changes — every component is still the unimplemented "
    "NotImplementedError stub)\n"
)

#: A1's saved candidate patch implements ONLY the tokenizer (the other three
#: components are still stubs in this saved evidence), so it is a genuine PARTIAL
#: implementation of the four-component spec — an honest ``partial``-band anchor.
_A1_PARTIAL = _load_patch("_a1_live_evidence", "candidate_patch.diff")

#: A2, A3, and A4's saved patches each implement all four components faithfully
#: (tokenizer, normalizer, frequency, pipeline), matching the spec's contracts,
#: ordering, and examples — ``high``-band anchors.
_A2_FULL = _load_patch("_a2_a3_live_evidence", "a2", "candidate_patch.diff")
_A3_FULL = _load_patch("_a2_a3_live_evidence", "a3", "candidate_patch.diff")
_A4_FULL = _load_patch("_a4_live_evidence", "candidate_patch.diff")

assert TEXT_TOOLKIT_SLUG  # referenced for provenance; the sample is this instance.

#: The seeded human-labelled calibration sample. FIVE items spanning the band
#: range. Each ``human_label`` + ``rationale`` is hand-authored against
#: :data:`benchmark.harness.scoring.conformance.judge.CONFORMANCE_RUBRIC`. Honest
#: about its size: one instance, five exemplars — enough to prove the mechanism and
#: report a real (if modest) agreement figure, not a publishable statistic.
CALIBRATION_SAMPLE: tuple[CalibrationItem, ...] = (
    CalibrationItem(
        name="empty-stub",
        spec_text=TEXT_TOOLKIT_PROBLEM_STATEMENT,
        code=_EMPTY_IMPLEMENTATION,
        human_label=0.0,
        rationale=(
            "No component implemented — every function still raises "
            "NotImplementedError; ignores the spec entirely (low)."
        ),
    ),
    CalibrationItem(
        name="a1-tokenizer-only",
        spec_text=TEXT_TOOLKIT_PROBLEM_STATEMENT,
        code=_A1_PARTIAL,
        human_label=0.4,
        rationale=(
            "Implements only the tokenizer faithfully; normalizer, frequency, "
            "and pipeline are absent from the patch — core started but most of "
            "the four-component spec is unmet (partial)."
        ),
    ),
    CalibrationItem(
        name="a2-full",
        spec_text=TEXT_TOOLKIT_PROBLEM_STATEMENT,
        code=_A2_FULL,
        human_label=0.95,
        rationale=(
            "All four components implemented; composition, stop-word set, "
            "count-desc/term-asc ordering, and the summarize envelope all match "
            "the spec's contracts and examples (high)."
        ),
    ),
    CalibrationItem(
        name="a3-full",
        spec_text=TEXT_TOOLKIT_PROBLEM_STATEMENT,
        code=_A3_FULL,
        human_label=0.95,
        rationale=(
            "Full four-component implementation with the STOP_WORDS frozenset, "
            "ordered top_terms, and the correct summarize shape — faithful to the "
            "spec throughout (high)."
        ),
    ),
    CalibrationItem(
        name="a4-full",
        spec_text=TEXT_TOOLKIT_PROBLEM_STATEMENT,
        code=_A4_FULL,
        human_label=0.9,
        rationale=(
            "All four components present and behaviourally faithful; uses a local "
            "stop-word set rather than the spec's named STOP_WORDS constant, a "
            "minor API divergence that keeps it just inside the high band."
        ),
    ),
)
