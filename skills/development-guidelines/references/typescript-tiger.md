# TypeScript — Tiger Style overlay

Layers onto [`typescript.md`](typescript.md) when the page's pervasive style is **Tiger Style**. Supplies the assertion subsection and Tiger Style's TypeScript-specific code-style and naming emphases. Slot each piece into the matching section of the assembled page.

---

## `### Assertions in TypeScript`

> Slots under `## Defensive coding and assertions`, in the per-language run of subsections.

- Use a small `invariant(condition, message)` helper that throws on a false condition; treat it the way Rust treats `assert!`. A separate `assertNever(x: never)` enforces exhaustive `switch`.
- Aim for the same density as the rest of the codebase — roughly two assertions per non-trivial function: preconditions on entry, postconditions on exit, invariants in the middle.
- Validate all inbound data with a schema validator (Valibot, Zod, or equivalent) against the types generated from `canonical-types.schema.json`, at the boundary. Never cast network data with `as Foo`.

## Code-style emphases

> Merge into `### Code style` under `## TypeScript conventions`.

- **Errors are values.** Prefer a typed result over throwing across module boundaries; throw only for programmer error (the `invariant` path).
- **Hard limits** on function size and line length — a common pair is 70 lines per function, 100 columns per line. The formatter enforces columns; function size is a review gate.

## Naming emphases

> Merge into `### Naming` under `## TypeScript conventions`.

- **Units last in identifiers**, descending significance: `latencyMsMax`, not `maxLatencyMs`. Related variables then sort and align.
- **Same-length names for related variables** where reasonable: `source` / `target`, not `src` / `dst`.
