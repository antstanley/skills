# Rust — Tiger Style overlay

Layers onto [`rust.md`](rust.md) when the page's pervasive style is **Tiger Style**. Supplies the assertion subsection and Tiger Style's Rust-specific code-style and naming emphases.

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

## Code-style emphases

> Merge into `### Code style` under `## Rust conventions`.

- **Hard limit: 70 lines per function.** If a function is longer, split it — extract pure helpers and centralise control flow in the parent ("push `if`s up, push `for`s down").
- **Hard limit: 100 columns per line**, via `rustfmt`'s `max_width`.
- **No recursion.** Use iteration with an explicit upper bound; the rare unavoidable case asserts its bound at entry.
- **The core never sees a third-party error type** — `From` impls translate every vendor error at the boundary.
- **Simpler return types win:** `()` > `bool` > integer > `Option<T>` > `Result<T, E>`. Chains of `.map().and_then().ok_or()` that hide branches are smells; prefer an explicit `match` when control flow is non-trivial.
- **Pass large structs by reference** (`> 16` bytes and not moved → take `&T`).
- **Calculate variables close to their use;** no dead bindings, no aliasing — state has one home.
- **State invariants positively:** `if index < length` over `if index >= length` when expressing the holding case.

## Naming emphases

> Merge into `### Naming` under `## Rust conventions`.

- **Units last in identifiers**, descending significance: `latency_ms_max`, not `max_latency_ms`.
- **Same-length names for related variables** where reasonable: `source` / `target`, not `src` / `dst`.
- **Helpers prefix with the parent name** to show call history; callbacks go last in parameter lists.
