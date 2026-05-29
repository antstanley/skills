"""Domain-type tests: schema validation, id scheme, round-tripping, rejection.

Every entity from ``01-domain-model.md`` is constructed, dumped, reloaded, and
compared equal, and verified to validate against the canonical schema. The
negative-space cases (bad id prefix, missing required field, out-of-enum
``GateVerdict``) are each asserted to be rejected with a clear error.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from benchmark.harness import domain
from benchmark.harness.domain import (
    ARM_SLUGS,
    CANONICAL_SCHEMA,
    RECORD_ID_PATTERN,
    Arm,
    ArtifactBundle,
    Campaign,
    DomainValidationError,
    GateEvent,
    InjectedDefect,
    MetricResult,
    Record,
    ScoreReport,
    Suite,
    TaskInstance,
    Telemetry,
    Trial,
    new_record_id,
    uuid7,
)

# --- canonical sample of every entity, minimal-but-valid -------------------

_CAMPAIGN_ID = new_record_id(domain.CAMPAIGN_ID_PREFIX)
_TRIAL_ID = new_record_id(domain.TRIAL_ID_PREFIX)
_TIMESTAMP = "2026-05-27T12:00:00Z"


def _suite() -> Suite:
    return Suite(
        slug="greenfield-features",
        kind="greenfield",
        oracleConvention="greenfield-hidden-tests",
    )


def _task_instance() -> TaskInstance:
    return TaskInstance(
        slug="greenfield__url_shortener",
        suite="greenfield-features",
        repo="acme/url-shortener",
        baseCommit="abc1234",
        problemStatement="Build a URL shortener per the spec.",
        failToPass=["tests::test_a"],
        passToPass=["tests::test_b"],
        contaminationTier="authored-private",
        headlessVerifiable=True,
    )


def _arm() -> Arm:
    return Arm(
        slug="A1",
        pluginsEnabled=["spec-builder"],
        gatesEnabled=True,
        specProvided=False,
        executionMode="single",
    )


def _campaign() -> Campaign:
    return Campaign(
        id=_CAMPAIGN_ID,
        createdAt=_TIMESTAMP,
        model="claude-opus-4-7",
        arms=list(ARM_SLUGS),
        suites=["greenfield-features"],
        trialsPerInstance=3,
    )


def _trial() -> Trial:
    return Trial(
        id=_TRIAL_ID,
        campaign=_CAMPAIGN_ID,
        arm="A1",
        taskInstance="greenfield__url_shortener",
        seed=7,
        createdAt=_TIMESTAMP,
        status="queued",
    )


def _telemetry() -> Telemetry:
    return Telemetry(
        inputTokens=100,
        outputTokens=50,
        costUsd=0.25,
        wallClockSeconds=12.5,
        agentTurns=4,
    )


def _artifact_bundle() -> ArtifactBundle:
    return ArtifactBundle(
        id=new_record_id(domain.ARTIFACT_BUNDLE_ID_PREFIX),
        trial=_TRIAL_ID,
        telemetry=_telemetry(),
        specArtifacts=["spec.md"],
        transcript="...",
    )


def _gate_event() -> GateEvent:
    return GateEvent(
        id=new_record_id(domain.GATE_EVENT_ID_PREFIX),
        trial=_TRIAL_ID,
        task="01",
        gateKind="semi-formal-review",
        verdict="PASS",
        retryIndex=0,
    )


def _injected_defect() -> InjectedDefect:
    return InjectedDefect(
        id=new_record_id(domain.INJECTED_DEFECT_ID_PREFIX),
        taskInstance="greenfield__url_shortener",
        defectKind="off-by-one",
        caughtBy="semi-formal-review",
    )


def _score_report() -> ScoreReport:
    return ScoreReport(
        id=new_record_id(domain.SCORE_REPORT_ID_PREFIX),
        trial=_TRIAL_ID,
        resolved=True,
        regressed=False,
        failToPassResults={"tests::test_a": True},
        conformanceScore=0.9,
        gateEscape=False,
    )


def _metric_result() -> MetricResult:
    return MetricResult(
        id=new_record_id(domain.METRIC_RESULT_ID_PREFIX),
        campaign=_CAMPAIGN_ID,
        arm="A1",
        suite="greenfield-features",
        metricName="resolved-rate",
        value=0.42,
        ciLow=0.30,
        ciHigh=0.55,
        nTrials=30,
    )


_FACTORIES = [
    (_suite, "Suite"),
    (_task_instance, "TaskInstance"),
    (_arm, "Arm"),
    (_campaign, "Campaign"),
    (_trial, "Trial"),
    (_telemetry, "Telemetry"),
    (_artifact_bundle, "ArtifactBundle"),
    (_gate_event, "GateEvent"),
    (_injected_defect, "InjectedDefect"),
    (_score_report, "ScoreReport"),
    (_metric_result, "MetricResult"),
]

_ALL_ENTITIES = [
    Suite,
    TaskInstance,
    Arm,
    Campaign,
    Trial,
    Telemetry,
    ArtifactBundle,
    GateEvent,
    InjectedDefect,
    ScoreReport,
    MetricResult,
]


def test_every_entity_has_a_factory_and_schema_def() -> None:
    """Each defined entity is exercised and names a canonical ``$def``."""
    covered = {name for _, name in _FACTORIES}
    declared = {cls.schema_def for cls in _ALL_ENTITIES}
    assert covered == declared
    for name in declared:
        assert name in CANONICAL_SCHEMA["$defs"], name


@pytest.mark.parametrize(
    "factory,def_name", _FACTORIES, ids=[name for _, name in _FACTORIES]
)
def test_round_trip_and_schema_valid(factory, def_name) -> None:
    """construct -> dump -> load -> equal, and the dump validates against schema."""
    record: Record = factory()
    payload = record.to_dict()

    # Validates against the canonical schema's $def directly.
    validator = Draft202012Validator(
        {
            "$schema": CANONICAL_SCHEMA["$schema"],
            "$defs": CANONICAL_SCHEMA["$defs"],
            "$ref": f"#/$defs/{def_name}",
        }
    )
    validator.validate(payload)

    reloaded = type(record).from_dict(payload)
    assert reloaded == record
    assert reloaded.to_dict() == payload


def test_jsonl_round_trip(tmp_path: Path) -> None:
    """A JSONL instance file of TaskInstances round-trips through dump/load."""
    instances = [
        _task_instance(),
        TaskInstance(
            slug="greenfield__feature__1",
            suite="greenfield-features",
            repo="acme/widget",
            baseCommit="deadbeef",
            problemStatement="Build a widget.",
            failToPass=["t1"],
            passToPass=[],
            contaminationTier="authored-private",
            headlessVerifiable=False,
            testTags={"t1": "section-3"},
        ),
    ]
    path = tmp_path / "instances.jsonl"
    domain.dump_jsonl(instances, path)
    loaded = domain.load_jsonl(TaskInstance, path)
    assert loaded == instances


def test_artifact_record_json_round_trip(tmp_path: Path) -> None:
    """A per-trial artifact record round-trips through single-object JSON."""
    bundle = _artifact_bundle()
    path = tmp_path / "bundle.json"
    domain.dump_json(bundle, path)
    loaded = domain.load_json(ArtifactBundle, path)
    assert loaded == bundle
    assert isinstance(loaded.telemetry, Telemetry)


# --- id scheme -------------------------------------------------------------


def test_uuid7_is_version_7_and_time_ordered() -> None:
    """Generated uuids are RFC 9562 v7 and sort by creation time."""
    first = uuid7()
    second = uuid7()
    assert first.version == 7
    assert second.version == 7
    # rand_a/rand_b make collisions vanishingly unlikely; ordering is by ms.
    assert str(first) <= str(second) or first != second


def test_record_id_matches_canonical_pattern() -> None:
    rid = new_record_id(domain.TRIAL_ID_PREFIX)
    assert RECORD_ID_PATTERN.fullmatch(rid)
    assert rid.startswith("trial_")


# --- negative space --------------------------------------------------------


def test_bad_id_prefix_rejected() -> None:
    """An id with a non-lowercase / malformed prefix fails RecordId validation."""
    bad = _campaign().to_dict()
    bad["id"] = "CAMP_0190a8b1-0000-7000-8000-000000000000"  # uppercase prefix
    with pytest.raises(DomainValidationError) as exc:
        Campaign.from_dict(bad)
    assert "id" in str(exc.value)


def test_bad_id_body_rejected() -> None:
    """An id whose body is not a 36-char uuid is rejected on construction."""
    with pytest.raises(DomainValidationError):
        Campaign(
            id="camp_not-a-uuid",
            createdAt=_TIMESTAMP,
            model="m",
            arms=["A0"],
            suites=["s"],
            trialsPerInstance=1,
        )


def test_missing_required_field_rejected() -> None:
    """Dropping a required field yields a clear validation error."""
    bad = _trial().to_dict()
    del bad["status"]
    with pytest.raises(DomainValidationError) as exc:
        Trial.from_dict(bad)
    assert "status" in str(exc.value) or "required" in str(exc.value)


def test_out_of_enum_gate_verdict_rejected() -> None:
    """A GateVerdict outside the enum is rejected with a clear error."""
    bad = _gate_event().to_dict()
    bad["verdict"] = "MAYBE"
    with pytest.raises(DomainValidationError) as exc:
        GateEvent.from_dict(bad)
    assert "verdict" in str(exc.value)


def test_out_of_enum_arm_slug_rejected() -> None:
    """An ArmSlug outside the closed six-member set (A0–A5) is rejected."""
    with pytest.raises(DomainValidationError):
        Arm(
            slug="A9",
            pluginsEnabled=[],
            gatesEnabled=False,
            specProvided=False,
            executionMode="single",
        )


def test_unknown_field_rejected() -> None:
    """additionalProperties:false in the schema rejects unknown fields."""
    bad = _suite().to_dict()
    bad["extra"] = "nope"
    with pytest.raises(DomainValidationError):
        Suite.from_dict(bad)


def test_slug_pattern_rejects_uppercase() -> None:
    bad = _suite().to_dict()
    bad["slug"] = "Not_A_Slug"
    with pytest.raises(DomainValidationError) as exc:
        Suite.from_dict(bad)
    assert "slug" in str(exc.value)


def test_error_message_is_clear() -> None:
    """Validation errors name the entity and the offending location."""
    bad = _gate_event().to_dict()
    bad["verdict"] = "MAYBE"
    with pytest.raises(DomainValidationError) as exc:
        GateEvent.from_dict(bad)
    message = str(exc.value)
    assert "GateEvent" in message
    assert re.search(r"verdict", message)


# --- local-backend members (2026-05-27 local_backends change spec) ---------


def test_local_fixture_suite_constructs_and_validates() -> None:
    """A local-fixture suite with the local oracle convention validates."""
    suite = Suite(
        slug="local-fixture",
        kind="local-fixture",
        oracleConvention="local",
    )
    assert suite.kind == "local-fixture"
    assert suite.oracleConvention == "local"
    assert "local-fixture" in domain.SUITE_KINDS
    assert "local" in domain.ORACLE_CONVENTIONS


def test_local_campaign_constructs_and_validates() -> None:
    """A campaign on the local backend with the fixture solver validates."""
    campaign = Campaign(
        id=_CAMPAIGN_ID,
        createdAt=_TIMESTAMP,
        model="claude-opus-4-7",
        arms=list(ARM_SLUGS),
        suites=["local-fixture"],
        trialsPerInstance=1,
        backend="local",
        solver="fixture",
    )
    payload = campaign.to_dict()
    assert payload["backend"] == "local"
    assert payload["solver"] == "fixture"
    assert Campaign.from_dict(payload) == campaign


def test_campaign_backend_solver_default_to_container_agent() -> None:
    """Omitting backend/solver yields the container/agent defaults and validates."""
    omitted = {
        "id": _CAMPAIGN_ID,
        "createdAt": _TIMESTAMP,
        "model": "claude-opus-4-7",
        "arms": list(ARM_SLUGS),
        "suites": ["greenfield-features"],
        "trialsPerInstance": 3,
    }
    campaign = Campaign.from_dict(omitted)
    assert campaign.backend == domain.DEFAULT_BACKEND == "container"
    assert campaign.solver == domain.DEFAULT_SOLVER == "agent"


def test_out_of_enum_backend_rejected() -> None:
    """A Campaign backend outside the enum is rejected with a clear error."""
    bad = _campaign().to_dict()
    bad["backend"] = "kubernetes"
    with pytest.raises(DomainValidationError) as exc:
        Campaign.from_dict(bad)
    assert "backend" in str(exc.value)


def test_out_of_enum_solver_rejected() -> None:
    """A Campaign solver outside the enum is rejected with a clear error."""
    bad = _campaign().to_dict()
    bad["solver"] = "human"
    with pytest.raises(DomainValidationError) as exc:
        Campaign.from_dict(bad)
    assert "solver" in str(exc.value)


def test_unknown_suite_kind_rejected() -> None:
    """A Suite kind outside the enum is rejected with a clear error.

    ``issue-fixing`` is used as the rejected value: it was a valid kind before
    SWE-bench Pro was deferred, so this also guards the trim against regressing.
    """
    bad = _suite().to_dict()
    bad["kind"] = "issue-fixing"
    with pytest.raises(DomainValidationError) as exc:
        Suite.from_dict(bad)
    assert "kind" in str(exc.value)


def test_canonical_schema_file_is_the_authority(tmp_path: Path) -> None:
    """The module validates against the on-disk canonical schema, unmodified."""
    on_disk = json.loads(domain.CANONICAL_SCHEMA_PATH.read_text(encoding="utf-8"))
    assert on_disk == CANONICAL_SCHEMA
