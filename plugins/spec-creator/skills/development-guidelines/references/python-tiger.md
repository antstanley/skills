# Python — Tiger Style overlay

Layers onto [`python.md`](python.md) when the page's pervasive style is **Tiger Style**. Supplies the assertion subsection and Tiger Style's Python-specific code-style and naming emphases.

A note on `assert`: CPython strips `assert` statements when run with `-O`. Tiger Style wants assertions enabled in production, so the discipline does **not** rely on the bare `assert` statement for invariants that must hold in production — it uses a helper that raises unconditionally (see below). The bare `assert` is fine in tests, which never run under `-O`.

---

## `### Assertions in Python`

> Slots under `## Defensive coding and assertions`, in the per-language run of subsections.

- Use an `invariant(condition, message)` helper that **raises unconditionally** (a plain `if not condition: raise ...`), not the bare `assert` statement — `assert` is stripped under `-O` and cannot be trusted for production invariants. Reserve bare `assert` for test bodies.
- Aim for roughly two invariant checks per non-trivial function: preconditions on entry, postconditions on exit, invariants in the middle.
- Run a static type checker (mypy or pyright) in **strict** mode in CI; it is the closest Python gets to "make invalid states unrepresentable".
- Use `typing.assert_never()` in the final branch of an exhaustive match over an enum / tagged union so the type checker flags an unhandled case.

## Code-style emphases

> Merge into `### Code style` under `## Python conventions`.

- **Hard limits** on function size and line length — a common pair is 70 lines, 100 columns. The formatter enforces columns; function size is a review gate.
- **Errors carry typed reasons.** Beyond raising typed exceptions, give them structured fields so a boundary layer can translate them into stable codes.

## Naming emphases

> Merge into `### Naming` under `## Python conventions`.

- **Units last in identifiers**, descending significance: `latency_ms_max`, not `max_latency_ms`.
- **Same-length names for related variables** where reasonable: `source` / `target`, not `src` / `dst`.
