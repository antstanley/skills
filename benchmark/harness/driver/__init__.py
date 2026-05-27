"""Driver: matrix expansion, Trial scheduler, and lifecycle management.

A backend-NEUTRAL scheduler over the Trial lifecycle: it expands a ``Campaign``
into Trials, drives each through ``queued → provisioning → running → captured →
scored → aggregated`` via the injected ``RunBackend`` / ``ScoringBackend``, runs
independent Trials concurrently up to a configured pool size, and records infra
faults as ``failed`` (excluded from metrics) distinct from ``resolved: false``.
See ``05-harness-architecture.md`` §Component shape and §Concurrency.
"""

from __future__ import annotations

from benchmark.harness.driver.scheduler import (
    DEFAULT_POOL_SIZE,
    RUN_BACKEND_GATE_EVENTS_ATTR,
    SEED_BASE,
    STATUS_AGGREGATED,
    STATUS_CAPTURED,
    STATUS_FAILED,
    STATUS_PROVISIONING,
    STATUS_QUEUED,
    STATUS_RUNNING,
    STATUS_SCORED,
    CampaignRun,
    InfraFault,
    TrialResult,
    expand_matrix,
    order_independent_results,
    run_campaign,
)

__all__ = [
    "DEFAULT_POOL_SIZE",
    "RUN_BACKEND_GATE_EVENTS_ATTR",
    "SEED_BASE",
    "STATUS_AGGREGATED",
    "STATUS_CAPTURED",
    "STATUS_FAILED",
    "STATUS_PROVISIONING",
    "STATUS_QUEUED",
    "STATUS_RUNNING",
    "STATUS_SCORED",
    "CampaignRun",
    "InfraFault",
    "TrialResult",
    "expand_matrix",
    "order_independent_results",
    "run_campaign",
]
