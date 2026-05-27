"""Arms: one provisioning recipe per Arm (plugins, flags, execution mode)."""

from __future__ import annotations

from benchmark.harness.arms.a0 import (
    A0,
    A0_INSTRUCTION,
    A0_MAX_BUDGET_USD,
    A0_MODEL,
    A0_SLUG,
    AUTH_PROBE_MAX_BUDGET_USD,
    a0_prompt,
)

__all__ = [
    "A0",
    "A0_INSTRUCTION",
    "A0_MAX_BUDGET_USD",
    "A0_MODEL",
    "A0_SLUG",
    "AUTH_PROBE_MAX_BUDGET_USD",
    "a0_prompt",
]
