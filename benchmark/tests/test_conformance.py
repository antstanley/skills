"""Tests for the rubric-driven spec-conformance judge (task 13).

Non-live by default: every test here injects a DETERMINISTIC mock judge, so no
API call is made and the suite is hermetic. They cover:

- score clamping into ``[0, 1]`` (over- and under-range judge outputs);
- the rubric-prompt builder embeds both the spec and the code;
- ``conformanceScore`` is populated for ALL FIVE arms when the suite supplies a
  spec (greenfield), and left NULL on a no-spec suite (local-fixture);
- the calibration agreement computation on a known sample yields the expected
  figure, and the seeded human-labelled sample clears the resolved threshold;
- a malformed judge response degrades gracefully (raises the judge error, never
  an uncaught parse crash).

The OPT-IN live test (``BENCHMARK_RUN_CONFORMANCE_LIVE=1``, skipped on CI) runs
the REAL bounded ``claude -p`` judge on one saved arm patch, asserts a ``[0, 1]``
score with a non-empty rationale, and SAVES the judgment evidence under
``benchmark/tests/_conformance_live_evidence/`` so the gates inspect it without
re-running the judge.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from benchmark.harness.domain import (
    SCORE_REPORT_ID_PREFIX,
    ScoreReport,
    Suite,
    new_record_id,
)
from benchmark.harness.scoring import (
    MIN_CALIBRATION_AGREEMENT,
    MIN_CALIBRATION_SAMPLE_SIZE,
    ConformanceJudgeError,
    compute_agreement,
    run_calibration,
    score_arm_conformance,
    score_conformance,
    suite_supplies_spec,
)
from benchmark.harness.scoring.conformance import (
    CALIBRATION_SAMPLE,
    SCORE_MAX,
    SCORE_MIN,
    bucket_of,
    build_rubric_prompt,
    clamp_score,
    cohens_kappa,
    parse_judge_response,
)
from benchmark.harness.scoring.conformance.judge import (
    _CODE_HEADER,
    _SPEC_HEADER,
)
from benchmark.suites import local_fixture
from benchmark.suites.greenfield import (
    TEXT_TOOLKIT_SLUG,
    load_instance,
)

# --- helpers ---------------------------------------------------------------

GREENFIELD_SUITE = Suite(
    slug="greenfield-features",
    kind="greenfield",
    oracleConvention="greenfield-hidden-tests",
)
LOCAL_FIXTURE_SUITE = Suite(
    slug="local-fixture",
    kind="local-fixture",
    oracleConvention="local",
)


def _make_report() -> ScoreReport:
    return ScoreReport(
        id=new_record_id(SCORE_REPORT_ID_PREFIX),
        trial=new_record_id("trial"),
        resolved=True,
        regressed=False,
    )


def _mock_judge(score: float, rationale: str = "ok") -> object:
    """A deterministic judge returning a fixed score, ignoring the prompt."""

    def judge(_prompt: str) -> str:
        return json.dumps({"score": score, "rationale": rationale})

    return judge


# --- clamping ---------------------------------------------------------------


def test_clamp_score_bounds():
    assert clamp_score(2.0) == SCORE_MAX
    assert clamp_score(-1.0) == SCORE_MIN
    assert clamp_score(0.42) == 0.42


def test_score_conformance_clamps_over_and_under_range():
    over = score_conformance("spec", "code", judge=_mock_judge(3.5))
    assert over.score == SCORE_MAX
    assert over.raw_score == 3.5  # raw kept for audit

    under = score_conformance("spec", "code", judge=_mock_judge(-2.0))
    assert under.score == SCORE_MIN
    assert under.raw_score == -2.0

    mid = score_conformance("spec", "code", judge=_mock_judge(0.73, "good"))
    assert mid.score == 0.73
    assert mid.rationale == "good"


# --- rubric prompt builder --------------------------------------------------


def test_rubric_prompt_includes_spec_and_code():
    prompt = build_rubric_prompt("THE-SPEC-TEXT", "THE-CODE-DIFF")
    assert "THE-SPEC-TEXT" in prompt
    assert "THE-CODE-DIFF" in prompt
    assert _SPEC_HEADER in prompt
    assert _CODE_HEADER in prompt
    # The rubric's four axes are present.
    assert "Coverage of spec components" in prompt
    assert "API correctness" in prompt
    assert "Behavioural fidelity" in prompt
    assert "No unspecified divergence" in prompt


# --- malformed responses degrade gracefully --------------------------------


@pytest.mark.parametrize(
    "bad",
    [
        "not json at all",
        "{ no closing brace",
        '{"rationale": "missing score"}',
        '{"score": "high"}',  # non-numeric score
        '{"score": true}',  # bool is not a number
        "",
    ],
)
def test_parse_judge_response_raises_on_malformed(bad: str):
    with pytest.raises(ConformanceJudgeError):
        parse_judge_response(bad)


def test_parse_judge_response_recovers_fenced_json():
    raw = 'Here is my verdict:\n```json\n{"score": 0.8, "rationale": "good"}\n```'
    score, rationale = parse_judge_response(raw)
    assert score == 0.8
    assert rationale == "good"


def test_score_conformance_propagates_malformed_judge():
    def bad_judge(_prompt: str) -> str:
        return "garbage, no json"

    with pytest.raises(ConformanceJudgeError):
        score_conformance("spec", "code", judge=bad_judge)


# --- every arm scored on greenfield; null on no-spec suite ------------------


def test_suite_supplies_spec_rule():
    assert suite_supplies_spec(GREENFIELD_SUITE) is True
    assert suite_supplies_spec(LOCAL_FIXTURE_SUITE) is False


@pytest.mark.parametrize("arm", ["A0", "A1", "A2", "A3", "A4"])
def test_conformance_populated_for_every_arm_on_greenfield(arm: str):
    instance = load_instance(TEXT_TOOLKIT_SLUG)
    # Each arm is judged against whatever spec it had; the call site is identical.
    spec_text = instance.problemStatement
    report = score_arm_conformance(
        _make_report(),
        suite=GREENFIELD_SUITE,
        spec_text=spec_text,
        final_code_or_patch=f"<{arm} final code>",
        judge=_mock_judge(0.88),
    )
    assert report.conformanceScore == 0.88, arm
    # Round-trips through the schema (optional field set, not _UNSET).
    assert report.to_dict()["conformanceScore"] == 0.88


def test_conformance_null_on_no_spec_suite():
    report = score_arm_conformance(
        _make_report(),
        suite=LOCAL_FIXTURE_SUITE,
        spec_text=local_fixture.load_instance().problemStatement,
        final_code_or_patch="<any code>",
        judge=_mock_judge(0.5),  # must NOT be consulted
    )
    assert report.conformanceScore is None
    assert report.to_dict()["conformanceScore"] is None


def test_no_spec_suite_does_not_invoke_judge():
    def exploding_judge(_prompt: str) -> str:
        raise AssertionError("judge must not run when the suite supplies no spec")

    report = score_arm_conformance(
        _make_report(),
        suite=LOCAL_FIXTURE_SUITE,
        spec_text="ignored",
        final_code_or_patch="ignored",
        judge=exploding_judge,
    )
    assert report.conformanceScore is None


# --- calibration agreement computation --------------------------------------


def test_bucket_boundaries():
    assert bucket_of(0.0) == "low"
    assert bucket_of(0.33) == "low"
    assert bucket_of(0.34) == "partial"
    assert bucket_of(0.66) == "partial"
    assert bucket_of(0.67) == "high"
    assert bucket_of(1.0) == "high"


def test_compute_agreement_known_sample():
    # 4 of 5 land in the same band; the last disagrees (partial vs high).
    human = [0.0, 0.4, 0.95, 0.95, 0.9]
    judge = [0.05, 0.5, 0.9, 0.8, 0.5]  # last: human high(0.9) vs judge partial(0.5)
    report = compute_agreement(human, judge)
    assert report.n == 5
    assert report.exact_bucket_agreement == pytest.approx(0.8)
    # Perfect agreement gives kappa 1.0; a single band miss lowers it below 1.
    assert report.cohens_kappa < 1.0


def test_compute_agreement_perfect():
    human = [0.1, 0.5, 0.9, 0.95]
    report = compute_agreement(human, list(human))
    assert report.exact_bucket_agreement == 1.0
    assert report.cohens_kappa == pytest.approx(1.0)


def test_cohens_kappa_constant_identical_raters():
    # Both raters always "high": degenerate p_e == 1 → kappa 1.0 by convention.
    assert cohens_kappa(["high", "high"], ["high", "high"]) == 1.0


def test_seeded_sample_size_and_threshold_constants():
    assert len(CALIBRATION_SAMPLE) >= MIN_CALIBRATION_SAMPLE_SIZE
    assert 0.0 < MIN_CALIBRATION_AGREEMENT <= 1.0


def test_run_calibration_on_seeded_sample_with_mock_judge():
    # A mock judge that returns each item's own human label → perfect agreement,
    # exercising the full run_calibration path against the real seeded sample.
    def oracle_judge(prompt: str) -> str:
        for item in CALIBRATION_SAMPLE:
            if item.code in prompt:
                return json.dumps({"score": item.human_label, "rationale": "x"})
        raise AssertionError("prompt did not embed a known sample item's code")

    report = run_calibration(judge=oracle_judge)
    assert report.n == len(CALIBRATION_SAMPLE)
    assert report.exact_bucket_agreement == 1.0
    assert report.meets_threshold


# --- opt-in LIVE judgment ---------------------------------------------------

_LIVE_ENV = "BENCHMARK_RUN_CONFORMANCE_LIVE"
_LIVE_EVIDENCE_DIR = Path(__file__).resolve().parent / "_conformance_live_evidence"


@pytest.mark.skipif(
    os.environ.get(_LIVE_ENV) != "1",
    reason=f"set {_LIVE_ENV}=1 to run the real bounded claude -p conformance judge",
)
def test_live_conformance_judge_on_saved_patch():
    """Run the REAL bounded judge on one saved arm patch; save the evidence."""
    instance = load_instance(TEXT_TOOLKIT_SLUG)
    patch = (
        Path(__file__).resolve().parent
        / "_a2_a3_live_evidence"
        / "a2"
        / "candidate_patch.diff"
    ).read_text(encoding="utf-8")

    result = score_conformance(instance.problemStatement, patch)  # live cli_judge

    assert SCORE_MIN <= result.score <= SCORE_MAX
    assert result.rationale.strip(), "live judge returned an empty rationale"

    _LIVE_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (_LIVE_EVIDENCE_DIR / "judgment.json").write_text(
        json.dumps(
            {
                "instance": TEXT_TOOLKIT_SLUG,
                "arm": "A2",
                "score": result.score,
                "raw_score": result.raw_score,
                "rationale": result.rationale,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
