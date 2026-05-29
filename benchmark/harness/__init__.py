"""Harness: executes a Campaign over the Arms x Suites x Trials matrix.

Sub-packages mirror ``05-harness-architecture.md`` §Implementation layout plus
the backend seam from ``changes/2026-05-27-local_backends.md``:

- :mod:`benchmark.harness.driver` -- matrix expansion, Trial scheduler, lifecycle
- :mod:`benchmark.harness.arms` -- one provisioning recipe per Arm
- :mod:`benchmark.harness.scoring` -- the clean oracle runner
- :mod:`benchmark.harness.backends` -- pluggable RunBackend / ScoringBackend
- :mod:`benchmark.harness.telemetry` -- token/cost/wall-clock/turn capture
- :mod:`benchmark.harness.stats` -- Pass@k, deltas, and confidence intervals
"""
