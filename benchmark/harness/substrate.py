"""The substrate decision: BenchFlow ``bench`` SDK vs. the local backend seam.

``05-harness-architecture.md`` §Substrate names the **BenchFlow ``bench`` SDK**
as the harness substrate, on the assumption that BenchFlow can host this
benchmark's custom ``TaskInstance`` schema, per-arm provisioning, and the
two-container run/scoring split without a fork. Task 01 investigates that
assumption against the published package (PyPI ``benchflow==0.4.0``) and records
what actually holds, so later milestones build on a confirmed footing rather
than the original guess.

Summary of the finding (investigated 2026-05-27, ``benchflow==0.4.0``):

- The package IS the substrate the spec names: its ``bench`` CLI exposes
  ``bench tasks init`` / ``bench tasks check`` (task scaffolding + structural
  validation) and ``bench eval create`` (evaluation execution over a tasks
  directory or a remote source repo such as ``benchflow-ai/skillsbench``). A
  trivial task scaffolded with ``bench tasks init`` passes ``bench tasks check``
  with no Docker daemon present (``check`` is a pure structural validator).
- ``bench tasks check`` validates a **fixed** task layout, not a custom schema:
  required ``task.toml`` + ``instruction.md`` + ``environment/``, with optional
  ``tests/`` (the verifier) and ``solution/`` (the oracle). See
  ``REQUIRED_TASK_FILES`` / ``REQUIRED_TASK_DIRS`` below, mirrored from
  ``benchflow._utils.task_authoring``. The benchmark's richer ``TaskInstance``
  (``benchmark.harness.domain``) is therefore carried by the benchmark itself,
  not by BenchFlow's task schema; a per-instance ``task.toml`` would be a
  generated *projection* of a ``TaskInstance``, not its source of truth.
- BenchFlow's eval model is a **single-sandbox rollout**: the agent runs in the
  task's one environment (``--sandbox docker|daytona|modal``), then the verifier
  (``tests/test.sh``, writing a reward to ``/logs/verifier/reward.txt``) runs to
  produce the reward. The verifier shares that one environment with the agent;
  the SDK does NOT natively stand up a *second, clean* scoring container into
  which hidden tests are injected after the agent finishes. The spec's
  two-container integrity rule (``05-harness-architecture.md`` §Scoring
  isolation) is thus NOT expressible by BenchFlow's stock eval model alone — it
  needs the thin wrapper this benchmark already owns.

Decision recorded here and in the plan's Open questions: the benchmark keeps its
own ``RunBackend`` / ``ScoringBackend`` seam (``benchmark.harness.backends``,
built in M0) as the substrate for the two-container split and the custom schema,
and treats BenchFlow as a *complementary* layer for task authoring/validation
and ACP-agent rollouts where those fit. ``bench tasks check`` is a usable
structural gate; the run/scoring isolation and the ``TaskInstance`` schema stay
on the benchmark's seam. This module is the durable record of that split; it
holds no runtime logic.
"""

from __future__ import annotations

#: Whether the BenchFlow ``bench tasks init`` / ``bench tasks check`` CLI is
#: present and usable for structural task validation. Confirmed for
#: ``benchflow==0.4.0`` (``bench tasks check`` validates a trivial task with no
#: Docker daemon). The benchmark may use it as a structural gate.
BENCH_TASKS_CLI_AVAILABLE: bool = True

#: Whether BenchFlow's stock eval model can express the spec's two-CONTAINER
#: run/scoring split (a separate clean scoring environment with hidden tests
#: injected only there) WITHOUT a wrapper. It cannot: BenchFlow runs the agent
#: and the verifier in the SAME sandbox, so the split is owned by the
#: benchmark's own ``RunBackend`` / ``ScoringBackend`` seam.
BENCH_NATIVE_TWO_CONTAINER_SPLIT: bool = False

#: Whether ``bench tasks check`` validates this benchmark's custom
#: ``TaskInstance`` schema. It does not: ``check`` validates BenchFlow's own
#: fixed task layout (below). The ``TaskInstance`` schema is owned by
#: ``benchmark.harness.domain``; a per-instance ``task.toml`` would be a
#: generated projection of a ``TaskInstance``, not the schema authority.
BENCH_VALIDATES_TASKINSTANCE_SCHEMA: bool = False

#: The files BenchFlow's ``bench tasks check`` requires in a task directory,
#: mirrored from ``benchflow._utils.task_authoring.REQUIRED_FILES`` (v0.4.0).
REQUIRED_TASK_FILES: tuple[str, ...] = ("task.toml", "instruction.md")

#: The directories BenchFlow's ``bench tasks check`` requires, mirrored from
#: ``benchflow._utils.task_authoring.REQUIRED_DIRS`` (v0.4.0). ``tests/`` (the
#: verifier) and ``solution/`` (the oracle) are validated when present but are
#: not required by ``check`` itself.
REQUIRED_TASK_DIRS: tuple[str, ...] = ("environment",)


def benchflow_version() -> str:
    """Return the installed ``benchflow`` distribution version.

    Confirms the locked BenchFlow substrate is importable as a distribution. A
    plain attribute read is avoided because the package exposes no public
    ``__version__``; the distribution metadata is the authoritative version.
    """
    from importlib.metadata import version

    return version("benchflow")
