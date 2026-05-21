# Rust — Clean Code overlay

Layers onto [`rust.md`](rust.md) when the page's pervasive style is **Clean Code**. Rust has no exceptions, so error handling stays `Result`-based (the base file's idiomatic mechanics); this overlay supplies Clean Code's emphasis on boundaries, small functions, and intention-revealing names.

---

## `### Error handling in Rust`

> Slots under `## Error handling and boundaries`, in the per-language run of subsections.

- Wrap third-party crates behind a repo-owned module that maps their errors into the crate's own `Error`; callers in the core never match on a vendor error type.
- Prefer `?` propagation with added context (e.g. `thiserror` variants or an `anyhow`-style context message) over hand-written `match` ladders where it reads more clearly.
- Reserve `panic!` / `unwrap` / `expect` for truly unreachable invariants and init-only code; an init-time `expect` carries a reason string.
- Return an explicit `Option`/`Result` rather than a sentinel value; a `None` or `Err` is the readable "no value" / "failed" signal.

## Code-style emphases

> Merge into `### Code style` under `## Rust conventions`.

- **Functions are small and single-purpose,** at one level of abstraction; extract named helpers when a second level appears.
- **Few parameters;** group related arguments into a struct rather than passing a long positional list.
- **Favour early returns** over deep nesting; let the happy path read top to bottom.
- **Prefer composition** (small focused traits, helper functions) over large multi-purpose types.

## Naming emphases

> Merge into `### Naming` under `## Rust conventions`.

- **Intention-revealing and searchable;** no abbreviations or encodings beyond the ecosystem-standard short names.
- **Types and traits are nouns or noun phrases; functions are verbs or verb phrases.**
