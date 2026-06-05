"""Gate-efficacy probes: injected defects + catch/escape accounting.

Implements ``.specs/benchmark/specs/06-scoring-and-statistics.md`` §Gate-efficacy
probes and the two gate metrics of ``.specs/benchmark/specs/04-metrics.md``
§Bucket 3, for the GATED arms (A1, A2):

- **Injected defects + catch rate** (:mod:`benchmark.harness.scoring.probes.defects`):
  a taxonomy of ``InjectedDefect`` kinds (named constants) and a generator of
  ``InjectedDefect`` records; the **catch-rate accounting** is the fraction of a
  set of injected defects whose ``caughtBy`` is set (a gate flagged it). The
  generation + accounting are pure computation; the live injection that
  POPULATES ``caughtBy`` by running a real gate is opt-in
  (:mod:`benchmark.harness.scoring.probes.live`).
- **False-``Done`` escape rate** (:mod:`benchmark.harness.scoring.probes.escape`):
  across organic gated trials, the fraction of ``Done`` tasks whose hidden tests
  fail (``ScoreReport.gateEscape``), with per-task attribution via the instance's
  ``testTags`` and an instance-granularity fallback.

Both gate metrics depend on the gates never having seen the hidden suite (the
integrity rule of ``05-harness-architecture.md``); the probes never inject the
hidden tests into a run environment.
"""

from __future__ import annotations

from benchmark.harness.scoring.probes.defects import (
    DEFECT_KIND_DROPPED_BRANCH,
    DEFECT_KIND_OFF_BY_ONE,
    DEFECT_KIND_WRONG_RETURN,
    DEFECT_KINDS,
    DEFECT_MUTATIONS,
    CatchRate,
    DefectMutation,
    catch_rate,
    make_injected_defect,
)
from benchmark.harness.scoring.probes.escape import (
    GATED_ARMS,
    EscapeRate,
    TaskEscape,
    derive_gate_escape,
    escape_rate,
    per_task_escapes,
)
from benchmark.harness.scoring.probes.live import (
    LIVE_PROBE_ENV,
    PROBE_MAX_BUDGET_USD,
    GateProbeError,
    build_review_prompt,
    cli_review_gate,
    run_gate_probe,
    verdict_caught,
)

__all__ = [
    "CatchRate",
    "DEFECT_KINDS",
    "DEFECT_KIND_DROPPED_BRANCH",
    "DEFECT_KIND_OFF_BY_ONE",
    "DEFECT_KIND_WRONG_RETURN",
    "DEFECT_MUTATIONS",
    "DefectMutation",
    "EscapeRate",
    "GATED_ARMS",
    "GateProbeError",
    "LIVE_PROBE_ENV",
    "PROBE_MAX_BUDGET_USD",
    "TaskEscape",
    "build_review_prompt",
    "catch_rate",
    "cli_review_gate",
    "derive_gate_escape",
    "escape_rate",
    "make_injected_defect",
    "per_task_escapes",
    "run_gate_probe",
    "verdict_caught",
]
