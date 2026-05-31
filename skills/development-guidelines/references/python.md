# Python — language base (style-neutral)

Slots into a development-guidelines page when Python is a selected language. Holds the **style-neutral substrate**: toolchain rows, formatting and linting, code-style mechanics, naming *case* conventions, testing, documentation, and the definition-of-done tool line. Adapt to the repo's actual tools.

The **style-coupled parts** — the assertion/error-handling subsection plus this language's code-style and naming *emphases* — live in the style overlay alongside this file: [`python-tiger.md`](python-tiger.md) or [`python-clean.md`](python-clean.md).

Python raises exceptions for both styles, so error handling is shared mechanism; the fork is emphasis (assertion density and production-safe `assert` under Tiger Style, vs. small functions and intention-revealing names under Clean Code).

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

## `## Python conventions`

> Top-level section on the page. The bullets below are style-neutral; the selected style's overlay adds its code-style and naming emphases.

### Formatting and linting

- The formatter runs clean before commit (Ruff format or Black); it owns line length and layout.
- The linter runs clean before commit with warnings treated as errors (Ruff or Flake8 with a documented rule set).
- The strict type checker runs clean before commit.
- Format, lint, and type-check are enforced in the pre-push hook and re-run in CI.

### Code style

- **Type-annotate everything public.** No untyped public function; no implicit `Any`. Configure the checker to forbid `Any` where avoidable.
- **`@dataclass(frozen=True)`** (or attrs / Pydantic models) for value objects, so invalid mutation raises rather than corrupting state.
- **Enums for state, not strings;** match exhaustively with `typing.assert_never` in the default branch.
- **Validate at boundaries.** Inbound JSON is parsed through a validation model (Pydantic, attrs + validators, or msgspec) into a typed object. No trusting a raw `dict`.
- **Errors are explicit.** Raise typed exceptions; never swallow with a bare `except:`. Catch the narrowest exception type and handle or re-raise.
- **No mutable default arguments.** Use `None` and construct inside the function.
- **Comments explain *why*,** in full sentences flagging a non-obvious constraint or invariant.

### Naming

- `snake_case` for functions, variables, modules; `PascalCase` for classes; `SCREAMING_SNAKE_CASE` for module-level constants.
- **No abbreviations** beyond ecosystem-standard short names (`ctx`, `id`, loop counters).
- A single leading underscore marks module-private names; respect it.

### Testing

- `pytest` (or the named runner) is the sanctioned way to run tests.
- **Test pyramid.** Unit tests for pure logic; integration tests exercising a module plus in-memory fakes; end-to-end tests against the assembled system, run explicitly (a marker, not the default selection).
- **Positive and negative space.** Every "happy path" test is paired with a test that the adjacent bad input raises the right error.
- **Test the validity boundary** — one below a limit, at the limit, one above.
- **Property tests** (Hypothesis) for state-machine logic and parsers.
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
