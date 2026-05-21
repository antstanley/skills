# Python — Tiger Style section

Slots into a development-guidelines page when Python is a selected language. Three pieces: toolchain rows, an `### Assertions in Python` subsection, and a `## Python conventions` section. Adapt to the repo's actual tools.

A note on `assert`: CPython strips `assert` statements when run with `-O`. Tiger Style wants assertions enabled in production, so the discipline does **not** rely on the bare `assert` statement for invariants that must hold in production — it uses a helper that raises unconditionally (see below). The bare `assert` is fine in tests, which never run under `-O`.

---

## Toolchain rows

Add to the page's `## Toolchain` table:

| Tool | Version / channel | Notes |
|---|---|---|
| Python | pinned minor | pinned in `.python-version` / `pyproject.toml` |
| package manager | latest | name the one in use (uv, Poetry, pip-tools) |
| linter + formatter | latest | name the one in use (Ruff covers both; or Black + Flake8) |
| type checker | latest | mypy or pyright, in strict mode |
| test runner | latest | pytest (or name the one in use) |

---

## `### Assertions in Python`

> Slots under `## Defensive coding and assertions`, in the per-language run of subsections.

- Use an `invariant(condition, message)` helper that **raises unconditionally** (a plain `if not condition: raise ...`), not the bare `assert` statement — `assert` is stripped under `-O` and cannot be trusted for production invariants. Reserve bare `assert` for test bodies.
- Aim for roughly two invariant checks per non-trivial function: preconditions on entry, postconditions on exit, invariants in the middle.
- **Validate all inbound data** with a schema/validation library (Pydantic, attrs + validators, or msgspec) at the boundary; never trust a parsed dict's shape.
- Run a static type checker (mypy or pyright) in **strict** mode in CI; type annotations are mandatory on public functions. Strict typing is the closest Python gets to "make invalid states unrepresentable".
- Use `typing.assert_never()` in the final branch of an exhaustive match over an enum / tagged union so the type checker flags an unhandled case.

---

## `## Python conventions`

> Top-level section on the page.

### Formatting and linting

- The formatter runs clean before commit (Ruff format or Black); it owns line length and layout.
- The linter runs clean before commit with warnings treated as errors (Ruff or Flake8 with a documented rule set).
- The strict type checker runs clean before commit.
- Format, lint, and type-check are enforced in the pre-push hook and re-run in CI.

### Code style

- **Type-annotate everything public.** No untyped public function; no implicit `Any`. Configure the checker to forbid `Any` where avoidable.
- **`@dataclass(frozen=True)`** (or attrs / Pydantic models) for value objects, so invalid mutation raises rather than corrupting state.
- **Enums for state, not strings;** match exhaustively with `assert_never` in the default branch.
- **Validate at boundaries.** Inbound JSON is parsed through a validation model into a typed object. No trusting a raw `dict`.
- **Errors are explicit.** Raise typed exceptions; never swallow with a bare `except:`. Catch the narrowest exception type and handle or re-raise.
- **No mutable default arguments.** Use `None` and construct inside the function.
- **Hard limits** on function size and line length — a common pair is 70 lines, 100 columns. The formatter enforces columns; function size is a review gate.
- **Comments explain *why*,** in full sentences flagging a non-obvious constraint or invariant.

### Naming

- `snake_case` for functions, variables, modules; `PascalCase` for classes; `SCREAMING_SNAKE_CASE` for module-level constants.
- **No abbreviations** beyond ecosystem-standard short names (`ctx`, `id`, loop counters).
- **Units last in identifiers**, descending significance: `latency_ms_max`, not `max_latency_ms`.
- **Same-length names for related variables** where reasonable: `source` / `target`, not `src` / `dst`.
- A single leading underscore marks module-private names; respect it.

### Testing

- `pytest` (or the named runner) is the sanctioned way to run tests.
- **Test pyramid.** Unit tests for pure logic; integration tests exercising a module plus in-memory fakes; end-to-end tests against the assembled system, run explicitly (a marker, not the default selection).
- **Positive and negative space.** Every "happy path" test is paired with a test that the adjacent bad input raises the right error.
- **Test the validity boundary** — one below a limit, at the limit, one above.
- **Property tests** (Hypothesis) for state-machine logic and parsers; they express the same invariants the runtime checks do.
- **Determinism.** Inject clock and id generators (or use a freezegun-style fake); no wall-clock or randomness in test bodies.
- **No flaky tests.** A flaky test is a bug to fix now.

### Documentation

- Public functions, classes, and modules carry docstrings stating purpose and contract.
- Each package's `__init__.py` (or top module) documents what the package is and the surface it offers.
- No bare `# TODO` without an owner and a tracking reference.

---

## Definition-of-done additions

Append to the page's `## Definition of done`:

- The Python linter, formatter, strict type checker, and test runner all pass locally.
