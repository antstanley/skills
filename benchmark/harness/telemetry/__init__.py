"""Telemetry: token/cost/wall-clock/turn capture into ArtifactBundle.telemetry.

One arm-agnostic capture path (:func:`telemetry_from_agent_result`) shared by the
run backend across ALL arms, so A0 and the plugin arms report the same five
Bucket-2 fields at identical granularity (see :mod:`.capture` for the A0-parity
finding).
"""

from __future__ import annotations

from benchmark.harness.telemetry.capture import telemetry_from_agent_result

__all__ = ["telemetry_from_agent_result"]
