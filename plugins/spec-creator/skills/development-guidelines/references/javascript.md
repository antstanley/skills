# JavaScript — Tiger Style section

Slots into a development-guidelines page when JavaScript (without a TypeScript layer) is a selected language. Three pieces: toolchain rows, an `### Assertions in JavaScript` subsection, and a `## JavaScript conventions` section. Adapt to the repo's actual tools.

The core challenge: JavaScript has no static type system, so Tiger Style's "make invalid states unrepresentable" moves almost entirely to **runtime validation**. Where TypeScript catches a wrong shape at compile time, JavaScript catches it at the boundary with a schema check, or not at all. The discipline compensates by validating more, and earlier.

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

## `### Assertions in JavaScript`

> Slots under `## Defensive coding and assertions`, in the per-language run of subsections.

- Use a small `invariant(condition, message)` helper that throws on a false condition; treat it the way Rust treats `assert!`. Aim for roughly two assertions per non-trivial function.
- **Validation is the type system.** Every value crossing a boundary — function arguments at module edges, inbound JSON, query params, environment config — is validated against a schema before use. There is no compiler to lean on.
- Use JSDoc type annotations (`@param`, `@returns`) on public functions and run the type-checker (`tsc --checkJs`) in CI; it is the cheapest static check available without adopting TypeScript.
- Freeze constants and config objects (`Object.freeze`) so accidental mutation throws instead of corrupting state silently.

---

## `## JavaScript conventions`

> Top-level section on the page.

### Formatting and linting

- The formatter runs clean before commit; it owns line length and layout.
- The linter runs clean before commit with warnings treated as errors; enable rules that catch the hazards a type system would (`no-undef`, `eqeqeq`, `no-implicit-coercion`, `consistent-return`).
- Lint and format are enforced in the pre-push hook and re-run in CI.

### Code style

- **`"use strict"`** everywhere (or native ES modules, which are strict by default).
- **`const` by default, `let` only when reassigned, never `var`.**
- **Strict equality (`===`) only.** No implicit coercion; convert explicitly.
- **Validate at boundaries.** Inbound JSON is parsed and validated through a schema validator into a known shape. No trusting `JSON.parse` output.
- **Errors are values where it reads clearly;** otherwise throw typed `Error` subclasses and handle them at a defined layer. Never swallow an error.
- **No silent fallthrough.** A `switch` over a tagged value has a `default` that throws on the unexpected case.
- **Hard limits** on function size and line length — a common pair is 70 lines, 100 columns. The formatter enforces columns; function size is a review gate.
- **Brace every block** unless it fits on one line. Split compound conditions that check different things.
- **Comments explain *why*,** in full sentences flagging a non-obvious constraint or invariant.

### Naming

- `camelCase` for functions and variables, `PascalCase` for classes and constructors, `SCREAMING_SNAKE_CASE` for module-level constants.
- **No abbreviations** beyond ecosystem-standard short names (`ctx`, `id`, loop counters).
- **Units last in identifiers**, descending significance: `latencyMsMax`, not `maxLatencyMs`.
- **Same-length names for related variables** where reasonable: `source` / `target`, not `src` / `dst`.

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
