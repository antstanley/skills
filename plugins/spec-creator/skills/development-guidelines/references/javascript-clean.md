# JavaScript — Clean Code overlay

Layers onto [`javascript.md`](javascript.md) when the page's pervasive style is **Clean Code**. Supplies the error-handling subsection and Clean Code's JavaScript-specific code-style and naming emphases.

---

## `### Error handling in JavaScript`

> Slots under `## Error handling and boundaries`, in the per-language run of subsections.

- Throw typed `Error` subclasses carrying context, not error codes a caller may forget to check.
- **Never return or accept `null`/`undefined` for a domain value.** Return an empty collection, a null-object, or an explicit result shape.
- Wrap third-party clients behind a repo-owned module that translates their failures into the repo's own error types.
- Validate inbound data at the boundary (the base substrate's schema check), then trust the shape inside the core.

## Code-style emphases

> Merge into `### Code style` under `## JavaScript conventions`.

- **Functions are small and single-purpose,** at one level of abstraction; extract a named helper when a second level appears.
- **Prefer 0–2 parameters; no boolean flag arguments.**
- **Separate commands from queries.**

## Naming emphases

> Merge into `### Naming` under `## JavaScript conventions`.

- **Intention-revealing and searchable;** no encodings or Hungarian prefixes.
- **Constructor/class names are nouns; functions are verbs or verb phrases.**
