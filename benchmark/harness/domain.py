"""Typed in-code records for every benchmark entity.

Each entity defined in ``docs/benchmark/specs/01-domain-model.md`` is mirrored
here as a frozen dataclass whose field names, types, and enums match the
canonical JSON Schema (``docs/benchmark/specs/canonical-types.schema.json``)
exactly. The schema is the single authority: every record validates against its
``$def`` both when constructed and when loaded, and ``to_dict``/``from_dict``
round-trip (construct -> dump -> load -> equal).

Identifiers follow the ``<prefix>_<uuid7>`` scheme from the spec: a short
lowercase prefix, an underscore, and a v7 UUID (RFC 9562) so ids sort by
creation time. Slugs (Suite, TaskInstance) and the fixed Arm slugs carry their
own rules. Every literal limit -- prefixes, patterns, enum members -- is a
named constant below.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import time
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import asdict, dataclass, fields, is_dataclass
from pathlib import Path
from typing import Any, ClassVar, TypeVar
from uuid import UUID

from jsonschema import Draft202012Validator
from jsonschema import ValidationError as _JsonSchemaValidationError

# ---------------------------------------------------------------------------
# Schema location and access
# ---------------------------------------------------------------------------

#: The canonical schema, the authority for every record shape.
CANONICAL_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "benchmark"
    / "specs"
    / "canonical-types.schema.json"
)

#: JSON-Schema ``$ref`` fragment prefix for the entity definitions.
_DEFS_FRAGMENT = "#/$defs/"


class DomainValidationError(ValueError):
    """Raised when a record fails schema validation, with a clear message."""


def _load_canonical_schema() -> dict[str, Any]:
    with CANONICAL_SCHEMA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


#: Parsed canonical schema document (loaded once at import).
CANONICAL_SCHEMA: dict[str, Any] = _load_canonical_schema()


def _validator_for(def_name: str) -> Draft202012Validator:
    """Build a validator for one ``$defs`` entry, resolving sibling ``$ref``s."""
    schema = {
        "$schema": CANONICAL_SCHEMA["$schema"],
        "$defs": CANONICAL_SCHEMA["$defs"],
        "$ref": f"{_DEFS_FRAGMENT}{def_name}",
    }
    return Draft202012Validator(schema)


_VALIDATORS: dict[str, Draft202012Validator] = {}


def _validate(def_name: str, payload: Mapping[str, Any]) -> None:
    """Validate ``payload`` against the named ``$def`` or raise a clear error."""
    validator = _VALIDATORS.get(def_name)
    if validator is None:
        validator = _validator_for(def_name)
        _VALIDATORS[def_name] = validator
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.path))
    if errors:
        first: _JsonSchemaValidationError = errors[0]
        location = "/".join(str(p) for p in first.path) or "<root>"
        raise DomainValidationError(
            f"{def_name} record invalid at {location}: {first.message}"
        )


# ---------------------------------------------------------------------------
# Shared pattern / enum constants (mirrored from the canonical schema)
# ---------------------------------------------------------------------------

#: Stable lowercase slug pattern (Slug $def).
SLUG_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9_-]*[a-z0-9])?$")

#: Generated record-id pattern (RecordId $def): ``<prefix>_<uuid7>``.
RECORD_ID_PATTERN = re.compile(r"^[a-z]+_[0-9a-f-]{36}$")

#: The five fixed ablation arm slugs (ArmSlug $def). Closed set, never reused.
ARM_SLUGS: tuple[str, ...] = ("A0", "A1", "A2", "A3", "A4")

#: Gate kinds (GateKind $def).
GATE_KINDS: tuple[str, ...] = ("semi-formal-review", "validate-done-certificate")

#: Gate verdicts (GateVerdict $def).
GATE_VERDICTS: tuple[str, ...] = ("PASS", "FAIL", "PARTIAL", "UNVERIFIED")

#: Suite kinds.
SUITE_KINDS: tuple[str, ...] = ("issue-fixing", "greenfield", "local-fixture")

#: Suite oracle conventions.
ORACLE_CONVENTIONS: tuple[str, ...] = (
    "swe-bench-pro",
    "greenfield-hidden-tests",
    "local",
)

#: Campaign run/scoring backends; ``container`` is the production default.
BACKENDS: tuple[str, ...] = ("container", "local")

#: Default Campaign backend applied when the field is omitted.
DEFAULT_BACKEND = "container"

#: Campaign solvers; ``agent`` is the default, ``fixture`` runs the scripted
#: solver that emits the instance goldPatch for deterministic verification.
SOLVERS: tuple[str, ...] = ("agent", "fixture")

#: Default Campaign solver applied when the field is omitted.
DEFAULT_SOLVER = "agent"

#: Contamination tiers for a TaskInstance.
CONTAMINATION_TIERS: tuple[str, ...] = ("public", "held-out", "authored-private")

#: Arm execution modes.
EXECUTION_MODES: tuple[str, ...] = (
    "single",
    "parallel-structured",
    "parallel-unstructured",
)

#: Trial lifecycle states (see 01-domain-model.md Lifecycle).
TRIAL_STATUSES: tuple[str, ...] = (
    "queued",
    "provisioning",
    "running",
    "captured",
    "scored",
    "aggregated",
    "failed",
)

# ---------------------------------------------------------------------------
# Record-id prefixes (one per generated-id entity, per 01-domain-model.md)
# ---------------------------------------------------------------------------

CAMPAIGN_ID_PREFIX = "camp"
TRIAL_ID_PREFIX = "trial"
ARTIFACT_BUNDLE_ID_PREFIX = "bundle"
GATE_EVENT_ID_PREFIX = "gate"
SCORE_REPORT_ID_PREFIX = "score"
INJECTED_DEFECT_ID_PREFIX = "defect"
METRIC_RESULT_ID_PREFIX = "metric"

# ---------------------------------------------------------------------------
# uuid7 generation (RFC 9562 §5.7) -- stdlib has no uuid.uuid7 on 3.13
# ---------------------------------------------------------------------------

_UUID7_VERSION = 0x7
_UUID7_VARIANT = 0b10
_MILLIS_PER_SECOND = 1000
_RAND_A_BITS = 12
_RAND_B_BITS = 62


def uuid7() -> UUID:
    """Return a version-7 UUID (RFC 9562): 48-bit ms timestamp + random bits.

    Time-ordered, so ``<prefix>_<uuid7>`` ids sort by creation time. Uses
    ``secrets`` for the random portion.
    """
    unix_ms = time.time_ns() // 1_000_000
    rand_a = secrets.randbits(_RAND_A_BITS)
    rand_b = secrets.randbits(_RAND_B_BITS)

    value = (unix_ms & ((1 << 48) - 1)) << 80
    value |= _UUID7_VERSION << 76
    value |= rand_a << 64
    value |= _UUID7_VARIANT << 62
    value |= rand_b
    return UUID(int=value)


def new_record_id(prefix: str) -> str:
    """Build a ``<prefix>_<uuid7>`` id and verify it against the RecordId rule."""
    record_id = f"{prefix}_{uuid7()}"
    if not RECORD_ID_PATTERN.fullmatch(record_id):
        raise DomainValidationError(
            f"generated id {record_id!r} does not match the RecordId pattern"
        )
    return record_id


def is_valid_slug(value: str) -> bool:
    """Whether ``value`` matches the canonical Slug pattern."""
    return bool(SLUG_PATTERN.fullmatch(value))


# ---------------------------------------------------------------------------
# Base record: schema-validated, dataclass-backed, round-tripping
# ---------------------------------------------------------------------------

T = TypeVar("T", bound="Record")

#: Sentinel for "field absent" so optional fields can be omitted from dumps
#: (the schema forbids unknown properties but allows optional ones to be
#: missing). ``None`` is a legitimate value for several nullable fields, so it
#: cannot double as "absent".
_UNSET: Any = object()


@dataclass(frozen=True)
class Record:
    """Base for every entity: validates against its ``$def`` on construct/load.

    Subclasses set ``schema_def`` to the canonical ``$defs`` name and
    ``optional_fields`` to the field names the schema does not require (these
    are dropped from ``to_dict`` when still unset, so dumps stay schema-clean).
    """

    schema_def: ClassVar[str] = ""
    optional_fields: ClassVar[frozenset[str]] = frozenset()

    def __post_init__(self) -> None:
        _validate(self.schema_def, self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        """Dump to a plain JSON-serialisable dict, omitting unset optionals."""
        out: dict[str, Any] = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if value is _UNSET:
                continue
            out[f.name] = _to_jsonable(value)
        return out

    @classmethod
    def from_dict(cls: type[T], payload: Mapping[str, Any]) -> T:
        """Load from a dict, validating against the schema first."""
        if not isinstance(payload, Mapping):
            kind = type(payload).__name__
            raise DomainValidationError(
                f"{cls.schema_def} record must be an object, got {kind}"
            )
        _validate(cls.schema_def, payload)
        known = {f.name for f in fields(cls)}
        unknown = set(payload) - known
        if unknown:
            raise DomainValidationError(
                f"{cls.schema_def} record has unknown field(s): {sorted(unknown)}"
            )
        kwargs: dict[str, Any] = {}
        for f in fields(cls):
            if f.name in payload:
                kwargs[f.name] = payload[f.name]
        return cls(**kwargs)


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        if isinstance(value, Record):
            return value.to_dict()
        return asdict(value)
    if isinstance(value, Mapping):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    return value


# ---------------------------------------------------------------------------
# Entities (field order and names mirror the canonical schema $defs)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Suite(Record):
    schema_def: ClassVar[str] = "Suite"

    slug: str
    kind: str
    oracleConvention: str


@dataclass(frozen=True)
class TaskInstance(Record):
    schema_def: ClassVar[str] = "TaskInstance"
    optional_fields: ClassVar[frozenset[str]] = frozenset(
        {"goldPatch", "testTags", "dockerImage"}
    )

    slug: str
    suite: str
    repo: str
    baseCommit: str
    problemStatement: str
    failToPass: list[str]
    passToPass: list[str]
    contaminationTier: str
    headlessVerifiable: bool
    goldPatch: str | None = _UNSET
    testTags: dict[str, str] | None = _UNSET
    dockerImage: str | None = _UNSET


@dataclass(frozen=True)
class Arm(Record):
    schema_def: ClassVar[str] = "Arm"

    slug: str
    pluginsEnabled: list[str]
    gatesEnabled: bool
    specProvided: bool
    executionMode: str


@dataclass(frozen=True)
class Campaign(Record):
    schema_def: ClassVar[str] = "Campaign"

    id: str
    createdAt: str
    model: str
    arms: list[str]
    suites: list[str]
    trialsPerInstance: int
    backend: str = DEFAULT_BACKEND
    solver: str = DEFAULT_SOLVER


@dataclass(frozen=True)
class Trial(Record):
    schema_def: ClassVar[str] = "Trial"
    optional_fields: ClassVar[frozenset[str]] = frozenset(
        {"candidatePatch", "artifactBundle", "scoreReport"}
    )

    id: str
    campaign: str
    arm: str
    taskInstance: str
    seed: int
    createdAt: str
    status: str
    candidatePatch: str | None = _UNSET
    artifactBundle: str | None = _UNSET
    scoreReport: str | None = _UNSET


@dataclass(frozen=True)
class Telemetry(Record):
    schema_def: ClassVar[str] = "Telemetry"

    inputTokens: int
    outputTokens: int
    costUsd: float
    wallClockSeconds: float
    agentTurns: int


@dataclass(frozen=True)
class ArtifactBundle(Record):
    schema_def: ClassVar[str] = "ArtifactBundle"
    optional_fields: ClassVar[frozenset[str]] = frozenset(
        {"specArtifacts", "planArtifacts", "certificateArtifacts", "transcript"}
    )

    id: str
    trial: str
    telemetry: Telemetry
    specArtifacts: list[str] = _UNSET
    planArtifacts: list[str] = _UNSET
    certificateArtifacts: list[str] = _UNSET
    transcript: str | None = _UNSET

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ArtifactBundle:
        record = super().from_dict(payload)
        # Re-wrap the nested telemetry mapping as a typed Telemetry record.
        if isinstance(record.telemetry, Mapping):
            object.__setattr__(
                record, "telemetry", Telemetry.from_dict(record.telemetry)
            )
        return record


@dataclass(frozen=True)
class GateEvent(Record):
    schema_def: ClassVar[str] = "GateEvent"

    id: str
    trial: str
    task: str
    gateKind: str
    verdict: str
    retryIndex: int


@dataclass(frozen=True)
class InjectedDefect(Record):
    schema_def: ClassVar[str] = "InjectedDefect"

    id: str
    taskInstance: str
    defectKind: str
    caughtBy: str | None


@dataclass(frozen=True)
class ScoreReport(Record):
    schema_def: ClassVar[str] = "ScoreReport"
    optional_fields: ClassVar[frozenset[str]] = frozenset(
        {
            "failToPassResults",
            "passToPassResults",
            "conformanceScore",
            "gateEscape",
        }
    )

    id: str
    trial: str
    resolved: bool
    regressed: bool
    failToPassResults: dict[str, bool] = _UNSET
    passToPassResults: dict[str, bool] = _UNSET
    conformanceScore: float | None = _UNSET
    gateEscape: bool | None = _UNSET


@dataclass(frozen=True)
class MetricResult(Record):
    schema_def: ClassVar[str] = "MetricResult"

    id: str
    campaign: str
    arm: str
    suite: str
    metricName: str
    value: float
    ciLow: float
    ciHigh: float
    nTrials: int


# ---------------------------------------------------------------------------
# JSONL load/dump for instance files and per-trial artifact records
# ---------------------------------------------------------------------------

_JSONL_ENCODING = "utf-8"


def dump_jsonl(records: Iterable[Record], path: str | os.PathLike[str]) -> None:
    """Write records to a JSONL file (one validated record per line)."""
    target = Path(path)
    with target.open("w", encoding=_JSONL_ENCODING) as handle:
        for record in records:
            handle.write(json.dumps(record.to_dict(), sort_keys=True))
            handle.write("\n")


def load_jsonl[R: Record](
    record_type: type[R], path: str | os.PathLike[str]
) -> list[R]:
    """Read and validate a JSONL file into typed records of ``record_type``."""
    source = Path(path)
    out: list[R] = []
    with source.open(encoding=_JSONL_ENCODING) as handle:
        for lineno, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise DomainValidationError(
                    f"{path}:{lineno}: not valid JSON: {exc}"
                ) from exc
            out.append(record_type.from_dict(payload))
    return out


def iter_jsonl[R: Record](
    record_type: type[R], path: str | os.PathLike[str]
) -> Iterator[R]:
    """Stream typed records from a JSONL file, validating each line."""
    yield from load_jsonl(record_type, path)


def dump_json(record: Record, path: str | os.PathLike[str]) -> None:
    """Write a single record as a JSON object (per-trial artifact record)."""
    Path(path).write_text(
        json.dumps(record.to_dict(), sort_keys=True, indent=2) + "\n",
        encoding=_JSONL_ENCODING,
    )


def load_json[R: Record](record_type: type[R], path: str | os.PathLike[str]) -> R:
    """Read and validate a single-object JSON file into a typed record."""
    payload = json.loads(Path(path).read_text(encoding=_JSONL_ENCODING))
    return record_type.from_dict(payload)
