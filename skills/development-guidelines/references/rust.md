# Rust — language base (style-neutral)

Slots into a development-guidelines page when Rust is a selected language. Holds the **style-neutral substrate**: toolchain rows, formatting and linting, code-style mechanics, naming *case* conventions, testing, documentation, and the definition-of-done tool line. Adapt to the repo's actual tools and versions.

The **style-coupled parts** — the assertion/error-handling subsection plus this language's code-style and naming *emphases* — live in the style overlay alongside this file: [`rust-tiger.md`](rust-tiger.md) or [`rust-clean.md`](rust-clean.md).

Rust has no exceptions, so error handling is always `Result`-based; the style fork is one of emphasis, not mechanism. The base below carries the idiomatic-Rust mechanics both styles share.

---

## Toolchain rows

Add to the page's `## Toolchain` table:

| Tool | Version / channel | Notes |
|---|---|---|
| Rust | stable, pinned | pinned in `rust-toolchain.toml` |
| rustfmt | default channel | runs in CI and pre-push |
| clippy | latest | `--all-targets --all-features` |
| test runner | cargo-nextest (or `cargo test`) | name the one CI runs |

---

## `## Rust conventions`

> Top-level section on the page. The bullets below are style-neutral; the selected style's overlay adds its code-style and naming emphases.

### Formatting and linting

- `cargo fmt --all` clean before commit.
- `cargo clippy --all-targets --all-features -D warnings` clean before commit.
- A `clippy.toml` enables pedantic-adjacent lints; each opt-out carries a comment explaining why.

### Code style

- **Modules over files.** Prefer many small files; a 1000-line `.rs` file is a smell.
- **No business logic in `main.rs` or in handlers.** Handlers parse, validate, call a core function, and serialise the result.
- **Explicit fixed-width integers** (`u32`, `u64`, `i32`, `i64`) for domain values. Avoid `usize`/`isize` across a serialisation boundary.
- **Errors are `Result`** with one `Error` enum per crate (`thiserror` for derivation); `From` impls translate at boundaries.
- **No `unsafe`** outside an adapter that strictly needs it; any `unsafe` block carries a `// SAFETY:` comment justifying every invariant it relies on.
- **`#[must_use]`** on `Result` and on builders.
- **Comments explain *why*,** in full sentences — a non-obvious constraint, a workaround, an invariant a future reader would miss.

### Naming

- `snake_case` for functions, variables, modules, files; `CamelCase` for types and traits (Rust convention is load-bearing in tooling).
- **Acronyms in proper case** in `CamelCase` types: `HttpClient`, not `HTTPClient`.
- **No abbreviations** beyond ecosystem-standard short names (`ctx`, `cfg`, `id`, loop counters).

### Testing

- The CI-sanctioned runner (commonly `cargo nextest run`) is how tests run.
- **Test pyramid.** In-module unit tests; integration tests in each crate's `tests/` exercising core plus in-memory adapters; end-to-end tests that spin up the assembled system, marked `#[ignore]` and run explicitly.
- **Positive and negative space.** "Validates a good input" is incomplete without "rejects a bad input" for every defined failure mode.
- **Test the validity boundary** — one below a limit, at the limit, one above.
- **Property tests** (`proptest`) for state-machine logic and parsers.
- **Determinism.** Use clock and id-generator fakes; no `Instant::now()` or randomness in test bodies.
- **No flaky tests.** A flaky test is a bug to fix immediately.

### Documentation

- Public items in library crates carry doc comments.
- Each crate's `lib.rs` documents what the crate is, the ports it depends on, and the surface it offers.
- No bare `// TODO` without an owner and a tracking reference.

---

## Definition-of-done additions

Append to the page's `## Definition of done`:

- `cargo fmt`, `cargo clippy -D warnings`, and the sanctioned test runner all pass locally.
