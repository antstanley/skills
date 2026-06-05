"""Tests for the A2 / A3 arms — plan + build from a HANDED-IN spec.

A2 (``02-arms.md`` §A2) and A3 (§A3) are configuration variants of A1: the
``spec-creator`` stage is replaced by a FROZEN given-spec written into the
container, and A3 additionally disables ``spec-builder``'s two gates. The
container backend routes A1/A2/A3 to ONE parameterized workflow path
(``_run_workflow_arm``) that differs only by the arm's ``_WorkflowArmConfig``.

These tests assert (non-gated, no API/Docker):

- the A2/A3 arm records are configured correctly (A2 gates on + spec provided;
  A3 gates off + spec provided; NEITHER enables spec-creator);
- dispatch routes A2/A3 to the WORKFLOW path (not the plain-A0 path) BY SLUG;
- the GateEvent-extraction logic yields events for a gates-on (discharged)
  certificate capture and NONE for a gates-off (blank) capture — the observable
  gate difference;
- the frozen given-spec loader returns the checked-in asset for both instances.

The LIVE test (``BENCHMARK_RUN_A2_A3_LIVE=1``, skipped on CI) runs ONE bounded
A2 and ONE bounded A3 on the seed instance through the driver +
``ContainerScoringBackend``, asserting both produce scored patches and A2 emits
GateEvents while A3 emits none. Its evidence is SAVED so the gates inspect it
without re-running the expensive workflow.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

from benchmark.harness.arms.a1 import A1, HOST_PLUGIN_MARKETPLACE_DIR
from benchmark.harness.arms.a2_a3 import (
    A2,
    A2_A3_MAX_BUDGET_USD,
    A2_A3_PLUGIN_DIR_NAMES,
    A3,
    GATE_KIND_REVIEW,
    GATE_KIND_VALIDATE,
    GIVEN_SPEC_QUALITY_BAR,
    a2_prompt,
    a3_prompt,
    extract_gate_events,
)
from benchmark.harness.backends import ContainerRunBackend, RunBackend
from benchmark.harness.backends.container import (
    _WORKFLOW_ARM_SLUGS,
    HOST_CREDENTIALS_PATH,
    _workflow_config_for,
)
from benchmark.harness.domain import GATE_VERDICTS, Arm, ArtifactBundle, Campaign
from benchmark.harness.driver import run_campaign
from benchmark.harness.scoring import ContainerScoringBackend
from benchmark.suites import greenfield_images as images
from benchmark.suites.greenfield import (
    SCHEDULER_SLUG,
    TEXT_TOOLKIT_SLUG,
    load_given_spec,
    load_instance,
)

# --- gating ----------------------------------------------------------------

_DOCKER_UP = images.docker_available()
_CREDS_PRESENT = HOST_CREDENTIALS_PATH.is_file()
_PLUGINS_PRESENT = all(
    (HOST_PLUGIN_MARKETPLACE_DIR / name / ".claude-plugin" / "plugin.json").is_file()
    for name in A2_A3_PLUGIN_DIR_NAMES
)

#: Opt-in env var gating the LIVE A2+A3 runs. Two RECURSIVE workflow runs spend
#: real (user-authorized) budget capped at ``A2_A3_MAX_BUDGET_USD`` each; this
#: must NOT fire on a routine ``check.sh`` / CI pass. Reviewers inspect the SAVED
#: evidence under :data:`LIVE_EVIDENCE_DIR` instead of paying to re-run.
_A2_A3_LIVE_OPT_IN_ENV = "BENCHMARK_RUN_A2_A3_LIVE"
_A2_A3_LIVE_OPT_IN = os.environ.get(_A2_A3_LIVE_OPT_IN_ENV) == "1"

_skip_no_live = pytest.mark.skipif(
    not (_A2_A3_LIVE_OPT_IN and _DOCKER_UP and _CREDS_PRESENT and _PLUGINS_PRESENT),
    reason=(
        f"LIVE A2/A3 runs need {_A2_A3_LIVE_OPT_IN_ENV}=1 (two recursive runs "
        "spend real budget) + Docker + host claude credentials + spec-* plugins"
    ),
)

#: Where the live test SAVES its evidence (per-arm patch, score report, captured
#: artifacts incl. certificates, telemetry, cost, transcript, and the extracted
#: GateEvents) so a reviewer can confirm the gate difference WITHOUT re-running.
LIVE_EVIDENCE_DIR = Path(__file__).resolve().parent / "_a2_a3_live_evidence"


# --- non-gated: the A2 / A3 arm records ------------------------------------


def test_a2_arm_is_plan_build_with_spec_handed_in() -> None:
    """A2: planner+builder, gates ON, spec PROVIDED, structured parallel."""
    assert A2.slug == "A2"
    assert A2.pluginsEnabled == ["spec-planner", "spec-builder"]
    assert A2.gatesEnabled is True
    assert A2.specProvided is True
    assert A2.executionMode == "parallel-structured"


def test_a3_arm_is_a2_without_gates() -> None:
    """A3: IDENTICAL to A2 except gates OFF (the only behavioural difference)."""
    assert A3.slug == "A3"
    assert A3.pluginsEnabled == ["spec-planner", "spec-builder"]
    assert A3.gatesEnabled is False
    assert A3.specProvided is True
    assert A3.executionMode == "parallel-structured"
    # A3 differs from A2 in EXACTLY ONE field: gatesEnabled.
    differing = {
        f
        for f in ("pluginsEnabled", "specProvided", "executionMode", "gatesEnabled")
        if getattr(A2, f) != getattr(A3, f)
    }
    assert differing == {"gatesEnabled"}


def test_neither_a2_nor_a3_enables_spec_creator() -> None:
    """Spec authoring is removed for both arms (the spec is handed in)."""
    assert "spec-creator" not in A2.pluginsEnabled
    assert "spec-creator" not in A3.pluginsEnabled
    assert "spec-creator" not in A2_A3_PLUGIN_DIR_NAMES


def test_a2_a3_arms_round_trip_through_the_schema() -> None:
    assert Arm.from_dict(A2.to_dict()) == A2
    assert Arm.from_dict(A3.to_dict()) == A3


def test_a2_prompt_skips_creator_and_references_the_given_spec() -> None:
    instance = load_instance(TEXT_TOOLKIT_SLUG)
    prompt = a2_prompt(instance.problemStatement)
    assert instance.problemStatement in prompt
    assert "spec-creator" in prompt  # ...but only to say NOT to run it
    assert "do NOT run spec-creator" in prompt or "Do NOT author a new" in prompt
    assert "spec-planner" in prompt
    assert "spec-builder" in prompt
    # Gates ON: the prompt instructs running both gates.
    assert "semi-formal" in prompt
    assert "validate-done-certificate" in prompt


def test_a3_prompt_disables_the_two_gates() -> None:
    instance = load_instance(TEXT_TOOLKIT_SLUG)
    prompt = a3_prompt(instance.problemStatement)
    assert "spec-planner" in prompt
    assert "spec-builder" in prompt
    # Gates OFF: the prompt instructs NOT running the gates.
    assert "DISABLE" in prompt or "do NOT run" in prompt
    assert "self-report" in prompt


# --- non-gated: arm dispatch (workflow path, not plain-A0) ------------------


def test_a2_a3_select_the_workflow_path() -> None:
    assert ContainerRunBackend._selects_workflow(A2) is True
    assert ContainerRunBackend._selects_workflow(A3) is True
    assert {A2.slug, A3.slug} <= _WORKFLOW_ARM_SLUGS


def test_a2_a3_do_not_select_the_plain_agent_path() -> None:
    """A2/A3 must NOT fall into the plain-A0 path (the bug the slug routing fixes)."""
    assert ContainerRunBackend._selects_agent(A2) is False
    assert ContainerRunBackend._selects_agent(A3) is False


def test_a0_still_routes_to_the_agent_path_not_the_workflow() -> None:
    from benchmark.harness.arms.a0 import A0

    assert ContainerRunBackend._selects_workflow(A0) is False
    assert ContainerRunBackend._selects_agent(A0) is True


def test_workflow_config_differs_only_in_the_isolated_variables() -> None:
    """A1/A2/A3 configs differ only in: creator-spec, gates (the isolated vars)."""
    a1c = _workflow_config_for(A1)
    a2c = _workflow_config_for(A2)
    a3c = _workflow_config_for(A3)
    # A1 authors its spec; A2/A3 are handed one.
    assert a1c.provides_given_spec is False
    assert a2c.provides_given_spec is True and a3c.provides_given_spec is True
    # A1/A2 gate; A3 does not.
    assert a1c.gates_enabled is True and a2c.gates_enabled is True
    assert a3c.gates_enabled is False
    # A2 and A3 share everything but the gates.
    assert a2c.plugin_dir_names == a3c.plugin_dir_names
    assert a2c.model == a3c.model
    assert a2c.max_budget_usd == a3c.max_budget_usd
    assert a2c.provides_given_spec == a3c.provides_given_spec
    assert a2c.gates_enabled != a3c.gates_enabled


def test_backend_still_satisfies_run_protocol() -> None:
    assert isinstance(ContainerRunBackend(), RunBackend)


# --- non-gated: the frozen given-spec loader --------------------------------


def test_given_spec_loader_returns_the_frozen_asset() -> None:
    """Both instances ship a frozen given-spec at the documented quality bar."""
    for slug in (TEXT_TOOLKIT_SLUG, SCHEDULER_SLUG):
        spec = load_given_spec(slug)
        assert isinstance(spec, str) and spec.strip() != ""
        assert "Given Spec" in spec
        # The bar: overview, components/contracts, and a definition of done.
        assert "## 1. Overview" in spec
        assert "Definition of done" in spec or "definition of done" in spec.lower()
        # Frozen + shared-by-both-arms is stated in the asset itself.
        assert "A2" in spec and "A3" in spec


def test_given_spec_is_identical_bytes_for_both_arms() -> None:
    """A2 and A3 consume the SAME asset, so spec variance cannot leak in."""
    # The loader is arm-agnostic; the same slug yields the same bytes regardless
    # of which arm reads it (there is no per-arm spec).
    first = load_given_spec(TEXT_TOOLKIT_SLUG)
    second = load_given_spec(TEXT_TOOLKIT_SLUG)
    assert first == second


def test_quality_bar_is_documented() -> None:
    assert "frozen" in GIVEN_SPEC_QUALITY_BAR.lower()
    assert "identically" in GIVEN_SPEC_QUALITY_BAR.lower()


# --- non-gated: GateEvent extraction (the observable gate difference) --------

_TRIAL_ID = "trial_00000000-0000-7000-8000-000000000001"


def _capture_entry(relpath: str, body: str) -> str:
    """A captured certificate bundle entry: ``"<relpath>\\n<contents>"``."""
    return f"{relpath}\n{body}"


_GATES_ON_CAPTURE = [
    _capture_entry(
        ".specs/plans/2026-05-27-x/certificates/01-tokenizer.md",
        "# Done Certificate — Task 01\n\n"
        "**Status:** Validated 2026-05-27\n\n"
        "## Conclusion\n\nVERDICT: DONE\nState: Validated 2026-05-27\n",
    ),
    _capture_entry(
        ".specs/plans/2026-05-27-x/certificates/02-normalizer.md",
        "# Done Certificate — Task 02\n\n"
        "## Semi-formal review\n\nVERDICT: CORRECT confidence 0.9\n\n"
        "## Conclusion\n\nVERDICT: PARTIAL\nState: Validated 2026-05-27\n",
    ),
]

_GATES_OFF_CAPTURE = [
    _capture_entry(
        ".specs/plans/2026-05-27-x/certificates/01-tokenizer.md",
        "# Done Certificate — Task 01\n\n"
        "**Status:** Pending validation\n\n"
        "**Verdict:** (blank — to be filled by validating agent)\n",
    ),
    _capture_entry(
        ".specs/plans/2026-05-27-x/certificates/02-normalizer.md",
        "# Done Certificate — Task 02\n\n"
        "**Status:** Pending validation\n\n"
        "**Verdict:** (blank — to be filled by validating agent)\n",
    ),
]


def test_gate_events_extracted_from_a_gates_on_capture() -> None:
    """A2 (gates on): discharged certificates yield >= 1 typed GateEvent."""
    events = extract_gate_events(_GATES_ON_CAPTURE, trial_id=_TRIAL_ID)
    assert len(events) >= 1
    for ev in events:
        assert ev.trial == _TRIAL_ID
        assert ev.gateKind in (GATE_KIND_VALIDATE, GATE_KIND_REVIEW)
        assert ev.verdict in GATE_VERDICTS
        assert ev.retryIndex == 0
    # The first cert's validate verdict DONE maps onto PASS.
    validate_events = [e for e in events if e.gateKind == GATE_KIND_VALIDATE]
    assert any(e.verdict == "PASS" for e in validate_events)
    # The second cert carries BOTH a review verdict and a validate verdict.
    by_task = {e.task for e in events}
    assert "01-tokenizer" in by_task
    assert "02-normalizer" in by_task
    review_events = [e for e in events if e.gateKind == GATE_KIND_REVIEW]
    assert any(e.verdict == "PASS" for e in review_events)  # CORRECT -> PASS


#: The REAL live shape captured from an A2 recursive run: the discharged
#: ``validate-done-certificate`` gate writes a ``## Verdict`` heading and a
#: MARKDOWN-BOLD label line ``**VERDICT:** DONE`` (not the bare ``VERDICT:
#: DONE`` the older unit fixtures use). This block reproduces that capture so
#: the parser is exercised against the bytes the live gate actually emits.
_LIVE_BOLD_VERDICT_CAPTURE = [
    _capture_entry(
        ".specs/plans/2026-05-29-x/certificates/01-tokenizer.md",
        "# Done Certificate — Task 01\n\n"
        "**Status:** Validated 2026-05-29\n\n"
        "## Verdict\n\n**VERDICT:** DONE\n\n"
        "State: Validated 2026-05-29\n",
    ),
]


def test_markdown_bold_verdict_line_yields_one_pass_event() -> None:
    """The REAL live cert shape ``**VERDICT:** DONE`` (markdown-bold label,
    under a ``## Verdict`` heading) yields exactly ONE validate GateEvent mapped
    to PASS. Before the label-emphasis tolerance the bold ``**`` between the
    colon and ``DONE`` defeated the regex, so a live discharged certificate
    parsed to NO gate event and A2 falsely looked ungated."""
    events = extract_gate_events(_LIVE_BOLD_VERDICT_CAPTURE, trial_id=_TRIAL_ID)
    assert len(events) == 1  # one validate event, no double-count
    (event,) = events
    assert event.gateKind == GATE_KIND_VALIDATE
    assert event.verdict == "PASS"  # DONE -> PASS
    assert event.verdict in GATE_VERDICTS
    assert event.task == "01-tokenizer"


def test_bare_verdict_line_still_yields_one_pass_event() -> None:
    """No regression: the bare ``VERDICT: DONE`` shape (no markdown emphasis)
    still yields exactly one validate PASS GateEvent."""
    cap = [
        _capture_entry(
            ".specs/plans/p/certificates/01-x.md",
            "## Conclusion\n\nVERDICT: DONE\nState: Validated 2026-05-29\n",
        ),
    ]
    events = extract_gate_events(cap, trial_id=_TRIAL_ID)
    assert len(events) == 1
    (event,) = events
    assert event.gateKind == GATE_KIND_VALIDATE
    assert event.verdict == "PASS"


def test_italic_emphasis_verdict_line_maps_to_partial() -> None:
    """Italic emphasis (``*VERDICT:* PARTIAL``) is also tolerated and maps the
    validate verdict PARTIAL onto the closed enum's PARTIAL."""
    cap = [
        _capture_entry(
            ".specs/plans/p/certificates/02-y.md",
            "## Verdict\n\n*VERDICT:* PARTIAL\n",
        ),
    ]
    events = extract_gate_events(cap, trial_id=_TRIAL_ID)
    assert len(events) == 1
    (event,) = events
    assert event.gateKind == GATE_KIND_VALIDATE
    assert event.verdict == "PARTIAL"
    assert event.verdict in GATE_VERDICTS


def test_no_gate_events_from_a_gates_off_capture() -> None:
    """A3 (gates off): blank/undischarged certificates yield NO GateEvent."""
    events = extract_gate_events(_GATES_OFF_CAPTURE, trial_id=_TRIAL_ID)
    assert events == []


def test_no_gate_events_from_an_empty_capture() -> None:
    assert extract_gate_events([], trial_id=_TRIAL_ID) == []


def test_review_verdict_mapping_onto_the_closed_enum() -> None:
    """BUGGY -> FAIL, CONCERNS -> PARTIAL, NOT_DONE -> FAIL (all in the enum)."""
    cap = [
        _capture_entry(
            ".specs/plans/p/certificates/03-x.md",
            "## review\nVERDICT: BUGGY\n## Conclusion\nVERDICT: NOT_DONE\n",
        ),
        _capture_entry(
            ".specs/plans/p/certificates/04-y.md",
            "## review\nVERDICT: CONCERNS\n",
        ),
    ]
    events = extract_gate_events(cap, trial_id=_TRIAL_ID)
    verdicts = {(e.gateKind, e.verdict) for e in events}
    assert (GATE_KIND_VALIDATE, "FAIL") in verdicts  # NOT_DONE -> FAIL
    assert (GATE_KIND_REVIEW, "FAIL") in verdicts  # BUGGY -> FAIL
    assert (GATE_KIND_REVIEW, "PARTIAL") in verdicts  # CONCERNS -> PARTIAL
    assert all(v in GATE_VERDICTS for _, v in verdicts)


def test_unverified_validate_verdict_is_the_manual_pause_signal() -> None:
    """A parked-for-human certificate (``VERDICT: UNVERIFIED``) yields exactly one
    UNVERIFIED validate GateEvent — the signal the manual-pause-rate metric counts
    (``04-metrics.md`` → Bucket 4). Before this, the extractor dropped it, leaving
    the metric structurally always-zero."""
    cap = [
        _capture_entry(
            ".specs/plans/p/certificates/05-ui-dashboard.md",
            "# Done Certificate — Task 05\n\n"
            "## Conclusion\n\nVERDICT: UNVERIFIED\n"
            "State: parked for human sign-off (UI-bound task)\n",
        ),
    ]
    events = extract_gate_events(cap, trial_id=_TRIAL_ID)
    assert len(events) == 1  # one event, not double-counted by the review map
    (event,) = events
    assert event.gateKind == GATE_KIND_VALIDATE
    assert event.verdict == "UNVERIFIED"
    assert event.verdict in GATE_VERDICTS
    assert event.task == "05-ui-dashboard"


def test_backend_last_gate_events_starts_empty() -> None:
    """Before any workflow run, the backend exposes no gate events."""
    assert ContainerRunBackend().last_gate_events == []


# --- LIVE: one bounded A2 + one bounded A3 run through the driver -----------


def _apply_check(patch: str, run_image_tag: str) -> subprocess.CompletedProcess[str]:
    """``git apply --check`` the CODE patch against a FRESH base checkout."""
    command = (
        f"set -e; cd {images.IMAGE_WORKDIR}; "
        "git init -q; git add -A; "
        "git -c user.email=t@t -c user.name=t commit -q -m base; "
        "git apply --check -"
    )
    return subprocess.run(
        ["docker", "run", "--rm", "-i", run_image_tag, "sh", "-c", command],
        input=patch,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _run_one_arm(arm: Arm, instance, evidence_subdir: str) -> tuple[object, list]:
    """Run ONE bounded arm through the driver; save evidence; return result+events."""
    campaign = Campaign(
        id="camp_00000000-0000-7000-8000-000000000010",
        createdAt="2026-05-27T00:00:00+00:00",
        model="sonnet",
        arms=[arm.slug],
        suites=[instance.suite],
        trialsPerInstance=1,
        backend="container",
        solver="agent",
    )
    run_backend = ContainerRunBackend()
    scoring_backend = ContainerScoringBackend()

    started = time.monotonic()
    campaign_run = run_campaign(
        campaign,
        arms=[arm],
        instances=[instance],
        run_backend=run_backend,
        scoring_backend=scoring_backend,
        pool_size=1,
    )
    wall_clock = time.monotonic() - started
    assert len(campaign_run.results) == 1
    result = campaign_run.results[0]
    gate_events = run_backend.last_gate_events

    out = LIVE_EVIDENCE_DIR / evidence_subdir
    out.mkdir(parents=True, exist_ok=True)
    patch = result.trial.candidatePatch
    bundle = result.bundle
    report = result.report
    (out / "candidate_patch.diff").write_text(patch or "")
    if bundle is not None:
        (out / "artifact_bundle.json").write_text(
            json.dumps(bundle.to_dict(), indent=2, sort_keys=True)
        )
        if bundle.transcript is not None:
            (out / "transcript.json").write_text(bundle.transcript)
    if report is not None:
        (out / "score_report.json").write_text(
            json.dumps(report.to_dict(), indent=2, sort_keys=True)
        )
    (out / "gate_events.json").write_text(
        json.dumps([e.to_dict() for e in gate_events], indent=2, sort_keys=True)
    )
    (out / "run_summary.json").write_text(
        json.dumps(
            {
                "arm": arm.slug,
                "gates_enabled": arm.gatesEnabled,
                "spec_provided": arm.specProvided,
                "trial_status": result.trial.status,
                "fault": result.fault,
                "wall_clock_seconds": wall_clock,
                "cost_usd": (bundle.telemetry.costUsd if bundle is not None else None),
                "resolved": report.resolved if report is not None else None,
                "regressed": report.regressed if report is not None else None,
                "gate_event_count": len(gate_events),
                "certificate_artifact_count": (
                    len(bundle.certificateArtifacts)
                    if bundle is not None and bundle.certificateArtifacts is not None
                    else 0
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return result, gate_events


@_skip_no_live
def test_live_a2_emits_gate_events_and_a3_emits_none() -> None:
    """LIVE: bounded A2 (gates on) + A3 (gates off) on the seed instance.

    Both run end to end through ``run_campaign`` + the container backends (the
    production path). Asserts both produce a scored, apply-able CODE patch and
    that A2 emits >= 1 GateEvent while A3 emits none — the observable gate
    difference. ALL evidence is saved under :data:`LIVE_EVIDENCE_DIR` for review.
    """
    instance = load_instance(TEXT_TOOLKIT_SLUG)

    a2_result, a2_events = _run_one_arm(A2, instance, "a2")
    a3_result, a3_events = _run_one_arm(A3, instance, "a3")

    for result in (a2_result, a3_result):
        assert not result.is_failed, f"workflow hit an infra fault: {result.fault}"
        bundle = result.bundle
        assert isinstance(bundle, ArtifactBundle)
        assert bundle.telemetry.costUsd <= A2_A3_MAX_BUDGET_USD
        patch = result.trial.candidatePatch
        assert isinstance(patch, str) and patch.strip() != ""
        run_tag = images.build_run_image(images.get_spec(TEXT_TOOLKIT_SLUG))
        check = _apply_check(patch, run_tag)
        assert check.returncode == 0, f"patch did not apply:\n{check.stderr}"
        assert result.report is not None

    # The observable gate difference: A2 discharges certificates (>= 1 event);
    # A3 disables the gates (no event).
    assert len(a2_events) >= 1
    assert a3_events == []
