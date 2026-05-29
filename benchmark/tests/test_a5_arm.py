"""Tests for the A5 arm — lighter pre-canned (non-recursive) variant.

A5 (``02-arms.md`` §A5 — Lighter pre-canned) produces the same OBSERVABLE
artifacts a gated workflow arm does — a candidate code patch and at least one
discharged done-certificate carrying a real ``VERDICT:`` line — but WITHOUT a
recursive ``spec-planner`` + ``spec-builder`` build. It runs ONE bounded
``claude -p`` call on a SMALL budget cap and a SHORT timeout. It exists as a fast,
reliable gate-emission witness (for ``extract_gate_events``) and as a cheaper
cost-curve point; the recursive arms (A1/A2) can exceed the run timeout, which
makes them a poor fixture for that check.

These tests assert (non-gated, no API/Docker):

- the A5 arm record is configured correctly (no plugins, gates ON, no spec,
  ``single``) and round-trips through the canonical schema;
- the budget/timeout constants are the documented small/short bounds and the
  budget is a fraction of A1's recursive-arm cap (the "lighter" claim);
- dispatch routes the A5 slug to its own ``_run_a5`` path, NOT the plain-A0,
  workflow, or A4 path; and A0 still routes to the agent path;
- the pre-canned prompt carries the problem statement plus a certificate-writing
  + ``VERDICT:`` directive, and is non-recursive (no ``spec-planner`` /
  ``spec-builder`` invocation, no isolated workspace);
- a captured A5-style certificate (the ``"<relpath>\\n<contents>"`` shape the
  container capture produces) fed to the SAME ``extract_gate_events`` A2 uses
  yields >= 1 ``GateEvent`` — proving an A5 run emits a gate event.

The live A5 run is gated behind ``BENCHMARK_RUN_A5_LIVE=1`` + Docker + creds
(mirroring the A4 opt-in) and skipped by default; the build verifies only the
SKIP/unit surface here.
"""

from __future__ import annotations

import os

import pytest

from benchmark.harness.arms.a0 import A0, A0_MODEL
from benchmark.harness.arms.a1 import A1_MAX_BUDGET_USD
from benchmark.harness.arms.a2_a3 import GATE_KIND_VALIDATE, extract_gate_events
from benchmark.harness.arms.a5 import (
    A5,
    A5_CERTIFICATE_RELPATH,
    A5_MAX_BUDGET_USD,
    A5_MODEL,
    A5_RUN_TIMEOUT_SECONDS,
    A5_SLUG,
    a5_prompt,
)
from benchmark.harness.backends import ContainerRunBackend, RunBackend
from benchmark.harness.backends.container import HOST_CREDENTIALS_PATH
from benchmark.harness.domain import ARM_SLUGS, GATE_VERDICTS, Arm
from benchmark.suites import greenfield_images as images
from benchmark.suites.greenfield import TEXT_TOOLKIT_SLUG, load_instance

# --- gating (live A5 run, opt-in only) -------------------------------------

_DOCKER_UP = images.docker_available()
_CREDS_PRESENT = HOST_CREDENTIALS_PATH.is_file()

#: Opt-in env var gating the LIVE A5 run (a single bounded real ``claude -p``
#: call spends real, user-authorized budget capped at ``A5_MAX_BUDGET_USD``).
_A5_LIVE_OPT_IN_ENV = "BENCHMARK_RUN_A5_LIVE"
_A5_LIVE_OPT_IN = os.environ.get(_A5_LIVE_OPT_IN_ENV) == "1"

_skip_no_live = pytest.mark.skipif(
    not (_A5_LIVE_OPT_IN and _DOCKER_UP and _CREDS_PRESENT),
    reason=(
        f"LIVE A5 run needs {_A5_LIVE_OPT_IN_ENV}=1 (a bounded real claude -p "
        "call spends budget) + Docker + host claude credentials"
    ),
)

_TRIAL_ID = "trial_00000000-0000-7000-8000-0000000000a5"


# --- the A5 arm record ------------------------------------------------------


def test_a5_arm_is_precanned_no_plugins_gates_on_single() -> None:
    """A5: no plugins, gates ON (emits gate events), no spec, single execution."""
    assert A5.slug == "A5"
    assert A5_SLUG == "A5"
    assert A5.pluginsEnabled == []
    assert A5.gatesEnabled is True
    assert A5.specProvided is False
    assert A5.executionMode == "single"


def test_a5_arm_round_trips_through_the_schema() -> None:
    assert Arm.from_dict(A5.to_dict()) == A5


def test_a5_is_in_the_closed_arm_slug_set() -> None:
    """A5 is the sixth member of the closed ARM_SLUGS / ArmSlug set."""
    assert "A5" in ARM_SLUGS
    assert ARM_SLUGS == ("A0", "A1", "A2", "A3", "A4", "A5")
    # And it validates as a Campaign/Trial arm member via the schema enum.
    assert (
        Arm(
            slug="A5",
            pluginsEnabled=[],
            gatesEnabled=True,
            specProvided=False,
            executionMode="single",
        )
        == A5
    )


# --- the lighter (small budget / short timeout) bounds ----------------------


def test_a5_budget_and_timeout_are_the_documented_light_bounds() -> None:
    """A5's cap is the small 5.0 USD bound; its timeout is the short 600s bound."""
    assert A5_MAX_BUDGET_USD == 5.0
    assert A5_RUN_TIMEOUT_SECONDS == 600
    assert A5_MODEL == A0_MODEL  # plain model, like A0


