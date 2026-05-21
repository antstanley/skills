# Rust — Tiger Style section

Slots into a development-guidelines page when Rust is a selected language. Three pieces: toolchain rows, an `### Assertions in Rust` subsection, and a `## Rust conventions` section. Adapt to the repo's actual tools and versions.

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

## `### Assertions in Rust`

> Slots under `## Defensive coding and assertions`, in the per-language run of subsections.

- Use `assert!`, `debug_assert!`, and `assert_eq!` liberally in core code. Production builds keep `assert!` enabled — no `--release`-only assertions for invariants.
- **Average two or more assertions per function** in cores: preconditions on entry, postconditions on exit, invariants in the middle. `assert!(true)` does not count.
- **Pair assertions.** For every property worth enforcing, find at least two independent paths to enforce it — for example, assert validity at write time and re-validate at every read site that mutates state from it.
- **Assert positive and negative space** — what you expect, and what you do not. The boundary between the two is where the interesting bugs live.
- **Compile-time assertions** for size and layout invariants: `const _: () = assert!(size_of::<Foo>() == 32);`.
- **Split compound assertions.** `assert!(a); assert!(b);` over `assert!(a && b);` — a failure then points at the actual broken condition.
- **No `unwrap()` / `expect()` in production paths.** Tests, init-only code, and one-off scripts may use them; an init-time `expect()` carries a reason string.
- **No `panic!` for control flow.** Panics signal programmer error only.

---

## `## Rust conventions`

> Top-level section on the page.

### Formatting and linting

- `cargo fmt --all` clean before commit.
- `cargo clippy --all-targets --all-features -D warnings` clean before commit.
- A `clippy.toml` enables pedantic-adjacent lints; each opt-out carries a comment explaining why.

### Code style

- **Hard limit: 70 lines per function.** If a function is longer, split it — extract pure helpers and centralise control flow in the parent ("push `if`s up, push `for`s down").
- **Hard limit: 100 columns per line**, via `rustfmt`'s `max_width`.
- **Modules over files.** Prefer many small files; a 1000-line `.rs` file is a smell.
- **No business logic in `main.rs` or in handlers.** Handlers parse, validate, call a core function, and serialise the result.
- **No recursion.** Use iteration with an explicit upper bound; the rare unavoidable case asserts its bound at entry.
- **Explicit fixed-width integers** (`u32`, `u64`, `i32`, `i64`) for domain values. Avoid `usize`/`isize` across a serialisation boundary.
- **Errors:** one `Error` enum per crate; `thiserror` for derivation; `From` impls translate at boundaries. The core never sees a third-party error type.
- **No `unsafe`** outside an adapter that strictly needs it; any `unsafe` block carries a `// SAFETY:` comment justifying every invariant it relies on.
- **`#[must_use]`** on `Result` and on builders.
- **Simpler return types win:** `()` > `bool` > integer > `Option<T>` > `Result<T, E>`. Chains of `.map().and_then().ok_or()` that hide branches are smells; prefer an explicit `match` when control flow is non-trivial.
- **Pass large structs by reference** (`> 16` bytes and not moved → take `&T`).
- **Calculate variables close to their use;** no dead bindings, no aliasing — state has one home.
- **State invariants positively:** `if index < length` over `if index >= length` when expressing the holding case.
- **Comments explain *why*,** in full sentences — a non-obvious constraint, a workaround, an invariant a future reader would miss.

### Naming

- `snake_case` for functions, variables, modules, files; `CamelCase` for types and traits (Rust convention is load-bearing in tooling).
- **No abbreviations** beyond ecosystem-standard short names (`ctx`, `cfg`, `id`, loop counters).
- **Acronyms in proper case** in `CamelCase` types: `HttpClient`, not `HTTPClient`.
- **Units last in identifiers**, descending significance: `latency_ms_max`, not `max_latency_ms`.
- **Same-length names for related variables** where reasonable: `source` / `target`, not `src` / `dst`.
- **Helpers prefix with the parent name** to show call history; callbacks go last in parameter lists.

### Testing

- The CI-sanctioned runner (commonly `cargo nextest run`) is how tests run.
- **Test pyramid.** In-module unit tests; integration tests in each crate's `tests/` exercising core plus in-memory adapters; end-to-end tests that spin up the assembled system, marked `#[ignore]` and run explicitly.
- **Positive and negative space.** "Validates a good input" is incomplete without "rejects a bad input" for every defined failure mode.
- **Test the validity boundary** — one below a limit, at the limit, one above.
- **Property tests** (`proptest`) for state-machine logic; they express the same invariants the production assertions do.
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
