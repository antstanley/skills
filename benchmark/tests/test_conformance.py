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
    JUDGE_NAME_RUBRIC,
    JUDGE_NAME_SPEC_REVIEWER,
    MIN_CALIBRATION_AGREEMENT,
    MIN_CALIBRATION_SAMPLE_SIZE,
    SPEC_REVIEWER_JUDGE_MAX_BUDGET_USD,
    ConformanceJudgeError,
    compute_agreement,
    run_calibration,
    score_arm_conformance,
    score_conformance,
    spec_reviewer_judge,
    suite_supplies_spec,
)
from benchmark.harness.scoring.conformance import (
    CALIBRATION_SAMPLE,
    SCORE_MAX,
    SCORE_MIN,
    bucket_of,
    build_rubric_prompt,
    build_spec_reviewer_prompt,
    clamp_score,
    cohens_kappa,
    parse_judge_response,
    parse_r2_verdict,
)
from benchmark.harness.scoring.conformance.judge import (
    _CODE_HEADER,
    _R2_VERDICT_TO_SCORE,
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


# --- spec-reviewer-backed judge (R2 mode) ----------------------------------


def _mock_spec_reviewer(
    verdict_label: str,
    *,
    confidence: str = "high",
    summary: str = "looks fine",
) -> object:
    """A deterministic spec-reviewer judge returning a fixed R2 verdict block."""

    response = (
        "P1: The spec page claims X. P2: The code lives in y/. P3: Body-only rule.\n"
        "CLAIM RESOLUTION: ... (worked trace omitted for the mock).\n\n"
        f"VERDICT: {verdict_label}\n"
        f"CONFIDENCE: {confidence}\n"
        f"SUMMARY: {summary}\n"
    )

    def judge(_prompt: str) -> str:
        return response

    return judge


def test_r2_verdict_mapping_constants():
    # The four documented R2 verdict labels are pinned to their named scores.
    assert _R2_VERDICT_TO_SCORE["CONFORMS"] == 1.0
    assert _R2_VERDICT_TO_SCORE["LIKELY_CONFORMS"] == 0.85
    assert _R2_VERDICT_TO_SCORE["CONCERNS"] == 0.5
    assert _R2_VERDICT_TO_SCORE["DIVERGES"] == 0.1
    # The mapping covers exactly the four labels the R2 template defines.
    assert set(_R2_VERDICT_TO_SCORE) == {
        "CONFORMS",
        "LIKELY_CONFORMS",
        "CONCERNS",
        "DIVERGES",
    }


@pytest.mark.parametrize(
    ("label", "expected_score"),
    [
        ("CONFORMS", 1.0),
        ("LIKELY_CONFORMS", 0.85),
        ("CONCERNS", 0.5),
        ("DIVERGES", 0.1),
    ],
)
def test_parse_r2_verdict_maps_each_label(label: str, expected_score: float):
    raw = f"Some prose.\n\nVERDICT: {label}\nCONFIDENCE: medium\nSUMMARY: example.\n"
    score, parsed_label, confidence = parse_r2_verdict(raw)
    assert score == expected_score
    assert parsed_label == label
    assert confidence == "medium"


def test_parse_r2_verdict_uses_last_verdict_line():
    # An earlier quoted template line must NOT shadow the real trailing verdict.
    raw = (
        "Worked example:\n"
        "VERDICT: DIVERGES\n"
        "CONFIDENCE: high\n"
        "SUMMARY: example divergence.\n\n"
        "Now the actual review:\n"
        "VERDICT: CONFORMS\n"
        "CONFIDENCE: high\n"
        "SUMMARY: real review summary.\n"
    )
    score, label, confidence = parse_r2_verdict(raw)
    assert label == "CONFORMS"
    assert score == 1.0
    assert confidence == "high"


def test_parse_r2_verdict_raises_on_missing_verdict_line():
    raw = "Lots of prose and analysis, but no verdict block."
    with pytest.raises(ConformanceJudgeError):
        parse_r2_verdict(raw)


def test_parse_r2_verdict_raises_on_unknown_label():
    # A fabricated / misspelled label must NOT silently default to a score.
    raw = "VERDICT: MAYBE\nCONFIDENCE: low\nSUMMARY: unclear.\n"
    with pytest.raises(ConformanceJudgeError):
        parse_r2_verdict(raw)


def test_build_spec_reviewer_prompt_embeds_inputs_and_names_r2_mode():
    prompt = build_spec_reviewer_prompt("SPEC-TEXT-XYZ", "CODE-DIFF-XYZ")
    assert "SPEC-TEXT-XYZ" in prompt
    assert "CODE-DIFF-XYZ" in prompt
    assert _SPEC_HEADER in prompt
    assert _CODE_HEADER in prompt
    # The prompt explicitly names the spec-reviewer skill and the R2 mode.
    assert "spec-creator:spec-reviewer" in prompt
    assert "R2" in prompt
    # The expected verdict block shape is included as guidance for the model.
    assert "VERDICT:" in prompt
    assert "CONFIDENCE:" in prompt


def test_spec_reviewer_judge_returns_score_and_rationale():
    result = spec_reviewer_judge(
        "the spec",
        "the code",
        judge=_mock_spec_reviewer("LIKELY_CONFORMS", confidence="medium"),
    )
    assert SCORE_MIN <= result.score <= SCORE_MAX
    assert result.score == 0.85
    assert result.raw_score == 0.85
    # The rationale carries the verdict label and the R2 confidence — a reviewer
    # can audit *why* the score landed where it did.
    assert "LIKELY_CONFORMS" in result.rationale
    assert "medium" in result.rationale


@pytest.mark.parametrize(
    ("label", "expected_score"),
    [
        ("CONFORMS", 1.0),
        ("LIKELY_CONFORMS", 0.85),
        ("CONCERNS", 0.5),
        ("DIVERGES", 0.1),
    ],
)
def test_spec_reviewer_judge_maps_each_label(label: str, expected_score: float):
    result = spec_reviewer_judge(
        "spec",
        "code",
        judge=_mock_spec_reviewer(label),
    )
    assert result.score == expected_score
    assert label in result.rationale


def test_spec_reviewer_judge_raises_on_unrecognised_verdict():
    def bad_judge(_prompt: str) -> str:
        return "VERDICT: BANANA\nCONFIDENCE: high\nSUMMARY: nope.\n"

    with pytest.raises(ConformanceJudgeError):
        spec_reviewer_judge("spec", "code", judge=bad_judge)


def test_spec_reviewer_judge_raises_on_missing_verdict():
    def bad_judge(_prompt: str) -> str:
        return "no verdict block here at all"

    with pytest.raises(ConformanceJudgeError):
        spec_reviewer_judge("spec", "code", judge=bad_judge)


def test_spec_reviewer_judge_budget_cap_is_named_constant():
    # The budget cap is a named, auditable constant — not a magic number.
    assert SPEC_REVIEWER_JUDGE_MAX_BUDGET_USD > 0
    assert isinstance(SPEC_REVIEWER_JUDGE_MAX_BUDGET_USD, float)


def test_spec_reviewer_judge_budget_overspend_raises_with_context(monkeypatch):
    """A simulated budget overspend raises ConformanceJudgeError with context.

    Mirrors :func:`test_cli_judge`'s shape for the rubric-direct path: we patch
    ``subprocess.run`` to return a non-zero exit code (the CLI's signal that the
    ``--max-budget-usd`` cap was breached or the call otherwise failed) and assert
    the error message carries enough context (exit code, stdout, stderr) for a
    reviewer to diagnose without re-running.
    """
    from benchmark.harness.scoring.conformance import judge as judge_module

    class _FakeResult:
        returncode = 2
        stdout = ""
        stderr = "budget cap of $3.0 exceeded"

    def fake_run(*_args, **_kwargs):
        return _FakeResult()

    monkeypatch.setattr(judge_module.subprocess, "run", fake_run)

    with pytest.raises(ConformanceJudgeError) as excinfo:
        judge_module.cli_spec_reviewer("any prompt")

    # The error names the budget cap (so a reviewer knows which knob to tune)
    # and includes the stderr (so they can see *why* the cap was breached).
    message = str(excinfo.value)
    assert "max-budget-usd" in message
    assert "budget cap" in message  # from the simulated stderr
    assert "exit 2" in message


# --- dispatcher: score_arm_conformance accepts name strings + callables -----


def test_score_arm_conformance_judge_name_rubric_uses_rubric_path(monkeypatch):
    """The ``"rubric"`` name routes through the rubric-direct path."""
    from benchmark.harness.scoring.conformance import judge as judge_module

    calls: list[str] = []

    def fake_cli_judge(_prompt: str) -> str:
        calls.append("rubric")
        return json.dumps({"score": 0.42, "rationale": "ok"})

    monkeypatch.setattr(judge_module, "cli_judge", fake_cli_judge)

    report = score_arm_conformance(
        _make_report(),
        suite=GREENFIELD_SUITE,
        spec_text="spec",
        final_code_or_patch="code",
        judge=JUDGE_NAME_RUBRIC,
    )
    assert calls == ["rubric"]
    assert report.conformanceScore == 0.42


def test_score_arm_conformance_judge_name_spec_reviewer_uses_r2_path(monkeypatch):
    """The ``"spec-reviewer"`` name routes through the spec-reviewer-backed path."""
    from benchmark.harness.scoring.conformance import judge as judge_module

    calls: list[str] = []

    def fake_cli_spec_reviewer(_prompt: str) -> str:
        calls.append("spec-reviewer")
        return "VERDICT: CONFORMS\nCONFIDENCE: high\nSUMMARY: maps cleanly.\n"

    monkeypatch.setattr(judge_module, "cli_spec_reviewer", fake_cli_spec_reviewer)

    report = score_arm_conformance(
        _make_report(),
        suite=GREENFIELD_SUITE,
        spec_text="spec",
        final_code_or_patch="code",
        judge=JUDGE_NAME_SPEC_REVIEWER,
    )
    assert calls == ["spec-reviewer"]
    # CONFORMS → 1.0 by the named mapping.
    assert report.conformanceScore == 1.0


def test_score_arm_conformance_callable_uses_rubric_path():
    """A callable ``judge=`` is treated as a rubric-direct backend (test seam)."""
    report = score_arm_conformance(
        _make_report(),
        suite=GREENFIELD_SUITE,
        spec_text="spec",
        final_code_or_patch="code",
        judge=_mock_judge(0.61, "callable backend"),
    )
    assert report.conformanceScore == 0.61


def test_score_arm_conformance_unknown_name_raises():
    with pytest.raises(ConformanceJudgeError):
        score_arm_conformance(
            _make_report(),
            suite=GREENFIELD_SUITE,
            spec_text="spec",
            final_code_or_patch="code",
            judge="not-a-real-judge-name",
        )


def test_score_arm_conformance_spec_reviewer_null_on_no_spec_suite():
    """The null-on-no-spec rule applies regardless of the selected judge."""

    def exploding_judge(_prompt: str) -> str:
        raise AssertionError("judge must not run on a no-spec suite")

    # Even when the spec-reviewer-backed path is selected, the judge is NOT
    # invoked on a no-spec suite — the rule is enforced before dispatch.
    report = score_arm_conformance(
        _make_report(),
        suite=LOCAL_FIXTURE_SUITE,
        spec_text="ignored",
        final_code_or_patch="ignored",
        judge=exploding_judge,
    )
    assert report.conformanceScore is None


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


# --- opt-in LIVE spec-reviewer-backed judgment ------------------------------

_SPEC_REVIEWER_LIVE_ENV = "BENCHMARK_RUN_SPEC_REVIEWER_JUDGE_LIVE"


def _extract_spec_text_from_artifact_bundle(bundle: dict) -> str:
    """Recover the spec body from a captured A2 ``artifact_bundle.json``.

    The bundle's ``specArtifacts`` is a list of ``"<path>\\n<body>"`` strings
    (the harness writes the path on the first line, the file body after). We
    join the bodies of every spec artefact in order, so the judge sees the
    same canonical-spec text the arm saw — never a stale stand-in.
    """
    spec_artifacts = bundle.get("specArtifacts") or []
    bodies: list[str] = []
    for item in spec_artifacts:
        # Drop the leading ``<path>\n`` so the judge sees only the spec body.
        _, _, body = str(item).partition("\n")
        bodies.append(body)
    return "\n\n".join(bodies)


@pytest.mark.skipif(
    os.environ.get(_SPEC_REVIEWER_LIVE_ENV) != "1",
    reason=(
        f"set {_SPEC_REVIEWER_LIVE_ENV}=1 to run the real bounded "
        "spec-reviewer-backed conformance judge"
    ),
)
def test_live_spec_reviewer_judge_on_saved_patch_and_artifacts():
    """Run the REAL bounded spec-reviewer-backed judge on a saved A2 patch.

    Loads the captured A2 ``specArtifacts`` (so the judge sees the same canonical
    spec the arm saw) and the saved candidate patch, runs the live
    :func:`spec_reviewer_judge` (which invokes the ``spec-creator:spec-reviewer``
    skill in R2 mode), and SAVES the judgment evidence under
    ``benchmark/tests/_conformance_live_evidence/spec_reviewer_judgment.json`` so
    a reviewer can audit the result without re-spending budget.
    """
    evidence_dir = Path(__file__).resolve().parent / "_a2_a3_live_evidence" / "a2"
    bundle = json.loads((evidence_dir / "artifact_bundle.json").read_text())
    spec_text = _extract_spec_text_from_artifact_bundle(bundle)
    assert spec_text.strip(), "expected non-empty specArtifacts in the saved bundle"

    patch = (evidence_dir / "candidate_patch.diff").read_text(encoding="utf-8")

    result = spec_reviewer_judge(spec_text, patch)  # live cli_spec_reviewer

    assert SCORE_MIN <= result.score <= SCORE_MAX
    assert result.rationale.strip(), "live judge returned an empty rationale"
    # The rationale must carry a recognised R2 verdict label so a reviewer
    # can see *why* the score landed where it did.
    assert any(label in result.rationale for label in _R2_VERDICT_TO_SCORE)

    _LIVE_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (_LIVE_EVIDENCE_DIR / "spec_reviewer_judgment.json").write_text(
        json.dumps(
            {
                "instance": TEXT_TOOLKIT_SLUG,
                "arm": "A2",
                "judge": JUDGE_NAME_SPEC_REVIEWER,
                "score": result.score,
                "raw_score": result.raw_score,
                "rationale": result.rationale,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
