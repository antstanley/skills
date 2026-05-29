"""Non-live unit tests for the arm-agnostic telemetry capture.

Feeds representative ``claude -p --output-format json`` result dicts to
:func:`benchmark.harness.telemetry.telemetry_from_agent_result` and asserts the
5-field guarantee (``docs/benchmark/specs/04-metrics.md`` §Bucket 2) without any
API spend: all five Telemetry fields present, correctly mapped, non-negative,
and gracefully defaulted when source fields are absent or non-numeric.
"""

from __future__ import annotations

from benchmark.harness.domain import Telemetry
from benchmark.harness.telemetry import telemetry_from_agent_result

#: Wall clock the caller measured for these fixture runs (seconds).
_WALL_CLOCK_SECONDS = 42.5

#: A representative claude ``--output-format json`` result (the shape the A0 run
#: backend parses): nested ``usage`` token counts, top-level cost and turns.
_SAMPLE_RESULT: dict[str, object] = {
    "type": "result",
    "subtype": "success",
    "is_error": False,
    "result": "done",
    "usage": {"input_tokens": 12, "output_tokens": 2233},
    "total_cost_usd": 0.15,
    "num_turns": 13,
}


def test_captures_all_five_fields_correctly_mapped() -> None:
    """All five fields are present, correctly mapped, and non-negative."""
    telemetry = telemetry_from_agent_result(_SAMPLE_RESULT, _WALL_CLOCK_SECONDS)

    assert isinstance(telemetry, Telemetry)
    assert telemetry.inputTokens == 12
    assert telemetry.outputTokens == 2233
    assert telemetry.costUsd == 0.15
    assert telemetry.wallClockSeconds == _WALL_CLOCK_SECONDS
    assert telemetry.agentTurns == 13

    # The 5-field non-negativity guarantee.
    assert telemetry.inputTokens >= 0
    assert telemetry.outputTokens >= 0
    assert telemetry.costUsd >= 0.0
    assert telemetry.wallClockSeconds >= 0.0
    assert telemetry.agentTurns >= 0


def test_round_trips_through_schema() -> None:
    """The captured record is schema-valid (survives to_dict/from_dict)."""
    telemetry = telemetry_from_agent_result(_SAMPLE_RESULT, _WALL_CLOCK_SECONDS)
    assert Telemetry.from_dict(telemetry.to_dict()) == telemetry


def test_defaults_when_fields_absent() -> None:
    """Missing token/cost/turn fields default to non-negative zeros."""
    telemetry = telemetry_from_agent_result({}, _WALL_CLOCK_SECONDS)

    assert telemetry.inputTokens == 0
    assert telemetry.outputTokens == 0
    assert telemetry.costUsd == 0.0
    assert telemetry.agentTurns == 0
    assert telemetry.wallClockSeconds == _WALL_CLOCK_SECONDS
    # Still schema-valid despite the empty result.
    assert Telemetry.from_dict(telemetry.to_dict()) == telemetry


def test_defaults_when_fields_non_numeric() -> None:
    """Non-numeric / malformed source values coerce to safe zero defaults."""
    malformed: dict[str, object] = {
        "usage": "not-a-mapping",
        "total_cost_usd": "expensive",
        "num_turns": None,
    }
    telemetry = telemetry_from_agent_result(malformed, _WALL_CLOCK_SECONDS)

    assert telemetry.inputTokens == 0
    assert telemetry.outputTokens == 0
    assert telemetry.costUsd == 0.0
    assert telemetry.agentTurns == 0
    assert telemetry.wallClockSeconds >= 0.0


def test_negative_sources_clamped_non_negative() -> None:
    """Negative wall clock / token / cost values clamp to non-negative."""
    weird: dict[str, object] = {
        "usage": {"input_tokens": -5, "output_tokens": -1},
        "total_cost_usd": -0.99,
        "num_turns": -3,
    }
    telemetry = telemetry_from_agent_result(weird, -10.0)

    assert telemetry.inputTokens == 0
    assert telemetry.outputTokens == 0
    assert telemetry.costUsd == 0.0
    assert telemetry.agentTurns == 0
    assert telemetry.wallClockSeconds == 0.0
