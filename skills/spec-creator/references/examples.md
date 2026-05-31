# Worked examples

Two worked runs of the skill. Read when a request matches one of these shapes and a concrete walkthrough helps.

## Promotion (per-package → global)

User: "The architecture page in `docs/editor/specs/06-architecture-principles.md` is mostly cross-cutting. Make it global."

1. Read the per-package file.
2. Identify cross-cutting paragraphs (hexagonal layering, monorepo layout, dependency graph, TS config, frontend stack).
3. Identify per-package paragraphs (the editor's specific package boundaries, ports, file layout).
4. Create `docs/specs/architecture-principles.md` with the cross-cutting content, scoped `Repo-wide`.
5. Rewrite `docs/editor/specs/06-architecture-principles.md` to a thin per-package version that opens with the **Read first** pointer and only covers the editor-specific deltas.
6. Update `docs/README.md` (creating it if needed) to index the new global spec.

## Adding a sibling app

User: "Add a spec for the website app at `apps/website` modelled on the editor specs."

1. Read `docs/editor/specs/` end-to-end as the template.
2. Read `apps/website/` source: routes, layouts, build config.
3. Pick a numbered file set appropriate to the website's surface area (smaller than the editor's — 00-overview, 01-content-model, 02-routes-and-layouts, 03-build-pipeline, plus per-package architecture and development pointer pages).
4. Write each file describing what exists.
5. Cross-link the global specs.
6. Update `docs/README.md` to add the website specs.
