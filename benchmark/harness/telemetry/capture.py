"""Arm-agnostic telemetry capture from a ``claude`` agent result.

This is the SINGLE, first-class capture path that turns a ``claude -p
--output-format json`` result (``.specs/benchmark/specs/04-metrics.md`` §Bucket 2 —
Cost and efficiency; sources: ``usage.input_tokens``/``output_tokens``,
``total_cost_usd``, ``num_turns``) plus a measured wall clock into a populated
:class:`~benchmark.harness.domain.Telemetry`. It lives in
``benchmark/harness/telemetry/`` per
``.specs/benchmark/specs/05-harness-architecture.md`` §Implementation layout.

Arm-agnostic by design
-----------------------
:func:`telemetry_from_agent_result` is the SAME function for EVERY arm: the
plain A0 baseline and the (future) plugin/workflow arms all run via
``claude -p --output-format json`` and all funnel their result JSON through this
one function. Token/cost/turn capture is therefore UNIFORM across arms — every
run reports all five fields at identical granularity through one code path
(DRY: the run backend delegates here rather than capturing inline).

A0 granularity finding
----------------------
A0 and the plugin arms both invoke ``claude -p --output-format json`` and read
the same ``usage``/``total_cost_usd``/``num_turns`` keys, so A0 reports at the
SAME granularity as the plugin arms: **A0 parity holds — there is NO granularity
gap.** (Recorded here per the task: a gap is logged in plan.md Open questions
only if one exists; none does.)
"""

from __future__ import annotations

from collections.abc import Mapping

from benchmark.harness.domain import Telemetry


def telemetry_from_agent_result(
    result_json: Mapping[str, object], wall_clock_seconds: float
) -> Telemetry:
    """Build a :class:`Telemetry` from a claude result JSON + measured wall clock.

    Maps the five Bucket-2 fields from the agent result:

    * ``inputTokens``  <- ``usage.input_tokens``
    * ``outputTokens`` <- ``usage.output_tokens``
    * ``costUsd``      <- ``total_cost_usd``
    * ``agentTurns``   <- ``num_turns``
    * ``wallClockSeconds`` <- the caller-measured ``wall_clock_seconds``

    Missing or non-numeric token/cost/turn fields coerce to safe, non-negative
    defaults (``0`` / ``0.0``) so the record stays schema-valid; the wall clock
    is clamped to be non-negative. Arm-agnostic: the SAME function captures A0
    and plugin-arm telemetry, so granularity is uniform across arms.
    """
    usage = result_json.get("usage")
    usage_map: Mapping[str, object] = usage if isinstance(usage, Mapping) else {}
    return Telemetry(
        inputTokens=_as_non_negative_int(usage_map.get("input_tokens")),
        outputTokens=_as_non_negative_int(usage_map.get("output_tokens")),
        costUsd=_as_non_negative_float(result_json.get("total_cost_usd")),
        wallClockSeconds=max(0.0, float(wall_clock_seconds)),
        agentTurns=_as_non_negative_int(result_json.get("num_turns")),
    )


def _as_non_negative_int(value: object) -> int:
    """Coerce a JSON numeric to a non-negative ``int`` (0 when absent/invalid)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return max(0, int(value))


def _as_non_negative_float(value: object) -> float:
    """Coerce a JSON numeric to a non-negative ``float`` (0.0 when absent/invalid)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0
    return max(0.0, float(value))
