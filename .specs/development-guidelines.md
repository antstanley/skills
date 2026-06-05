# Development Guidelines

**Status:** Draft · **Date:** 2026-05-27 · **Owner:** Ant Stanley · **Scope:** Repo-wide

The rules of the road for everyone — humans and agents — writing code in this repository. They cover the toolchain, the pervasive coding style, where and how to handle errors, limits, version control, the per-language conventions, testing, repository hygiene, the emphases that matter most for AI agents, and the definition of done. The body states the discipline the repo adopts; tooling or gates that are not yet wired up live in the closing Open questions, not the body.

The repository is a Claude Code plugin marketplace; its only executable code today is the Python benchmark harness ([.specs/benchmark/specs/](benchmark/specs/)), so the per-language conventions below are Python's. Additional language sections are added here when another language enters the repo.

---

## Toolchain

The tools actually in use. Each is wired into the repo today; planned-but-unwired tooling is in Open questions.

| Tool | Version / channel | Notes |
|---|---|---|
| Python | 3.13 | pinned in `.python-version` and `pyproject.toml` (`requires-python = ">=3.13"`) |
| uv | latest | package manager and runner; dependencies locked in `uv.lock`, run via `uv run …` |
| Ruff | latest (`>=0.6`) | linter and formatter both; lint rule set `E, F, I, UP, B` (`[tool.ruff.lint]`) |
| pytest | latest (`>=8.0`) | test runner; `testpaths = ["benchmark/tests"]` |
| pyright | latest (`>=1.1.409`) | type checker, standard mode (`[tool.pyright]`); checks library code, excludes the test suite and the bundled fixture repo |
| jujutsu (`jj`) | latest | version-control front end (see [Version control](#version-control)) |
| Docker | peer dependency (≥ 25) | runtime for the benchmark's `container` backend (run/scoring on the SWE-bench Pro and greenfield suites); **not** required for local development, the test suite, or the Docker-free `local` backend / M0 pipeline |

Pervasive coding style: **Clean Code** (below). The format / lint / type-check / test gate is run by a pre-push hook and by CI (see [Repository hygiene](#repository-hygiene)).

Docker is a **peer dependency**, not part of the locked Python toolchain: it is installed and managed at the OS level (`dnf install docker` on Amazon Linux 2023), and only the `container` backend needs it. Everything in this guideline — format, lint, type-check, tests, and the M0 local pipeline — runs without it.

---

## Clean Code — the pervasive style

This project adopts **Clean Code** as its pervasive coding style. This is the default, not a recommendation. Deviations require a written reason in the change description.

The short form: **make the code reveal its intent.** A reader should understand a unit from its name and shape without tracing it. Prefer clarity to cleverness.

The design priority — **readability and maintainability first** — applies throughout. When a clever construction and a clear one compete, the clear one wins even at a cost in lines.

Load-bearing principles:

- **Meaningful names.** Intention-revealing, pronounceable, searchable. The name states what a thing is or does; no encodings, no abbreviations that need a key.
- **Small functions that do one thing.** A function operates at a single level of abstraction. Few parameters (prefer 0–2; avoid boolean flag arguments — they signal a function doing two things). No hidden side effects; separate commands from queries.
- **Single responsibility.** A module has one reason to change. High cohesion, low coupling. Depend on abstractions, not concretions — the driver depends on the `RunBackend` / `ScoringBackend` protocols, not on a concrete backend ([.specs/benchmark/specs/05-harness-architecture.md](benchmark/specs/05-harness-architecture.md) → Backends).
- **No duplication (DRY).** Duplicated logic has one home — tempered by judgment: prefer a little duplication over the wrong abstraction. The resolution rule lives once in `benchmark/harness/scoring/resolution.py` and both backends call it.
- **Self-documenting code; comments are a last resort.** A comment is often a failure to express something in code. Good comments explain *why* or warn of consequences; they never paraphrase the code, and commented-out code is deleted.

---

## Error handling and boundaries

### Where validation lives

Validate where data crosses from a place you do not control into one you do, and translate the failure into the repo's own vocabulary at that line.

| Boundary | What to validate | How |
|---|---|---|
| Inbound record (construct / `from_dict`) | Entity shape, required fields, enums, ID format | Validate against [`canonical-types.schema.json`](benchmark/specs/canonical-types.schema.json) on construction and on load; reject with a typed `DomainValidationError` naming the entity and field |
| JSONL instance file → harness | Per-record round-trip integrity | Re-validate each record on read; raise on the first malformed record rather than best-effort parsing |
| Run side ↔ scoring side (the backend seam) | The integrity rule | The run environment never carries hidden test content; hidden `failToPass` / `passToPass` are injected only on the scoring side ([05-harness-architecture.md](benchmark/specs/05-harness-architecture.md) → Scoring isolation) |
| Subprocess result (local `pytest` run) | Exit status and per-selector outcome | Interpret the documented exit codes explicitly; an unexpected code is an infra fault, distinct from a legitimate `resolved: false` |

### Error handling in Python

- Raise specific exception types with context, rooted in a small exception hierarchy under one project base exception (e.g. `DomainValidationError(ValueError)`).
- **Never return `None` as an error signal.** Raise, or return an explicit `Optional`/`Result`-style object whose meaning is unambiguous. (A `None` `candidatePatch` is a deliberate, documented value — the no-op patch — not an error code.)
- Catch the narrowest exception type; handle it or re-raise with added context. Never a bare `except:`.
- Wrap third-party clients behind a repo-owned module that translates their exceptions into the project's own.

### Use exceptions, not return codes

- Signal failure with exceptions, not error codes a caller may forget to check.
- Write the `try/except/finally` first; it defines the scope of what can fail. Clean up temp working directories in `finally`.
- Throw exceptions carrying enough **context** to locate the cause — the operation that failed and why. Never log a secret in that context.
- **Do not return `None`; do not pass `None`.** Return an empty collection or an explicit optional. A `None` that escapes is a future crash with no context.

### Make intent explicit

- Prefer types that make an invalid value hard to construct — frozen dataclasses for value objects, enums or closed string sets over free strings — so fewer states need runtime guarding.
- When behaviour is hard to read, the fix is a better name or a smaller function — not a comment.
- Match exhaustively over enums / closed sets; the unexpected case raises rather than falling through.

---

## Limits and bounds

Magic numbers are replaced with **named constants** that state their meaning. Any genuine limit — pool sizes, timeouts, retry counts, collection cardinality, ID prefixes — is a named constant referenced wherever it applies, not a literal (the harness already follows this: `DEFAULT_POOL_SIZE`, `PYTEST_TIMEOUT_SECONDS`, `RUN_TEMP_BASE` / `SCORING_TEMP_BASE`, the `*_ID_PREFIX` set). The *existence* of a limit as a named constant is the rule here; concrete values are an app concern and live in the per-app specs ([.specs/benchmark/specs/](benchmark/specs/)).

---

## Version control

### Shared core (any VCS)

- **Commits are small and well-described.** One coherent change per commit. Squash noise before pushing.
- **Empty commit descriptions are not accepted.** Describe the *why* before pushing.
- **Conventional Commits** for the subject line: `type(scope): subject`, types from the standard set (`feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `build`, `ci`, `perf`, `style`).
- **Branch model.** The integration line (`main`) stays releasable. Feature work happens on named bookmarks; pull requests target the integration line.
- **Do not rewrite published history** unless the change is yours and unmerged. If a force-push is required, call it out.
- **Destructive operations need explicit confirmation** — history rewrites, bookmark deletion, hard resets, force-fetches — even when they look like the cleanest path.

### Variant — jujutsu

This repo is jj-managed (`.jj/` present; a `.git/` backend also exists, but `jj` is the front end).

- **`jj` is the sole version-control front end.** Do not run `git commit` / `git add` / `git status` against the working copy — the index/working-copy mismatch is exactly what jj removes.
- **Describe before pushing.** `jj describe` sets the *why*; an empty description blocks the push.
- **Feature work happens on named bookmarks** (`jj bookmark create feat/x`); pull requests are pushed with `jj git push`.
- **Resolve conflicts in jj** (`jj resolve`), not by editing plain-text markers.
- **Destructive `jj` operations need explicit confirmation** — `jj abandon`, `jj op restore`, force-fetches, bookmark deletion — even when they look like the cleanest path.
- The `.jj/` directory is local; it is not committed.

---

## Python conventions

### Formatting and linting

- The formatter (`uv run ruff format`) runs clean before commit; it owns line length and layout.
- The linter (`uv run ruff check`) runs clean before commit with warnings treated as errors; the rule set (`E, F, I, UP, B`) is declared in `pyproject.toml`.
- The type checker (`uv run pyright`, standard mode) runs clean before push and in CI; it checks the library code, with the test suite and the bundled fixture repo excluded.

### Code style

- **Type-annotate everything public.** No untyped public function; no implicit `Any`.
- **`@dataclass(frozen=True)`** for value objects, so invalid mutation raises rather than corrupting state; validate the record against the canonical schema in `__post_init__` and on load.
- **Closed string sets / enums for state, not free strings;** the unexpected value raises.
- **Validate at boundaries.** Inbound JSON is parsed into a typed record that validates against `canonical-types.schema.json`; no trusting a raw `dict`.
- **Errors are explicit.** Raise typed exceptions; never swallow with a bare `except:`. Catch the narrowest type and handle or re-raise with context.
- **No mutable default arguments.** Use `None` (or a sentinel) and construct inside the function.
- **Functions are small and single-purpose,** at one level of abstraction; extract a named helper when a second level appears.
- **Few parameters; no boolean flag arguments** — a flag means the function does two things, so split it.
- **Favour early returns** over deep nesting; keep the happy path readable top to bottom.
- **Comments explain *why*,** in full sentences flagging a non-obvious constraint or invariant.

### Naming

- `snake_case` for functions, variables, modules; `PascalCase` for classes; `SCREAMING_SNAKE_CASE` for module-level constants.
- **Intention-revealing and searchable;** no abbreviations or encodings beyond ecosystem-standard short names (`ctx`, `id`, loop counters).
- **Classes are nouns; functions and methods are verbs or verb phrases.**
- A single leading underscore marks module-private names; respect it.

### Testing

- `pytest` is the sanctioned way to run tests (`uv run pytest`).
- **Test pyramid.** Unit tests for pure logic; integration tests exercising a module plus in-memory fakes (the conformance backend double); end-to-end tests against the assembled pipeline (the local-fixture demo).
- **Positive and negative space.** Every "happy path" test is paired with a test that the adjacent bad input raises the right error (a bad ID prefix, a missing required field, an out-of-enum value).
- **Test the validity boundary** — one below a limit, at the limit, one above.
- **Determinism.** Inject clock and id generators where outcomes depend on them; no wall-clock or randomness in test bodies. Pipeline verdicts are deterministic across repeated runs.
- **No flaky tests.** A flaky test is a bug to fix now.

### Documentation

- Public functions, classes, and modules carry docstrings stating purpose and contract; module docstrings trace the module to the spec section it implements.
- Each package's `__init__.py` documents what the package is and the surface it offers.
- No bare `# TODO` without an owner and a tracking reference.

---

## Repository hygiene

- **`.specs/`** is the canonical home for specs, change specs, and plans.
- **Per-task isolated workspaces** (jj workspaces / git worktrees) live as siblings *outside* the main tree, never nested inside it.
- **Local, untracked operator data** lives in a gitignored directory; never commit environment-specific config or secrets.
- **A pre-push hook** (`.githooks/pre-push`, enabled per clone with `git config core.hooksPath .githooks`) runs `scripts/check.sh` — `uv sync --frozen`, format-check, lint, type-check, and the test suite — before a push. **CI** (`.github/workflows/ci.yml`) re-runs the same `scripts/check.sh` on every push and pull request and is the authoritative gate. `jj git push` pushes through jj and bypasses git hooks, so when pushing with jj run `scripts/check.sh` locally first; CI catches it regardless. Clean Code leans on the test suite as its safety net — keep it fast and green.
- **One check script, two callers.** `scripts/check.sh` is the single source of truth for the gate; the hook and CI both invoke it, so local and CI runs are identical.
- **GitHub Actions are pinned to a full commit SHA**, never a floating tag, with the version tag in a trailing comment — `uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2`. A tag like `@v6` can be repointed at different (or compromised) code; the 40-character commit SHA is immutable, so CI runs exactly the audited code. This applies to *every* action a workflow pulls in, including first-party `actions/*`. Bump deliberately: resolve the new tag to its commit SHA (`gh api repos/<owner>/<repo>/commits/<tag> --jq .sha`) and update the SHA and the comment together, preferring the current Node-24 action majors.
- **The canonical schema is hand-authored authority**, not generated: `canonical-types.schema.json` is the source of truth that the domain types validate against, and a test asserts the in-memory schema equals the on-disk file.

---

## Guidelines for AI agents

1. **Optimize for the reader.** Prefer the clear construction; do not introduce cleverness to save lines.
2. **Keep functions small and single-purpose.** When a function grows a second level of abstraction, extract it with an intention-revealing name.
3. **No `None` in, no `None` out** for a domain value. Return empty collections or an explicit optional; a deliberate optional (the no-op patch) is documented as such.
4. **Express intent in names, not comments.** Do not add a comment that restates the code; if a comment is needed to explain *what*, rename instead.
5. **Tests are first-class.** A change ships with tests that are Fast, Independent, Repeatable, Self-validating, and written with the change (FIRST). "Compiles" is not "works" — run the tests and report the actual output.
6. **No duplication.** Before adding logic, check whether it already has a home (the resolution rule, the temp-dir conventions, the ID scheme).
7. **Stay inside the architecture.** Depend on abstractions; do not reach across a boundary a wrapper already owns. The run side must never see the hidden tests.
8. **Errors are raised with context, never swallowed.** Every `except` handles or re-raises with more information.
9. **Use `uv run …`**, never the system `python3`; the locked toolchain is the only supported one.
10. **Do not run destructive version-control operations without explicit confirmation, and do not skip hooks.** If a check fails, fix the underlying issue.
11. **Pin every GitHub Action to a full commit SHA** (`uses: …@<sha> # vX.Y.Z`); never add or leave a floating `@vN` tag in a workflow.

---

## Definition of done

A change is done when:

- The behaviour is covered by tests that follow FIRST; new validation paths have negative-space tests.
- Functions are small and single-purpose; names reveal intent without comments.
- No duplicated logic was introduced.
- Magic numbers are named constants.
- Errors are raised with context; no `None` is returned or passed for a domain value.
- The Python formatter (`uv run ruff format --check`), linter (`uv run ruff check`), type checker (`uv run pyright`), and test runner (`uv run pytest`) all pass locally — equivalently, `scripts/check.sh` passes — and CI is green.
- If domain types changed, `canonical-types.schema.json` is updated and every record still validates against it.
- The commit description states the *why*, with a Conventional Commits subject.

---

## Assumptions and open questions

**Assumptions**

- Python is the repo's only executable language at this date; the rest of the repository is Claude Code plugin/skill content (markdown). A second language adds its own conventions section here.
- Contributors run `uv` with the locked toolchain; the system Python is not a supported runtime.

**Decisions**

- *Clean Code over Tiger Style.* **Readability-first discipline, exceptions over errors-as-data.** The harness is pure-logic orchestration read and extended far more than it is hot-path executed; small intention-revealing functions and a fast test suite fit it better than pervasive runtime assertions.
- *Ruff as both linter and formatter.* **One tool, rule set `E, F, I, UP, B`.** A single fast tool covering format and lint keeps the pre-commit loop short; the rule set is declared in `pyproject.toml` rather than left to defaults.
- *Named constants for every limit.* **No magic numbers.** The harness already routes pool size, timeouts, temp-dir bases, and ID prefixes through named constants, so the rule reflects current practice.
- *jj is the version-control front end.* **`.jj/` over the `.git/` backend.** Both directories exist; describing the git workflow would tell contributors to run `git commit` against a jj working copy, the mismatch these rules exist to prevent.
- *pyright in standard mode, not strict.* **Standard mode over the library code.** The JSON-Schema validation dependency (`jsonschema`) ships no complete type stubs, so strict mode flags its untyped surface; standard mode checks the repo's own code cleanly without scattering suppressions around a third-party boundary. The test suite and the bundled fixture repo are excluded (tests use duck-typed fakes and protected access by design; the fixture repo is sample data checked out at runtime).
- *One check script behind the hook and CI.* **`scripts/check.sh` is the single gate, run by both.** Keeping local and CI checks identical avoids drift; CI is authoritative because `jj git push` bypasses git hooks.
- *GitHub Actions pinned to commit SHAs.* **`uses: …@<40-char-sha> # vX.Y.Z`.** A tag is mutable and a moved or compromised tag would silently change what CI executes; pinning to the immutable commit SHA fixes the running code, while the trailing version comment keeps it auditable and bumpable.

**Open questions**

- *Tightening to strict typing.* Should the JSON-Schema boundary be wrapped in a typed adapter so the library can move from `pyright` standard to strict, and should the test suite then be type-checked too (currently excluded)?
- *Commit-message enforcement.* Conventional Commits is followed by convention; there is no `commit-msg` hook or CI check validating the subject line. Should one be added?
- *Per-app deltas.* If the benchmark harness later needs a stricter limit or an extra tool than the repo-wide rules, does it warrant a per-app `.specs/benchmark/specs/NN-development.md` that opens with a Read-first pointer and documents only the deltas?
