# TypeScript — Tiger Style section

Slots into a development-guidelines page when TypeScript is a selected language. Three pieces: toolchain rows, an `### Assertions in TypeScript` subsection (under Defensive coding), and a `## TypeScript conventions` section. Adapt to the repo's actual tools and versions.

---

## Toolchain rows

Add to the page's `## Toolchain` table:

| Tool | Version / channel | Notes |
|---|---|---|
| TypeScript | pinned major (strict mode) | `strict` settings, see conventions |
| Node | LTS | dev server / tooling runtime |
| linter | latest | lints TS — name the one in use (oxlint, ESLint) |
| formatter | latest | formats TS — name the one in use (oxfmt, Prettier, Biome) |
| test runner | latest | name the one in use (vitest, node:test, jest) |

---

## `### Assertions in TypeScript`

> Slots under `## Defensive coding and assertions`, in the per-language run of subsections.

- Use a small `invariant(condition, message)` helper that throws on a false condition; treat it the way Rust treats `assert!`. A separate `assertNever(x: never)` enforces exhaustive `switch`.
- Aim for the same density as the rest of the codebase — roughly two assertions per non-trivial function: preconditions on entry, postconditions on exit, invariants in the middle.
- Validate all inbound data with a schema validator (Valibot, Zod, or equivalent) against the types generated from `canonical-types.schema.json`, at the boundary. Never cast network data with `as Foo`.
- Strict compiler settings are load-bearing: `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`. No `any`.

---

## `## TypeScript conventions`

> Top-level section on the page.

### Formatting and linting

- The formatter runs clean before commit; it owns line length and layout.
- The linter runs clean before commit with warnings treated as errors.
- Lint and format are enforced in the pre-push hook and re-run in CI.

### Code style

- **No `any`.** Use `unknown` plus narrowing, or a typed parser. Casts are bugs unless justified in a comment.
- **Domain types are imported from one shared package**, never hand-redefined in app code.
- **Validate at boundaries.** Inbound JSON — responses, frames, query params — is parsed through a schema validator into the typed shape. No `JSON.parse(...) as Foo`.
- **No silent fallthrough.** A `switch` over a discriminated union ends with `assertNever(x)` so the compiler enforces exhaustiveness.
- **Errors are values.** Prefer a typed result over throwing across module boundaries; throw only for programmer error (the `invariant` path).
- **Hard limits** on function size and line length — a common pair is 70 lines per function, 100 columns per line. The formatter enforces columns; function size is a review gate.
- **Brace every block** unless it fits on one line. Split compound conditions when they check different things.
- **Comments explain *why*.** No comment paraphrases the code; comments are full sentences flagging a non-obvious constraint or invariant.

### Naming

- `camelCase` for functions and variables, `PascalCase` for types and classes, `SCREAMING_SNAKE_CASE` for module-level constants.
- **No abbreviations** in identifiers, beyond ecosystem-standard short names (`ctx`, `id`, loop counters).
- **Units last in identifiers**, descending significance: `latencyMsMax`, not `maxLatencyMs`. Related variables then sort and align.
- **Same-length names for related variables** where reasonable: `source` / `target`, not `src` / `dst`.

### Testing

- The chosen test runner is the sanctioned way to run tests.
- **Test pyramid.** Unit tests for pure logic; integration tests exercising a module plus in-memory adapters; end-to-end tests against the assembled system, run explicitly.
- **Positive and negative space.** Every "happy path" test is paired with a test that the adjacent bad input is rejected.
- **Test the validity boundary** — one below a limit, at the limit, one above.
- **No flaky tests.** A flaky test is a bug to fix now, not a known issue to retry around.
- **Determinism.** Inject clock and id generators; no wall-clock or randomness in test bodies.

### Documentation

- Public exports of shared packages carry doc comments.
- Each package's entry module documents what the package is and the surface it offers.
- No bare `// TODO` without an owner and a tracking reference.

---

## Definition-of-done additions

Append to the page's `## Definition of done`:

- The TypeScript linter, formatter, and test runner all pass locally.
