"""Gate-probe tests: catch rate, escape rate, GateEvent threading, live probe.

Covers ``benchmark.harness.scoring.probes`` and the GateEvent threading in
``benchmark.harness.driver.scheduler``:

- **Catch rate** with synthetic ``InjectedDefect``s (some caught, some escaped)
  -> the expected rate + per-kind breakdown.
- **Escape rate** on synthetic gated trials: a Done-but-unresolved trial is an
  escape, with per-task ``testTags`` attribution AND the instance-granularity
  fallback when testTags are absent; plus the captured A1 evidence.
- **GateEvent threading**: a run backend that surfaces ``last_gate_events`` has
  its events re-keyed onto the TrialResult and aggregated on the CampaignRun.
- **The OPT-IN live probe** (``BENCHMARK_RUN_GATE_PROBE_LIVE=1``): the real
  inject -> review-gate -> caughtBy path on a small bounded sample. The
  mapping/mutation mechanics are tested NON-LIVE with an injected reviewer.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from benchmark.harness.arms.a2_a3 import GATE_KIND_REVIEW
from benchmark.harness.domain import (
    GATE_EVENT_ID_PREFIX,
    SCORE_REPORT_ID_PREFIX,
    TRIAL_ID_PREFIX,
    GateEvent,
    ScoreReport,
    TaskInstance,
    new_record_id,
)
from benchmark.harness.driver import run_campaign
from benchmark.harness.scoring.probes import (
    DEFECT_KIND_DROPPED_BRANCH,
    DEFECT_KIND_OFF_BY_ONE,
    DEFECT_KIND_WRONG_RETURN,
    DEFECT_MUTATIONS,
    LIVE_PROBE_ENV,
    catch_rate,
    derive_gate_escape,
    escape_rate,
    make_injected_defect,
    per_task_escapes,
)
from benchmark.harness.scoring.probes.live import (
    build_review_prompt,
    run_gate_probe,
    verdict_caught,
)
from benchmark.suites.greenfield import (
    TEXT_TOOLKIT_SLUG,
    load_instance,
    load_reference_solution,
)

# ---------------------------------------------------------------------------
# Catch rate
# ---------------------------------------------------------------------------


def test_catch_rate_counts_caught_and_escaped() -> None:
    # Three caught (caughtBy set), two escaped (None) -> 3/5.
    defects = [
        make_injected_defect(
            "inst", DEFECT_KIND_OFF_BY_ONE, caught_by="semi-formal-review"
        ),
        make_injected_defect("inst", DEFECT_KIND_OFF_BY_ONE, caught_by=None),
        make_injected_defect(
            "inst", DEFECT_KIND_DROPPED_BRANCH, caught_by="semi-formal-review"
        ),
        make_injected_defect(
            "inst", DEFECT_KIND_WRONG_RETURN, caught_by="semi-formal-review"
        ),
        make_injected_defect("inst", DEFECT_KIND_WRONG_RETURN, caught_by=None),
    ]
    result = catch_rate(defects)
    assert result.total == 5
    assert result.caught == 3
    assert result.escaped == 2
    assert result.rate == 3 / 5
    # Per-kind: off-by-one 1/2, dropped-branch 1/1, wrong-return 1/2.
    assert result.by_kind[DEFECT_KIND_OFF_BY_ONE] == 0.5
    assert result.by_kind[DEFECT_KIND_DROPPED_BRANCH] == 1.0
    assert result.by_kind[DEFECT_KIND_WRONG_RETURN] == 0.5


def test_catch_rate_empty_is_zero() -> None:
    result = catch_rate([])
    assert result.total == 0
    assert result.rate == 0.0
    assert result.by_kind == {}


def test_make_injected_defect_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError, match="unknown defectKind"):
        make_injected_defect("inst", "not-a-kind")


def test_defect_mutations_cover_the_whole_taxonomy() -> None:
    kinds = {m.defect_kind for m in DEFECT_MUTATIONS}
    assert kinds == {
        DEFECT_KIND_OFF_BY_ONE,
        DEFECT_KIND_DROPPED_BRANCH,
        DEFECT_KIND_WRONG_RETURN,
    }


# ---------------------------------------------------------------------------
# Escape rate
# ---------------------------------------------------------------------------


def _instance_with_tags(tags: dict[str, str] | None) -> TaskInstance:
    return TaskInstance(
        slug="greenfield__demo__0001",
        suite="greenfield-features",
        repo="demo",
        baseCommit="0" * 40,
        problemStatement="demo",
        failToPass=list(tags or {"hidden/test_x.py::t": "x"}),
        passToPass=[],
        contaminationTier="authored-private",
        headlessVerifiable=True,
        testTags=tags,
    )


def _report(trial: str, *, resolved: bool, f2p: dict[str, bool]) -> ScoreReport:
    return ScoreReport(
        id=new_record_id(SCORE_REPORT_ID_PREFIX),
        trial=trial,
        resolved=resolved,
        regressed=False,
        failToPassResults=f2p,
    )


def _trial_id() -> str:
    return new_record_id(TRIAL_ID_PREFIX)


def test_derive_gate_escape_is_done_but_unresolved() -> None:
    # A gated, scored trial that is NOT resolved escaped (gates passed it Done).
    t = _trial_id()
    assert derive_gate_escape(_report(t, resolved=False, f2p={})) is True
    assert derive_gate_escape(_report(t, resolved=True, f2p={})) is False


def test_per_task_escapes_attributes_failures_via_testtags() -> None:
    tags = {
        "hidden/test_tok.py::a": "tokenizer",
        "hidden/test_tok.py::b": "tokenizer",
        "hidden/test_norm.py::c": "normalizer",
    }
    instance = _instance_with_tags(tags)
    report = _report(
        _trial_id(),
        resolved=False,
        f2p={
            "hidden/test_tok.py::a": True,  # passes
            "hidden/test_tok.py::b": False,  # fails -> tokenizer escape
            "hidden/test_norm.py::c": False,  # fails -> normalizer escape
        },
    )
    escapes = per_task_escapes(report, instance)
    components = {e.component for e in escapes}
    assert components == {"tokenizer", "normalizer"}
    tok = next(e for e in escapes if e.component == "tokenizer")
    assert tok.failing_selectors == ("hidden/test_tok.py::b",)


def test_escape_rate_per_task_granularity() -> None:
    # 3 Done units (3 distinct components), 2 escape -> 2/3, task granularity.
    tags = {
        "hidden/t.py::a": "tokenizer",
        "hidden/n.py::b": "normalizer",
        "hidden/f.py::c": "frequency",
    }
    instance = _instance_with_tags(tags)
    t = _trial_id()
    report = _report(
        t,
        resolved=False,
        f2p={
            "hidden/t.py::a": True,  # tokenizer holds
            "hidden/n.py::b": False,  # normalizer escapes
            "hidden/f.py::c": False,  # frequency escapes
        },
    )
    result = escape_rate([report], {t: instance})
    assert result.granularity == "task"
    assert result.total == 3
    assert result.escaped == 2
    assert result.rate == 2 / 3


def test_escape_rate_instance_granularity_fallback() -> None:
    # No testTags -> instance-granularity: one Done unit, escapes iff unresolved.
    instance = _instance_with_tags(None)
    t1, t2 = _trial_id(), _trial_id()
    escaped_report = _report(t1, resolved=False, f2p={})
    held_report = _report(t2, resolved=True, f2p={})
    instances = {t1: instance, t2: _instance_with_tags(None)}
    result = escape_rate([escaped_report, held_report], instances)
    assert result.granularity == "instance"
    assert result.total == 2
    assert result.escaped == 1
    assert result.rate == 0.5


def test_escape_rate_on_captured_a1_evidence() -> None:
    instance = load_instance(TEXT_TOOLKIT_SLUG)
    report = ScoreReport.from_dict(
        json.loads(
            (
                Path(__file__).resolve().parent
                / "_a1_live_evidence"
                / "score_report.json"
            ).read_text(encoding="utf-8")
        )
    )
    result = escape_rate([report], {report.trial: instance})
    # The captured A1 trial reached an integration tip (Done) but only the
    # tokenizer tests pass; frequency, normalizer, and pipeline tests fail ->
    # 3 of the 4 Done component-tasks escaped.
    assert result.granularity == "task"
    assert result.total == 4
    assert result.escaped == 3
    assert result.rate == 0.75


# ---------------------------------------------------------------------------
# GateEvent threading (the deferred tasks-08/10 wiring)
# ---------------------------------------------------------------------------


class _StubRunBackend:
    """A run backend that surfaces gate events on ``last_gate_events``."""

    def __init__(self, gate_events: list[GateEvent]) -> None:
        self._events = gate_events
        self.telemetry_calls = 0

    @property
    def last_gate_events(self) -> list[GateEvent]:
        return list(self._events)

    def run(self, instance, arm_or_solver):  # noqa: ANN001, ANN201
        from benchmark.harness.domain import (
            ARTIFACT_BUNDLE_ID_PREFIX,
            ArtifactBundle,
            Telemetry,
        )

        bundle = ArtifactBundle(
            id=new_record_id(ARTIFACT_BUNDLE_ID_PREFIX),
            trial=new_record_id(TRIAL_ID_PREFIX),
            telemetry=Telemetry(
                inputTokens=1,
                outputTokens=1,
                costUsd=0.0,
                wallClockSeconds=0.0,
                agentTurns=1,
            ),
        )
        return bundle, "diff"


class _StubScoringBackend:
    def score(self, instance, candidate_patch):  # noqa: ANN001, ANN201
        return ScoreReport(
            id=new_record_id(SCORE_REPORT_ID_PREFIX),
            trial=new_record_id(TRIAL_ID_PREFIX),
            resolved=True,
            regressed=False,
        )


def _campaign_arm_instance():
    from benchmark.harness.arms.a2_a3 import A2
    from benchmark.harness.domain import CAMPAIGN_ID_PREFIX, Campaign

    campaign = Campaign(
        id=new_record_id(CAMPAIGN_ID_PREFIX),
        createdAt="2026-05-27T00:00:00+00:00",
        model="sonnet",
        arms=["A2"],
        suites=["greenfield-features"],
        trialsPerInstance=1,
    )
    instance = _instance_with_tags({"hidden/t.py::a": "tokenizer"})
    return campaign, A2, instance


def test_gate_events_thread_onto_the_trial_result() -> None:
    backend_internal_id = new_record_id(TRIAL_ID_PREFIX)
    event = GateEvent(
        id=new_record_id(GATE_EVENT_ID_PREFIX),
        trial=backend_internal_id,
        task="01-tokenizer",
        gateKind=GATE_KIND_REVIEW,
        verdict="PASS",
        retryIndex=0,
    )
    run_backend = _StubRunBackend([event])
    campaign, arm, instance = _campaign_arm_instance()

    run = run_campaign(campaign, [arm], [instance], run_backend, _StubScoringBackend())

    # The single trial carried the run's gate event, re-keyed onto its trial id.
    [result] = run.results
    assert len(result.gate_events) == 1
    threaded = result.gate_events[0]
    assert threaded.task == "01-tokenizer"
    assert threaded.gateKind == GATE_KIND_REVIEW
    # The event was re-keyed from the backend's internal id onto the driver's
    # Trial id (the tasks-08/10 wiring).
    assert threaded.trial == result.trial.id
    assert threaded.trial != backend_internal_id
    # The CampaignRun aggregates all threaded events.
    assert run.gate_events == list(result.gate_events)


def test_backend_without_gate_events_threads_none() -> None:
    run_backend = _StubRunBackend([])
    campaign, arm, instance = _campaign_arm_instance()
    run = run_campaign(campaign, [arm], [instance], run_backend, _StubScoringBackend())
    [result] = run.results
    assert result.gate_events == ()
    assert run.gate_events == []


# ---------------------------------------------------------------------------
# Live probe — mechanics non-live, the real call opt-in
# ---------------------------------------------------------------------------


def test_verdict_caught_maps_verdicts() -> None:
    assert verdict_caught("reasoning...\nVERDICT: BUGGY") is True
    assert verdict_caught("VERDICT: CONCERNS") is True
    assert verdict_caught("VERDICT: CORRECT") is False
    assert verdict_caught("VERDICT: LIKELY_CORRECT") is False
    # No parseable verdict -> conservatively NOT caught.
    assert verdict_caught("the model said nothing useful") is False


def test_run_gate_probe_sets_caughtby_with_injected_reviewer() -> None:
    mutation = DEFECT_MUTATIONS[0]
    caught = run_gate_probe(
        "inst", "diff text", mutation, reviewer=lambda _p: "VERDICT: BUGGY"
    )
    assert caught.caughtBy == GATE_KIND_REVIEW
    assert caught.defectKind == mutation.defect_kind

    escaped = run_gate_probe(
        "inst", "diff text", mutation, reviewer=lambda _p: "VERDICT: CORRECT"
    )
    assert escaped.caughtBy is None


def test_build_review_prompt_carries_diff_and_verdict_contract() -> None:
    mutation = DEFECT_MUTATIONS[0]
    prompt = build_review_prompt("a-diff", mutation)
    assert "a-diff" in prompt
    assert "VERDICT" in prompt
    assert mutation.component in prompt
    # The prompt must NOT name the injected fault (the gate finds it unaided).
    assert mutation.rationale not in prompt


def test_defect_mutations_apply_to_the_reference_solution() -> None:
    # The mutation targets are added lines of the reference solution: applying
    # them to the post-diff source manufactures a genuine known-bad source.
    ref = load_reference_solution(TEXT_TOOLKIT_SLUG)
    added = "\n".join(
        line[1:]
        for line in ref.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    for mutation in DEFECT_MUTATIONS:
        mutated = mutation.apply(added)
        assert mutated != added
        assert mutation.after in mutated


# --- the OPT-IN live probe ---------------------------------------------------

_LIVE_EVIDENCE = Path(__file__).resolve().parent / "_gate_probe_live_evidence"


@pytest.mark.skipif(
    os.environ.get(LIVE_PROBE_ENV) != "1",
    reason=f"set {LIVE_PROBE_ENV}=1 to run the real bounded inject->gate probe",
)
def test_live_gate_probe_on_one_injected_defect() -> None:
    """Run ONE real bounded review gate on a defect-injected diff; save evidence.

    Bounded: a SINGLE small ``claude -p`` call. Demonstrates the live
    inject -> gate -> ``caughtBy`` path on one defect of the taxonomy.
    """
    ref = load_reference_solution(TEXT_TOOLKIT_SLUG)
    added = "\n".join(
        line[1:]
        for line in ref.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    mutation = DEFECT_MUTATIONS[0]
    bad_diff = (
        f"--- a/{mutation.component}.py\n+++ b/{mutation.component}.py\n"
        f"-{mutation.before}\n+{mutation.after}\n"
    )
    assert mutation.before in added  # the mutation truly targets the solution

    defect = run_gate_probe(TEXT_TOOLKIT_SLUG, bad_diff, mutation)  # live cli gate

    _LIVE_EVIDENCE.mkdir(parents=True, exist_ok=True)
    (_LIVE_EVIDENCE / "defect.json").write_text(
        json.dumps(
            {
                "instance": TEXT_TOOLKIT_SLUG,
                "defectKind": defect.defectKind,
                "caughtBy": defect.caughtBy,
                "component": mutation.component,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    # The probe produced a well-formed verdict either way; record which.
    assert defect.defectKind == mutation.defect_kind
    assert defect.caughtBy in (None, GATE_KIND_REVIEW)
