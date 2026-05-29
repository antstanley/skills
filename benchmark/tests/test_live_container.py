"""Thin pytest wrapper over the OPT-IN live container round-trip witness.

Wraps :mod:`benchmark.harness.run_container_check` (tasks 01-02). The guard
tests RUN in CI and need no Docker: they prove ``evaluate_skip`` and ``main``
refuse to do real work when the opt-in is unset / not ``"1"`` (the negative
space — no container is provisioned at collection/guard time). The single live
test is gated behind ``BENCHMARK_RUN_CONTAINER_LIVE=1`` and SKIPs by default,
mirroring the live gate-probe test (``benchmark/tests/test_gate_probes.py``);
it calls ``run_container_check()`` (the full A0 round-trip + resolved-parity +
run-image integrity + gate-emission + live ``claude -p`` gate-probe witness)
and only fires on an operator host with Docker + an authenticated CLI.
"""

from __future__ import annotations

import os

import pytest

from benchmark.harness.run_container_check import (
    LIVE_CONTAINER_ENABLED_VALUE,
    LIVE_CONTAINER_ENV,
    SKIP_EXIT_CODE,
    evaluate_skip,
    main,
    run_container_check,
)

# --- guard tests (these RUN in CI, no Docker) --------------------------------


def test_evaluate_skip_does_not_run_when_env_missing() -> None:
    # Empty env mapping -> the opt-in is absent -> the live path must not run,
    # and the reason must name the env var so an operator knows how to opt in.
    decision = evaluate_skip(env={})
    assert decision.should_run is False
    assert LIVE_CONTAINER_ENV in decision.reason


def test_evaluate_skip_does_not_run_when_env_not_enabled_value() -> None:
    # Set but not to "1" -> still a skip (the value must equal the enabled
    # value exactly), with the env var named in the reason.
    decision = evaluate_skip(env={LIVE_CONTAINER_ENV: "0"})
    assert decision.should_run is False
    assert LIVE_CONTAINER_ENV in decision.reason


def test_main_returns_skip_exit_code_when_opt_in_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # main() reads the real os.environ; clearing the opt-in proves it skips
    # cleanly (no container started, no exception) and returns SKIP_EXIT_CODE.
    monkeypatch.delenv(LIVE_CONTAINER_ENV, raising=False)
    assert main() == SKIP_EXIT_CODE


# --- the OPT-IN live witness (SKIPs by default) ------------------------------


@pytest.mark.skipif(
    os.environ.get(LIVE_CONTAINER_ENV) != LIVE_CONTAINER_ENABLED_VALUE,
    reason=(
        f"set {LIVE_CONTAINER_ENV}={LIVE_CONTAINER_ENABLED_VALUE} to run the real "
        "A0 container round-trip on Docker (needs an authenticated claude CLI)"
    ),
)
def test_live_container_round_trip() -> None:
    """Run the full live A0 round-trip + parity + integrity + gate witness.

    Calls ``run_container_check()`` directly: it provisions the real RUN/SCORING
    containers, asserts resolved-parity at both poles, run-image integrity, the
    A2/A3 gate emission, and the live ``claude -p`` gate probe. Returns the
    ``(reference, noop)`` parity verdicts — the reference pole must resolve and
    the no-op pole must not, which is the witness this opt-in path proves.
    """
    reference_verdict, noop_verdict = run_container_check()
    assert reference_verdict.agree
    assert noop_verdict.agree
    assert reference_verdict.container_resolved is True
    assert noop_verdict.container_resolved is False
