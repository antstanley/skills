"""The OPT-IN live gate probe: inject a known defect, run a gate, set caughtBy.

The ONE live piece of the gate-catch-rate mechanism. Everything else in
:mod:`benchmark.harness.scoring.probes` is pure computation; this module runs a
REAL gate (a bounded host-side ``claude -p`` carrying the semi-formal-review
correctness rubric) over a manufactured known-bad patch and records whether the
gate flagged it (``InjectedDefect.caughtBy`` set) or it escaped (``None``).

It is gated behind the opt-in env :data:`LIVE_PROBE_ENV` and is BOUNDED — one
small ``claude -p`` call per defect, capped at :data:`PROBE_MAX_BUDGET_USD`,
under :data:`PROBE_TIMEOUT_SECONDS`. It NEVER sees the hidden suite: it injects a
classified mutation into the (correct) reference solution and asks the gate to
review the diff. The defect is a genuine fault of its kind (see
:data:`~benchmark.harness.scoring.probes.defects.DEFECT_MUTATIONS`), so a working
correctness gate should flag it.

The gate verdict is mapped onto the closed gate verdicts (mirroring
``benchmark.harness.arms.a2_a3``): CORRECT / LIKELY_CORRECT means the gate PASSED
the defect (it ESCAPED); CONCERNS / BUGGY means the gate CAUGHT it. A caught
defect's ``caughtBy`` is set to the gate kind ``semi-formal-review``.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable

from benchmark.harness.arms.a2_a3 import GATE_KIND_REVIEW
from benchmark.harness.domain import InjectedDefect
from benchmark.harness.scoring.probes.defects import (
    DefectMutation,
    make_injected_defect,
)

# --- opt-in / bounding constants --------------------------------------------

#: The opt-in env var gating the live probe. Unset / != "1" -> skip (CI, routine
#: ``check.sh``). Mirrors the other live opt-ins (``BENCHMARK_RUN_*_LIVE``).
LIVE_PROBE_ENV = "BENCHMARK_RUN_GATE_PROBE_LIVE"

#: Fixed model alias the gate runs on (matches the rest of the harness).
PROBE_MODEL = "sonnet"

#: SMALL hard per-defect budget ceiling (USD): one focused review call, not a
#: recursive agent, so a tiny cap is the honest safety rail.
PROBE_MAX_BUDGET_USD = 1.0

#: Wall-clock ceiling (seconds) for the single ``claude -p`` review call.
PROBE_TIMEOUT_SECONDS = 240

#: ``claude`` exit code meaning the headless run completed.
_CLAUDE_EXIT_OK = 0

#: The discharged semi-formal-review verdicts that mean the gate CAUGHT the
#: defect (a non-passing verdict). CORRECT / LIKELY_CORRECT mean it escaped.
_CAUGHT_VERDICTS = frozenset({"CONCERNS", "BUGGY"})

#: Verdict line the review emits: ``VERDICT: CORRECT|LIKELY_CORRECT|CONCERNS|
#: BUGGY`` (mirrors ``a2_a3._REVIEW_VERDICT_RE``).
_REVIEW_VERDICT_RE = re.compile(
    r"\bVERDICT:\s*(CORRECT|LIKELY_CORRECT|CONCERNS|BUGGY)\b", re.IGNORECASE
)


class GateProbeError(RuntimeError):
    """Raised when the live gate probe cannot run or its output is unparseable."""


#: A reviewer callable: takes the review prompt, returns the gate's verdict text.
#: Injectable so tests can drive the mapping deterministically; the live default
#: is :func:`cli_review_gate`.
GateReviewer = Callable[[str], str]


# --- the review prompt -------------------------------------------------------

#: The correctness-review instruction the probe hands the gate. It asks for the
#: closed verdict line the harness already parses, so the probe and the organic
#: A2 certificates speak the same verdict vocabulary.
_REVIEW_INSTRUCTION = (
    "You are a correctness reviewer applying a semi-formal review to a code "
    "change. The change is a unified diff against a known-correct baseline. "
    "Decide whether the change is CORRECT, or whether it introduces a defect. "
    "Reason about boundary conditions, dropped branches, and return values. "
    "End your reply with EXACTLY one line of the form "
    "'VERDICT: CORRECT' or 'VERDICT: LIKELY_CORRECT' or 'VERDICT: CONCERNS' or "
    "'VERDICT: BUGGY'."
)


def build_review_prompt(diff_text: str, mutation: DefectMutation) -> str:
    """Build the review prompt for a defect-injected ``diff_text``.

    Carries the correctness instruction and the diff; deliberately does NOT name
    the injected fault (the gate must find it unaided). The targeted component is
    given only as orienting context.
    """
    return (
        f"{_REVIEW_INSTRUCTION}\n\n"
        f"The change touches the `{mutation.component}` component.\n\n"
        "Diff under review:\n\n"
        f"```diff\n{diff_text}\n```\n"
    )


def _shell_quote(value: str) -> str:
    """Single-quote ``value`` for a POSIX ``sh -c`` command line."""
    return "'" + value.replace("'", "'\\''") + "'"


def cli_review_gate(prompt: str) -> str:
    """The live default reviewer: ONE bounded host-side ``claude -p`` call.

    Runs ``claude -p <prompt> --model sonnet --max-budget-usd <CAP>
    --output-format json`` on the HOST and returns the model's ``result`` text.
    Raises :class:`GateProbeError` on a non-zero exit or an unparseable envelope.
    """
    command = (
        f"claude -p {_shell_quote(prompt)} "
        f"--model {PROBE_MODEL} "
        f"--max-budget-usd {PROBE_MAX_BUDGET_USD} --output-format json"
    )
    result = subprocess.run(
        ["sh", "-c", command],
        capture_output=True,
        text=True,
        timeout=PROBE_TIMEOUT_SECONDS,
    )
    if result.returncode != _CLAUDE_EXIT_OK:
        raise GateProbeError(
            f"gate probe claude -p failed (exit {result.returncode}).\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    try:
        envelope = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise GateProbeError(
            f"could not parse claude --output-format json envelope:\n{result.stdout}"
        ) from exc
    if not isinstance(envelope, dict) or "result" not in envelope:
        raise GateProbeError(f"claude JSON envelope missing 'result': {envelope!r}")
    inner = envelope["result"]
    if not isinstance(inner, str):
        raise GateProbeError(f"claude 'result' was not a string: {inner!r}")
    return inner


def verdict_caught(verdict_text: str) -> bool:
    """Whether a review verdict text means the gate CAUGHT the defect.

    Parses the ``VERDICT:`` line; CONCERNS / BUGGY -> caught; CORRECT /
    LIKELY_CORRECT -> escaped. A reply with no parseable verdict is treated as
    NOT caught (the gate did not flag it) — the honest, conservative reading.
    """
    match = _REVIEW_VERDICT_RE.search(verdict_text)
    if match is None:
        return False
    return match.group(1).upper() in _CAUGHT_VERDICTS


def run_gate_probe(
    task_instance: str,
    diff_text: str,
    mutation: DefectMutation,
    *,
    reviewer: GateReviewer = cli_review_gate,
) -> InjectedDefect:
    """Run ONE defect through the real review gate; return the InjectedDefect.

    Builds the review prompt for the known-bad ``diff_text`` (the reference
    solution mutated by ``mutation``), runs it through ``reviewer`` (the live
    :func:`cli_review_gate` by default; an injected callable in tests), and mints
    an :class:`InjectedDefect` whose ``caughtBy`` is the review gate kind when the
    gate flagged it, else ``None`` (it escaped). The ``reviewer`` is injectable so
    the mapping is testable WITHOUT spending budget.
    """
    prompt = build_review_prompt(diff_text, mutation)
    verdict_text = reviewer(prompt)
    caught = verdict_caught(verdict_text)
    return make_injected_defect(
        task_instance,
        mutation.defect_kind,
        caught_by=GATE_KIND_REVIEW if caught else None,
    )
