# TypeScript — Clean Code overlay

Layers onto [`typescript.md`](typescript.md) when the page's pervasive style is **Clean Code**. Supplies the error-handling subsection and Clean Code's TypeScript-specific code-style and naming emphases. Slot each piece into the matching section of the assembled page.

---

## `### Error handling in TypeScript`

> Slots under `## Error handling and boundaries`, in the per-language run of subsections.

- Throw typed `Error` subclasses carrying context; do not return error codes a caller may forget to check.
- **Never return or accept `null`/`undefined` for a domain value.** Use an explicit `Optional`/`Result` type, an empty collection, or a null-object.
- Wrap third-party clients behind a repo-owned module that translates their errors into the repo's own `Error` types; the core never sees a vendor error.
- Validate inbound data against the generated types at the boundary, then work with trusted shapes inside the core.

## Code-style emphases

> Merge into `### Code style` under `## TypeScript conventions`.

- **Functions are small and single-purpose,** operating at one level of abstraction; when a second level appears, extract a named helper.
- **Prefer 0–2 parameters; no boolean flag arguments** — a flag means the function does two things, so split it.
- **Separate commands from queries** — a function either changes state or returns a value, not both.

## Naming emphases

> Merge into `### Naming` under `## TypeScript conventions`.

- **Intention-revealing and searchable.** The name says what the value is or does; no encodings, no Hungarian prefixes.
- **Class/type names are nouns; function and method names are verbs or verb phrases.**
