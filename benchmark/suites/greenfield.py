"""The ``greenfield-features`` suite: Commit0-style build-from-spec instances.

See ``.specs/benchmark/specs/03-task-suites.md`` §Suite: ``greenfield-features``
and ``05-harness-architecture.md`` §Run container. Each instance is a prose
specification of a MULTI-COMPONENT feature/small library, starting from a
skeleton repo at a fixed commit; resolution is decided by a WITHHELD acceptance
test suite the arms never see.

Layout (mirrors the ``base/`` + ``hidden/`` split the local ScoringBackend and
the container backends both expect — see
``benchmark/harness/scoring/local.py`` ``REPO_BASE_SUBDIR`` / ``REPO_HIDDEN_SUBDIR``)::

    greenfield-features/
      <slug>/
        repo/
          base/      # run-visible skeleton: package layout + TODO stubs + a
                     # passToPass smoke test that already passes
          hidden/    # withheld acceptance suite = failToPass (scoring-side only)
        reference/   # OPTIONAL private reference solution (self-test instances)

Each instance loads as a validated :class:`TaskInstance` with:

- ``goldPatch = None`` — greenfield has no single arms-visible reference;
- ``contaminationTier = "authored-private"`` — authored fresh, kept private;
- ``headlessVerifiable = True`` — the hidden pytest oracle runs without a human;
- ``testTags`` mapping every hidden selector to the component/spec section it
  exercises, enabling per-task escape attribution (task 14);
- ``dockerImage`` set to the RUN image tag the two-image build produces
  (``greenfield-<slug>:run``), which excludes the hidden tests.

The private reference solution (where present) is loaded by
:func:`load_reference_solution` — deliberately NOT carried in the arms-visible
``TaskInstance.goldPatch`` field, which stays ``None``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from benchmark.harness.domain import TaskInstance

# --- named constants -------------------------------------------------------

#: Scoring-side subdir the hidden suite is injected at inside the checkout, and
#: thus the prefix every hidden selector carries. Mirrors
#: ``benchmark.harness.scoring.local.REPO_HIDDEN_SUBDIR`` (kept as a literal here
#: to avoid a heavy import cycle through the backends package at suite-load time;
#: a suite test asserts the two stay in sync).
REPO_HIDDEN_SUBDIR = "hidden"

#: Directory of the ``benchmark/suites`` package this loader lives in.
SUITES_DIR = Path(__file__).resolve().parent

#: Directory holding the bundled greenfield instances (hyphenated to match the
#: suite slug and the spec's ``benchmark/suites/greenfield-features/`` path).
SUITE_DIR = SUITES_DIR / "greenfield-features"

#: Suite slug, mirrored from ``Suite.slug`` / ``03-task-suites.md``.
SUITE_SLUG = "greenfield-features"

#: Per-instance ``repo/`` subdir holding the ``base/`` + ``hidden/`` trees.
REPO_SUBDIR = "repo"

#: Per-instance subdir holding a private reference solution (self-test only).
REFERENCE_SUBDIR = "reference"

#: File name of a private reference solution under :data:`REFERENCE_SUBDIR`.
REFERENCE_PATCH_NAME = "solution.patch"

#: Per-instance subdir holding the FROZEN given-spec handed to arms A2 and A3.
#: A single authored spec, produced once to the fixed quality bar documented in
#: ``benchmark/harness/arms/a2_a3.py`` and consumed IDENTICALLY by both A2 and
#: A3 (so spec variance never leaks into the A1−A2 or A2−A3 deltas).
GIVEN_SPEC_SUBDIR = "given_spec"

#: File name of the frozen given-spec under :data:`GIVEN_SPEC_SUBDIR`.
GIVEN_SPEC_NAME = "given_spec.md"

#: A fixed, synthetic commit id. The skeleton repos are content-addressed by
#: their bundled ``base/`` trees, not a real git history, so this is a stable
#: placeholder satisfying the ``baseCommit`` pattern (7-40 hex chars).
BASE_COMMIT = "0000000"

#: Shared contamination tier for every greenfield instance.
CONTAMINATION_TIER = "authored-private"

#: Template for the per-instance RUN image tag (hidden tests EXCLUDED). The
#: two-image build (``benchmark/suites/greenfield_images.py``) produces it.
RUN_IMAGE_TAG_TEMPLATE = "greenfield-{slug}:run"


def _hidden_selector(test_file: str, test_name: str) -> str:
    """Build a hidden pytest node id relative to the scoring checkout root.

    The local ScoringBackend injects the ``hidden/`` tree at ``hidden/`` inside
    the checkout, so a selector is ``hidden/<file>::<test>`` and resolves
    verbatim.
    """
    return f"{REPO_HIDDEN_SUBDIR}/{test_file}::{test_name}"


@dataclass(frozen=True)
class GreenfieldInstanceSpec:
    """Static description of one bundled greenfield instance.

    Holds everything :func:`load_instance` needs to build a validated
    :class:`TaskInstance`, plus the human-facing component list used by the
    suite tests to assert multi-component coverage.
    """

    #: Instance slug (also the per-instance directory name under the suite).
    slug: str
    #: The prose specification seed handed to the arms.
    problem_statement: str
    #: Component/spec-section names this instance builds (>= 2 -> multi-component).
    components: tuple[str, ...]
    #: Hidden ``failToPass`` selectors -> the component/spec section each tags.
    fail_to_pass_tags: tuple[tuple[str, str], ...]
    #: Skeleton smoke ``passToPass`` selectors (already pass on the skeleton).
    pass_to_pass: tuple[str, ...]
    #: ``True`` iff this instance ships a private reference solution.
    has_reference_solution: bool

    @property
    def instance_dir(self) -> Path:
        return SUITE_DIR / self.slug

    @property
    def repo_source_dir(self) -> Path:
        return self.instance_dir / REPO_SUBDIR

    @property
    def run_image_tag(self) -> str:
        return RUN_IMAGE_TAG_TEMPLATE.format(slug=self.slug)


# --- instance: text-toolkit (the self-test instance) -----------------------

TEXT_TOOLKIT_SLUG = "greenfield__text_toolkit__0001"

TEXT_TOOLKIT_PROBLEM_STATEMENT = (
    "Build `text_toolkit`, a small text-processing library with four "
    "interlocking components. Implement each stub in the skeleton package so "
    "the public API works end to end.\n\n"
    "1. `tokenizer.tokenize(text) -> list[str]`: split `text` into word tokens "
    "on any run of non-alphanumeric characters, preserving original case and "
    "dropping empty tokens.\n"
    "2. `normalizer.normalize(tokens) -> list[str]` (uses the tokenizer's "
    "output): lowercase each token and remove the stop words "
    "{a, an, the, of, and, to, in}, preserving the order of survivors.\n"
    "3. `frequency.word_counts(text) -> dict[str, int]` and "
    "`frequency.top_terms(text, limit) -> list[tuple[str, int]]` (compose the "
    "tokenizer and normalizer): count normalized terms; `top_terms` returns the "
    "`limit` most frequent (term, count) pairs sorted by count descending, "
    "ties broken by term ascending.\n"
    "4. `pipeline.summarize(text, limit) -> dict` (orchestrates all three): "
    "return {'tokens': <raw token count>, 'terms': <distinct normalized term "
    "count>, 'top': top_terms(text, limit)}.\n\n"
    "The package's `__init__` re-exports tokenize, normalize, word_counts, "
    "top_terms, and summarize. A withheld acceptance suite decides resolution."
)

TEXT_TOOLKIT_SPEC = GreenfieldInstanceSpec(
    slug=TEXT_TOOLKIT_SLUG,
    problem_statement=TEXT_TOOLKIT_PROBLEM_STATEMENT,
    components=("tokenizer", "normalizer", "frequency", "pipeline"),
    fail_to_pass_tags=(
        (
            _hidden_selector("test_tokenizer.py", "test_splits_on_whitespace"),
            "tokenizer",
        ),
        (
            _hidden_selector(
                "test_tokenizer.py", "test_splits_on_punctuation_and_drops_empties"
            ),
            "tokenizer",
        ),
        (
            _hidden_selector("test_tokenizer.py", "test_preserves_case_and_digits"),
            "tokenizer",
        ),
        (
            _hidden_selector("test_tokenizer.py", "test_empty_text_yields_no_tokens"),
            "tokenizer",
        ),
        (
            _hidden_selector("test_normalizer.py", "test_lowercases_tokens"),
            "normalizer",
        ),
        (_hidden_selector("test_normalizer.py", "test_drops_stop_words"), "normalizer"),
        (
            _hidden_selector("test_normalizer.py", "test_preserves_order_of_survivors"),
            "normalizer",
        ),
        (
            _hidden_selector("test_normalizer.py", "test_empty_input_yields_empty"),
            "normalizer",
        ),
        (
            _hidden_selector(
                "test_frequency.py", "test_word_counts_uses_normalized_terms"
            ),
            "frequency",
        ),
        (
            _hidden_selector("test_frequency.py", "test_word_counts_empty_text"),
            "frequency",
        ),
        (
            _hidden_selector(
                "test_frequency.py", "test_top_terms_orders_by_count_then_term"
            ),
            "frequency",
        ),
        (
            _hidden_selector(
                "test_frequency.py", "test_top_terms_breaks_ties_alphabetically"
            ),
            "frequency",
        ),
        (
            _hidden_selector("test_frequency.py", "test_top_terms_respects_limit"),
            "frequency",
        ),
        (
            _hidden_selector(
                "test_pipeline.py", "test_summarize_reports_token_and_term_counts"
            ),
            "pipeline",
        ),
        (_hidden_selector("test_pipeline.py", "test_summarize_empty_text"), "pipeline"),
    ),
    pass_to_pass=(
        "test_smoke.py::test_public_api_is_exposed",
        "test_smoke.py::test_component_modules_import",
    ),
    has_reference_solution=True,
)


# --- instance: task-scheduler ----------------------------------------------

SCHEDULER_SLUG = "greenfield__scheduler__0001"

SCHEDULER_PROBLEM_STATEMENT = (
    "Build `task_scheduler`, a tiny dependency-aware task scheduler with four "
    "interlocking components. Implement each stub in the skeleton package.\n\n"
    "1. `graph.DependencyGraph`: `add_task(name, depends_on=None)` registers a "
    "task and its prerequisite names (default none); re-adding a task replaces "
    "its prerequisites without duplicating it. `tasks()` returns task names in "
    "insertion order. `prerequisites(name)` returns the declared prerequisite "
    "list.\n"
    "2. `topo.topological_order(graph) -> list[str]` (uses the graph): return "
    "every task once, each after all its prerequisites, breaking ties by "
    "insertion order (Kahn's algorithm) so the result is deterministic.\n"
    "3. `validators.missing_dependencies(graph) -> list[str]` and "
    "`validators.find_cycle(graph) -> list[str] | None` (use the graph): the "
    "first returns the sorted, de-duplicated prerequisite names never "
    "registered as tasks; the second returns a task-name list forming a cycle, "
    "or None when acyclic.\n"
    "4. `scheduler.schedule(graph) -> list[str]` (composes topo + validators): "
    "raise `scheduler.ScheduleError` if the graph has missing dependencies or a "
    "cycle, otherwise return `topological_order(graph)`.\n\n"
    "The package's `__init__` re-exports DependencyGraph, topological_order, "
    "missing_dependencies, find_cycle, and schedule. A withheld acceptance "
    "suite decides resolution."
)

SCHEDULER_SPEC = GreenfieldInstanceSpec(
    slug=SCHEDULER_SLUG,
    problem_statement=SCHEDULER_PROBLEM_STATEMENT,
    components=("graph", "topo", "validators", "scheduler"),
    fail_to_pass_tags=(
        (
            _hidden_selector("test_graph.py", "test_tasks_preserve_insertion_order"),
            "graph",
        ),
        (
            _hidden_selector("test_graph.py", "test_prerequisites_default_to_empty"),
            "graph",
        ),
        (_hidden_selector("test_graph.py", "test_prerequisites_round_trip"), "graph"),
        (
            _hidden_selector("test_graph.py", "test_re_adding_replaces_prerequisites"),
            "graph",
        ),
        (_hidden_selector("test_topo.py", "test_orders_simple_chain"), "topo"),
        (
            _hidden_selector("test_topo.py", "test_respects_dependencies_in_diamond"),
            "topo",
        ),
        (
            _hidden_selector(
                "test_topo.py", "test_is_deterministic_by_insertion_order"
            ),
            "topo",
        ),
        (
            _hidden_selector(
                "test_validators.py", "test_missing_dependencies_sorted_and_unique"
            ),
            "validators",
        ),
        (
            _hidden_selector("test_validators.py", "test_no_missing_dependencies"),
            "validators",
        ),
        (
            _hidden_selector(
                "test_validators.py", "test_find_cycle_returns_none_when_acyclic"
            ),
            "validators",
        ),
        (
            _hidden_selector("test_validators.py", "test_find_cycle_detects_a_cycle"),
            "validators",
        ),
        (
            _hidden_selector(
                "test_scheduler.py", "test_schedule_returns_topological_order"
            ),
            "scheduler",
        ),
        (
            _hidden_selector(
                "test_scheduler.py", "test_schedule_rejects_missing_dependency"
            ),
            "scheduler",
        ),
        (
            _hidden_selector("test_scheduler.py", "test_schedule_rejects_cycle"),
            "scheduler",
        ),
    ),
    pass_to_pass=(
        "test_smoke.py::test_public_api_is_exposed",
        "test_smoke.py::test_component_modules_import",
    ),
    has_reference_solution=False,
)


#: Every bundled instance spec, in a stable order.
INSTANCE_SPECS: tuple[GreenfieldInstanceSpec, ...] = (
    TEXT_TOOLKIT_SPEC,
    SCHEDULER_SPEC,
)

#: Specs keyed by slug for :func:`load_instance` / :func:`get_spec`.
_SPECS_BY_SLUG = {spec.slug: spec for spec in INSTANCE_SPECS}


def get_spec(slug: str) -> GreenfieldInstanceSpec:
    """Return the :class:`GreenfieldInstanceSpec` for ``slug`` (or raise)."""
    try:
        return _SPECS_BY_SLUG[slug]
    except KeyError as exc:
        known = ", ".join(sorted(_SPECS_BY_SLUG))
        raise KeyError(f"unknown greenfield instance {slug!r}; known: {known}") from exc


def _build_instance(spec: GreenfieldInstanceSpec) -> TaskInstance:
    """Construct (and thereby validate) one greenfield :class:`TaskInstance`."""
    fail_to_pass = [selector for selector, _tag in spec.fail_to_pass_tags]
    test_tags = {selector: tag for selector, tag in spec.fail_to_pass_tags}
    return TaskInstance(
        slug=spec.slug,
        suite=SUITE_SLUG,
        repo=str(spec.repo_source_dir),
        baseCommit=BASE_COMMIT,
        problemStatement=spec.problem_statement,
        failToPass=fail_to_pass,
        passToPass=list(spec.pass_to_pass),
        contaminationTier=CONTAMINATION_TIER,
        headlessVerifiable=True,
        goldPatch=None,
        testTags=test_tags,
        dockerImage=spec.run_image_tag,
    )


def load_instance(slug: str) -> TaskInstance:
    """Return the validated greenfield :class:`TaskInstance` named ``slug``."""
    return _build_instance(get_spec(slug))


def load_instances() -> list[TaskInstance]:
    """Return every bundled greenfield :class:`TaskInstance`, validated."""
    return [_build_instance(spec) for spec in INSTANCE_SPECS]


def given_spec_path(slug: str) -> Path:
    """Return the path to ``slug``'s frozen A2/A3 given-spec file."""
    return get_spec(slug).instance_dir / GIVEN_SPEC_SUBDIR / GIVEN_SPEC_NAME


