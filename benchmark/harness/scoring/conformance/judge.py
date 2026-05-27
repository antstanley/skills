"""The rubric-driven, host-side LLM conformance judge.

Implements ``06-scoring-and-statistics.md`` §The conformance judge and
``04-metrics.md`` §Bucket 3 (spec conformance): *"a rubric-driven LLM judge
scores how well the final code satisfies the spec, written to
``ScoreReport.conformanceScore`` in ``[0, 1]``."*

Judging procedure — rubric-direct (the documented default)
==========================================================
The spec permits two procedures: where the spec-creator plugin's ``spec-reviewer``
(R2 canonical / R3 change) is available it MAY serve as the judge's procedure;
*"otherwise the judge applies the same conformance rubric directly."* This module
uses the **rubric-direct** path: a SINGLE bounded ``claude -p`` call carrying a
structured conformance rubric (:data:`CONFORMANCE_RUBRIC`) that returns a JSON
``{"score": float, "rationale": str}``. Rubric-direct is the cheaper, more
reproducible default — one focused scoring call, not a recursive ``spec-reviewer``
agent — and the spec explicitly allows it. The rubric itself mirrors the four axes
``spec-reviewer`` mode R2 checks (coverage, correctness, behavioural fidelity, no
unspecified divergence), so the two procedures score against the same bar.

Safety / reproducibility (everything a named constant)
======================================================
- :data:`CONFORMANCE_MODEL` — the fixed model alias the judge runs on.
- :data:`CONFORMANCE_MAX_BUDGET_USD` — a SMALL per-judgment ``--max-budget-usd``
  cap. The judge is one focused rubric-scoring call (NOT a recursive agent), so a
  tiny cap is the right safety rail.
- :data:`JUDGE_TIMEOUT_SECONDS` — wall-clock ceiling for the single call.
- :data:`SCORE_MIN` / :data:`SCORE_MAX` — the ``[0, 1]`` clamp bounds.

The LLM backend is INJECTABLE (a :data:`JudgeCallable`): tests pass a deterministic
mock; :func:`cli_judge` (the real bounded ``claude -p``) is the default. The judge
runs HOST-SIDE — it is the scorer, never the system under test, so it needs no
container and never touches the hidden tests.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass

from benchmark.harness.domain import ScoreReport, Suite

# --- named constants: clamp bounds ------------------------------------------

#: Lower clamp bound for a conformance score (``ScoreReport.conformanceScore``).
SCORE_MIN = 0.0

#: Upper clamp bound for a conformance score.
SCORE_MAX = 1.0

# --- named constants: the bounded host-side claude -p call ------------------

#: Fixed model alias the judge runs on. A focused rubric-scoring call wants a
#: capable-but-cheap model; ``sonnet`` matches the rest of the harness.
CONFORMANCE_MODEL = "sonnet"

#: SMALL hard per-judgment budget ceiling (USD) handed to ``--max-budget-usd``.
#: The judge is ONE focused scoring call, not a recursive agent, so a tiny cap is
#: the honest safety rail against a runaway spend. Named so every caller and test
#: agrees on the bound.
CONFORMANCE_MAX_BUDGET_USD = 1.0

#: Wall-clock ceiling (seconds) for the single ``claude -p`` judging call.
JUDGE_TIMEOUT_SECONDS = 240

#: ``claude`` exit code meaning the headless run completed (mirrors the backends).
_CLAUDE_EXIT_OK = 0

#: Greenfield suite kind: the only suite kind that supplies a spec to judge
#: against (the prose seed is the instance input). Mirrors
#: ``benchmark.harness.domain.SUITE_KINDS``; kept local so the null-on-no-spec rule
#: reads in one place.
_GREENFIELD_SUITE_KIND = "greenfield"

# --- named constant: the structured conformance rubric ----------------------

#: The structured conformance rubric the judge applies. Mirrors the four axes the
#: spec-creator ``spec-reviewer`` (R2) weighs, so the rubric-direct path scores
#: against the same bar as the plugin procedure would. The prompt asks for a single
#: ``[0, 1]`` score and a one-paragraph rationale, returned as strict JSON.
CONFORMANCE_RUBRIC = (
    "You are a strict, impartial spec-conformance judge. You are given a SPEC "
    "(the authority for what the code must do) and the FINAL CODE that an agent "
    "produced to satisfy it. Score how well the code satisfies the spec on a "
    "continuous scale from 0.0 (ignores or contradicts the spec) to 1.0 (fully "
    "and faithfully implements it). Resolution by hidden tests is NOT your "
    "concern — judge fidelity to the SPEC only.\n\n"
    "Weigh these four axes:\n"
    "1. Coverage of spec components: is every component / function / behaviour the "
    "spec calls for actually present in the code?\n"
    "2. API correctness: do the public signatures, names, return shapes, and "
    "re-exports match what the spec specifies?\n"
    "3. Behavioural fidelity: does the code's behaviour (ordering, edge cases, "
    "invariants, error handling) match the spec's stated contract and examples?\n"
    "4. No unspecified divergence: the code does not add behaviour that "
    "contradicts the spec or silently changes a specified contract.\n\n"
    "Be calibrated: 1.0 only for code that satisfies every axis; around 0.5 for "
    "code that implements the core but misses or bends a stated contract; near 0.0 "
    "for code that is absent, stubbed, or contradicts the spec.\n\n"
    "Respond with ONE JSON object and nothing else, exactly this shape:\n"
    '{"score": <number between 0 and 1>, "rationale": "<one short paragraph '
    'citing the axes that drove the score>"}'
)

#: Prompt section headers, named so the prompt-builder and its test agree.
_SPEC_HEADER = "=== SPEC (the authority) ==="
_CODE_HEADER = "=== FINAL CODE (an arm's final implementation / patch) ==="


class ConformanceJudgeError(RuntimeError):
    """Raised when the live judge cannot run or its output cannot be parsed."""


@dataclass(frozen=True)
class ConformanceResult:
    """The judge's verdict for one ``(spec, code)`` pair.

    ``score`` is always CLAMPED into ``[SCORE_MIN, SCORE_MAX]``; ``rationale`` is
    the judge's free-text justification (may be empty if the model omitted one).
    ``raw_score`` keeps the pre-clamp value the judge returned, for auditing.
    """

    score: float
    rationale: str
    raw_score: float


#: An injectable judge backend: given a fully-built rubric prompt, return the raw
#: model response text (expected to be the JSON object the rubric asks for). Tests
#: pass a deterministic mock; :func:`cli_judge` is the live default.
JudgeCallable = Callable[[str], str]


def clamp_score(value: float) -> float:
    """Clamp ``value`` into ``[SCORE_MIN, SCORE_MAX]``."""
    return max(SCORE_MIN, min(SCORE_MAX, value))


def build_rubric_prompt(spec_text: str, final_code: str) -> str:
    """Build the full rubric prompt embedding the spec and the final code.

    The prompt is :data:`CONFORMANCE_RUBRIC` followed by a clearly delimited SPEC
    block and FINAL CODE block, so the judge sees both inputs verbatim.
    """
    return (
        f"{CONFORMANCE_RUBRIC}\n\n"
        f"{_SPEC_HEADER}\n{spec_text}\n\n"
        f"{_CODE_HEADER}\n{final_code}\n"
    )


def parse_judge_response(raw: str) -> tuple[float, str]:
    """Parse a judge response into ``(raw_score, rationale)``, gracefully.

    Tolerant of the model wrapping the JSON in prose or a ```json fence: it scans
    for the first ``{`` and the last ``}`` and parses that span. Raises
    :class:`ConformanceJudgeError` (never an uncaught ``JSONDecodeError`` /
    ``KeyError``) when no JSON object with a numeric ``score`` can be recovered,
    so callers can decide how to degrade.
    """
    text = raw.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ConformanceJudgeError(f"judge response contained no JSON object: {raw!r}")
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ConformanceJudgeError(
            f"judge response was not valid JSON: {raw!r}"
        ) from exc
    if not isinstance(parsed, dict) or "score" not in parsed:
        raise ConformanceJudgeError(f"judge JSON missing a 'score' field: {parsed!r}")
    score = parsed["score"]
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise ConformanceJudgeError(f"judge 'score' was not a number: {score!r}")
    rationale = parsed.get("rationale", "")
    if not isinstance(rationale, str):
        rationale = str(rationale)
    return float(score), rationale


def _shell_quote(value: str) -> str:
    """Single-quote ``value`` for a POSIX ``sh -c`` command line."""
    return "'" + value.replace("'", "'\\''") + "'"


def cli_judge(prompt: str) -> str:
    """The live default judge: ONE bounded host-side ``claude -p`` call.

    Runs ``claude -p <prompt> --model sonnet --max-budget-usd <CAP>
    --output-format json`` on the HOST (the judge is the scorer, not the system
    under test — no container, never sees the hidden tests). Returns the model's
    ``result`` text (the rubric JSON). Raises :class:`ConformanceJudgeError` on a
    non-zero exit or an unparseable CLI envelope; on an auth failure the CLI exits
    non-zero and that surfaces here so the caller can STOP.
    """
    command = (
        f"claude -p {_shell_quote(prompt)} "
        f"--model {CONFORMANCE_MODEL} "
        f"--max-budget-usd {CONFORMANCE_MAX_BUDGET_USD} --output-format json"
    )
    result = subprocess.run(
        ["sh", "-c", command],
        capture_output=True,
        text=True,
        timeout=JUDGE_TIMEOUT_SECONDS,
    )
    if result.returncode != _CLAUDE_EXIT_OK:
        raise ConformanceJudgeError(
            f"conformance judge claude -p failed (exit {result.returncode}).\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    try:
        envelope = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ConformanceJudgeError(
            f"could not parse claude --output-format json envelope:\n{result.stdout}"
        ) from exc
    if not isinstance(envelope, dict) or "result" not in envelope:
        raise ConformanceJudgeError(
            f"claude JSON envelope missing 'result': {envelope!r}"
        )
    inner = envelope["result"]
    if not isinstance(inner, str):
        raise ConformanceJudgeError(f"claude 'result' was not a string: {inner!r}")
    return inner


def score_conformance(
    spec_text: str,
    final_code_or_patch: str,
    *,
    judge: JudgeCallable = cli_judge,
) -> ConformanceResult:
    """Score how well ``final_code_or_patch`` satisfies ``spec_text`` in ``[0, 1]``.

    Builds the rubric prompt, runs it through ``judge`` (the live
    :func:`cli_judge` by default; an injected mock in tests), parses the JSON
    ``{score, rationale}``, and CLAMPS the score into ``[SCORE_MIN, SCORE_MAX]``.
    Returns a :class:`ConformanceResult`. Propagates
    :class:`ConformanceJudgeError` if the judge cannot run or its output cannot be
    parsed — the caller decides whether to leave the score null.
    """
    prompt = build_rubric_prompt(spec_text, final_code_or_patch)
    raw = judge(prompt)
    raw_score, rationale = parse_judge_response(raw)
    return ConformanceResult(
        score=clamp_score(raw_score),
        rationale=rationale,
        raw_score=raw_score,
    )


def suite_supplies_spec(suite: Suite) -> bool:
    """Whether ``suite`` supplies a spec to judge conformance against.

    Per ``04-metrics.md`` §Bucket 3, spec conformance is scored *"on the greenfield
    suite"* — the prose spec seed is the instance input there. Other suite kinds
    (e.g. ``local-fixture``, a bug-fix oracle) supply no spec, so conformance is
    left null on them.
    """
    return suite.kind == _GREENFIELD_SUITE_KIND


def score_arm_conformance(
    report: ScoreReport,
    *,
    suite: Suite,
    spec_text: str,
    final_code_or_patch: str,
    judge: JudgeCallable = cli_judge,
) -> ScoreReport:
    """Return a copy of ``report`` with ``conformanceScore`` populated (or null).

    The null-on-no-spec rule: if ``suite`` supplies no spec
    (:func:`suite_supplies_spec` is False), the returned report has
    ``conformanceScore = None`` and the judge is NOT invoked. Otherwise the judge
    scores ``(spec_text, final_code_or_patch)`` and the clamped score is written
    onto a new ``ScoreReport`` (the inputs are frozen dataclasses, so this returns
    a fresh record rather than mutating).

    This is the per-arm entry point: ``spec_text`` is whatever spec that arm is
    judged against — the instance ``problemStatement`` (the prose seed) for A0/A4,
    A1's authored spec captured in its ``specArtifacts``, or the frozen given-spec
    handed to A2/A3 — judged identically by the same rubric (``04-metrics.md``
    §Bucket 3: *"even A0 and A4 are judged against it, and A1's authored spec (or
    the spec handed to A2 and A3) is judged the same way"*).
    """
    if not suite_supplies_spec(suite):
        return _with_conformance(report, None)
    result = score_conformance(spec_text, final_code_or_patch, judge=judge)
    return _with_conformance(report, result.score)


def _with_conformance(report: ScoreReport, score: float | None) -> ScoreReport:
    """Return a new ``ScoreReport`` equal to ``report`` but with ``conformanceScore``.

    Rebuilds from ``to_dict`` (preserving any already-set optional fields) so the
    result re-validates against the canonical schema.
    """
    payload = report.to_dict()
    payload["conformanceScore"] = score
    return ScoreReport.from_dict(payload)