def test_a5_is_lighter_than_the_recursive_workflow_cap() -> None:
    """The whole point: A5's budget is a FRACTION of A1's recursive-arm cap."""
    assert A5_MAX_BUDGET_USD < A1_MAX_BUDGET_USD


# --- dispatch (A5 path, not plain-A0 / workflow / A4) -----------------------


def test_a5_selects_its_own_path_not_agent_not_workflow_not_a4() -> None:
    assert ContainerRunBackend._selects_a5(A5) is True
    # A5 must NOT fall into the plain-A0 path (it is, like A0, a no-plugin/no-spec
    # Arm, so dispatching by the A5 slug FIRST is what keeps it on _run_a5).
    assert ContainerRunBackend._selects_agent(A5) is False
    # A5 is not a recursive workflow arm and not the naive-parallel A4.
    assert ContainerRunBackend._selects_workflow(A5) is False
    assert ContainerRunBackend._selects_a4(A5) is False


def test_a0_does_not_select_the_a5_path() -> None:
    assert ContainerRunBackend._selects_a5(A0) is False
    assert ContainerRunBackend._selects_agent(A0) is True


def test_backend_satisfies_run_protocol() -> None:
    assert isinstance(ContainerRunBackend(), RunBackend)


def test_backend_last_gate_events_starts_empty() -> None:
    """Before any A5 run, the backend exposes no gate events."""
    assert ContainerRunBackend().last_gate_events == []


# --- the pre-canned prompt --------------------------------------------------


def test_a5_prompt_carries_the_problem_and_the_certificate_verdict_directive() -> None:
    """The fixed prompt: implement the feature AND write a VERDICT: certificate."""
    instance = load_instance(TEXT_TOOLKIT_SLUG)
    prompt = a5_prompt(instance.problemStatement)
    assert instance.problemStatement in prompt
    # It must direct writing a done-certificate carrying a real VERDICT: line at
    # the captured-artifact path, so extract_gate_events finds a GateEvent.
    assert "VERDICT:" in prompt
    assert "certificate" in prompt.lower()
    assert A5_CERTIFICATE_RELPATH in prompt


def test_a5_prompt_is_pre_canned_not_recursive() -> None:
    """A5 is scripted: it does NOT invoke spec-planner/spec-builder or recurse."""
    instance = load_instance(TEXT_TOOLKIT_SLUG)
    prompt = a5_prompt(instance.problemStatement).lower()
    # The pre-canned flow explicitly does NOT stand up the recursive workflow.
    assert "do not run spec-planner" in prompt
    assert "isolated workspace" in prompt  # ...only to say NOT to set one up
    assert "do not spawn sub-agents" in prompt


# --- the gate-emission witness (the change's whole reason to exist) ---------

#: A captured A5 done-certificate in the bundle-entry shape the container
#: capture produces (``"<relpath>\n<contents>"``), carrying the discharged
#: validate-done verdict the pre-canned prompt writes.
_A5_CAPTURED_CERTIFICATE = (
    f"{A5_CERTIFICATE_RELPATH}\n"
    "# Done certificate\n\n"
    "## Conclusion\n\nVERDICT: DONE\nState: self-reported by the pre-canned A5 run\n"
)


def test_a5_captured_certificate_yields_a_gate_event() -> None:
    """An A5 run's discharged certificate maps to >= 1 GateEvent, exactly as A2's.

    Uses the SAME extract_gate_events the workflow arms use, on a certificate in
    the captured-bundle shape — so this pins the change's core claim: A5 emits a
    GateEvent WITHOUT a recursive build.
    """
    events = extract_gate_events([_A5_CAPTURED_CERTIFICATE], trial_id=_TRIAL_ID)
    assert len(events) >= 1
    event = events[0]
    assert event.gateKind == GATE_KIND_VALIDATE
    assert event.verdict in GATE_VERDICTS
    assert event.verdict == "PASS"  # DONE -> PASS in the validate map
    assert event.trial == _TRIAL_ID
    assert event.task == "01-feature"  # the certificate file stem


def test_a5_blank_certificate_yields_no_gate_event() -> None:
    """Negative space: an UNdischarged certificate (no VERDICT:) emits nothing."""
    blank = (
        f"{A5_CERTIFICATE_RELPATH}\n"
        "# Done certificate\n\n**Verdict:** (blank — to be filled by the gate)\n"
    )
    assert extract_gate_events([blank], trial_id=_TRIAL_ID) == []


# --- LIVE: one bounded A5 run (opt-in, reviewed by reading otherwise) -------


@_skip_no_live
def test_live_a5_runs_one_precanned_call_and_emits_a_gate_event() -> None:
    """LIVE: a single bounded A5 pre-canned call on the seed instance.

    Asserts the arm produces a CODE candidate patch within the small budget cap
    and that the captured certificate yields >= 1 GateEvent — the fast,
    bounded gate-emission witness. Skipped by default; reviewed by reading the
    ``_run_a5`` path when Docker/creds are absent.
    """
    instance = load_instance(TEXT_TOOLKIT_SLUG)
    backend = ContainerRunBackend(trial_id=_TRIAL_ID)
    bundle, patch = backend.run(instance, A5)
    assert bundle.telemetry.costUsd <= A5_MAX_BUDGET_USD
    assert isinstance(patch, str) and patch.strip() != ""
    assert len(backend.last_gate_events) >= 1