def load_given_spec(slug: str) -> str:
    """Return the frozen given-spec markdown handed to arms A2 and A3 for ``slug``.

    This is the ready-made spec the A2/A3 recipes write into the run container
    under ``.specs/`` BEFORE the workflow runs (replacing the spec-creator
    stage). It is authored ONCE per instance to a fixed, documented quality bar
    (``benchmark.harness.arms.a2_a3.GIVEN_SPEC_QUALITY_BAR``) and is consumed
    identically by both arms, so spec variance does not leak into the deltas.

    Raises ``FileNotFoundError`` for instances that ship no given-spec.
    """
    return given_spec_path(slug).read_text(encoding="utf-8")


def reference_solution_path(slug: str) -> Path:
    """Return the path to ``slug``'s private reference solution patch file."""
    return get_spec(slug).instance_dir / REFERENCE_SUBDIR / REFERENCE_PATCH_NAME


def load_reference_solution(slug: str) -> str:
    """Return the private reference-solution patch text for ``slug``.

    This patch is deliberately NOT exposed via ``TaskInstance.goldPatch`` (which
    stays ``None`` for every greenfield instance); it lives only under the
    instance's ``reference/`` directory for self-test verification.

    Raises ``FileNotFoundError`` for instances that ship no reference solution.
    """
    path = reference_solution_path(slug)
    return path.read_text(encoding="utf-8")
