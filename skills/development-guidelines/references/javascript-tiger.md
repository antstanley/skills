# JavaScript — Tiger Style overlay

Layers onto [`javascript.md`](javascript.md) when the page's pervasive style is **Tiger Style**. Supplies the assertion subsection and Tiger Style's JavaScript-specific code-style and naming emphases.

---

## `### Assertions in JavaScript`

> Slots under `## Defensive coding and assertions`, in the per-language run of subsections.

- Use a small `invariant(condition, message)` helper that throws on a false condition; treat it the way Rust treats `assert!`. Aim for roughly two assertions per non-trivial function.
- **Validation is the type system.** Every value crossing a boundary — function arguments at module edges, inbound JSON, query params, environment config — is validated against a schema before use. There is no compiler to lean on.
- Freeze constants and config objects (`Object.freeze`) so accidental mutation throws instead of corrupting state silently.

## Code-style emphases

> Merge into `### Code style` under `## JavaScript conventions`.

- **Errors are values where it reads clearly;** otherwise throw typed `Error` subclasses and handle them at a defined layer. Never swallow an error.
- **Hard limits** on function size and line length — a common pair is 70 lines, 100 columns. The formatter enforces columns; function size is a review gate.

## Naming emphases

> Merge into `### Naming` under `## JavaScript conventions`.

- **Units last in identifiers**, descending significance: `latencyMsMax`, not `maxLatencyMs`.
- **Same-length names for related variables** where reasonable: `source` / `target`, not `src` / `dst`.
