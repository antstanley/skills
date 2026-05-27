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
from benchmark.harness.arms.a1 import (
    A1,
    A1_ARTIFACT_DIR,
    A1_CERTIFICATE_DIR_NAME,
    A1_CONTAINER_PLUGIN_ROOT,
    A1_FEASIBILITY_PROBE_MAX_BUDGET_USD,
    A1_INSTRUCTION,
    A1_MAX_BUDGET_USD,
    A1_MODEL,
    A1_PLAN_SUBDIR,
    A1_PLUGIN_DIR_NAMES,
    A1_PLUGINS_ENABLED,
    A1_SLUG,
    A1_SPEC_SUBDIR,
    HOST_PLUGIN_MARKETPLACE_DIR,
    a1_prompt,
)

__all__ = [
    "A0",
    "A0_INSTRUCTION",
    "A0_MAX_BUDGET_USD",
    "A0_MODEL",
    "A0_SLUG",
    "A1",
    "A1_ARTIFACT_DIR",
    "A1_CERTIFICATE_DIR_NAME",
    "A1_CONTAINER_PLUGIN_ROOT",
    "A1_FEASIBILITY_PROBE_MAX_BUDGET_USD",
    "A1_INSTRUCTION",
    "A1_MAX_BUDGET_USD",
    "A1_MODEL",
    "A1_PLAN_SUBDIR",
    "A1_PLUGINS_ENABLED",
    "A1_PLUGIN_DIR_NAMES",
    "A1_SLUG",
    "A1_SPEC_SUBDIR",
    "AUTH_PROBE_MAX_BUDGET_USD",
    "HOST_PLUGIN_MARKETPLACE_DIR",
    "a0_prompt",
    "a1_prompt",
]
