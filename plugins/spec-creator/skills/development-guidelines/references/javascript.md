# JavaScript — language base (style-neutral)

Slots into a development-guidelines page when JavaScript (without a TypeScript layer) is a selected language. Holds the **style-neutral substrate**: toolchain rows, formatting and linting, code-style mechanics, naming *case* conventions, testing, documentation, and the definition-of-done tool line. Adapt to the repo's actual tools.

The **style-coupled parts** — the assertion/error-handling subsection plus this language's code-style and naming *emphases* — live in the style overlay alongside this file: [`javascript-tiger.md`](javascript-tiger.md) or [`javascript-clean.md`](javascript-clean.md).

JavaScript has no static type system, so "invalid states" are caught at runtime, at the boundary, with a schema check — or not at all. Both supported styles compensate by validating more, and earlier; the base substrate below makes boundary validation a default.

---

## Toolchain rows

Add to the page's `## Toolchain` table:

| Tool | Version / channel | Notes |
|---|---|---|
| Node | LTS | runtime |
| linter | latest | name the one in use (ESLint, oxlint, Biome) |
| formatter | latest | name the one in use (Prettier, Biome, oxfmt) |
| test runner | latest | name the one in use (node:test, vitest, jest) |
| schema validator | latest | runtime validation — Valibot, Zod, Ajv |

---

## `## JavaScript conventions`

> Top-level section on the page. The bullets below are style-neutral; the selected style's overlay adds its code-style and naming emphases.

### Formatting and linting

- The formatter runs clean before commit; it owns line length and layout.
- The linter runs clean before commit with warnings treated as errors; enable rules that catch the hazards a type system would (`no-undef`, `eqeqeq`, `no-implicit-coercion`, `consistent-return`).
- Lint and format are enforced in the pre-push hook and re-run in CI.

### Code style

- **`"use strict"`** everywhere (or native ES modules, which are strict by default).
- **`const` by default, `let` only when reassigned, never `var`.**
- **Strict equality (`===`) only.** No implicit coercion; convert explicitly.
- **Validate at boundaries.** Inbound JSON is parsed and validated through a schema validator into a known shape. No trusting `JSON.parse` output.
- **Cheap static checking.** Use JSDoc type annotations (`@param`, `@returns`) on public functions and run `tsc --checkJs` in CI — the cheapest static check available without adopting TypeScript.
- **No silent fallthrough.** A `switch` over a tagged value has a `default` that throws on the unexpected case.
- **Brace every block** unless it fits on one line. Split compound conditions that check different things.
- **Comments explain *why*,** in full sentences flagging a non-obvious constraint or invariant.

### Naming

- `camelCase` for functions and variables, `PascalCase` for classes and constructors, `SCREAMING_SNAKE_CASE` for module-level constants.
- **No abbreviations** beyond ecosystem-standard short names (`ctx`, `id`, loop counters).

### Testing

- The chosen test runner is the sanctioned way to run tests.
- **Test pyramid.** Unit tests for pure logic; integration tests exercising a module plus in-memory fakes; end-to-end tests against the assembled system, run explicitly.
- **Positive and negative space.** Because the type system cannot reject a bad shape, the negative-space test is doing the work a compiler would — write it for every validation path.
- **Test the validity boundary** — one below a limit, at the limit, one above.
- **Determinism.** Inject clock and id generators; no wall-clock or randomness in test bodies.
- **No flaky tests.** A flaky test is a bug to fix now.

### Documentation

- Public exports carry JSDoc with types; the JSDoc is the contract a consumer reads.
- Each package's entry module documents what the package is and the surface it offers.
- No bare `// TODO` without an owner and a tracking reference.

---

## Definition-of-done additions

Append to the page's `## Definition of done`:

- The JavaScript linter, formatter, `tsc --checkJs`, and test runner all pass locally.
