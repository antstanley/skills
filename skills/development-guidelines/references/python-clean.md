# Python — Clean Code overlay

Layers onto [`python.md`](python.md) when the page's pervasive style is **Clean Code**. Python raises exceptions for both styles (the base file's mechanics); this overlay supplies Clean Code's emphasis on exception hierarchies, small functions, and intention-revealing names.

---

## `### Error handling in Python`

> Slots under `## Error handling and boundaries`, in the per-language run of subsections.

- Raise specific exception types with context, rooted in a small exception hierarchy under one project base exception.
- **Never return `None` as an error signal.** Raise, or return an explicit `Optional`/`Result`-style object whose meaning is unambiguous.
- Catch the narrowest exception type; handle it or re-raise with added context. Never a bare `except:`.
- Wrap third-party clients behind a repo-owned module that translates their exceptions into the project's own.

## Code-style emphases

> Merge into `### Code style` under `## Python conventions`.

- **Functions are small and single-purpose,** at one level of abstraction; extract a named helper when a second level appears.
- **Few parameters; no boolean flag arguments** — a flag means the function does two things, so split it.
- **Favour early returns** over deep nesting; keep the happy path readable top to bottom.

## Naming emphases

> Merge into `### Naming` under `## Python conventions`.

- **Intention-revealing and searchable;** no abbreviations or encodings beyond ecosystem-standard short names.
- **Classes are nouns; functions and methods are verbs or verb phrases.**
