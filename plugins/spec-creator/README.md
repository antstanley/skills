# spec-creator

Create or expand formal design specifications for an app, package, or codebase — numbered, layered, cross-linked markdown that defines what exists in the current branch.

Triggers on phrases like "create a spec", "spec out this app", "write design docs", "formalize the architecture", or when the user references using another project's specs as a template. The output is a numbered directory of markdown files plus a JSON Schema sidecar, layered as repo-wide globals + per-app specs.

It also writes **change specs** — single documents under `docs/specs/changes/` that propose a delta to the canonical spec, carry inline schema changes and implementation pointers, and are merged back into the canonical spec once the change ships. Triggers on "propose a change to the spec", "draft a change spec", "RFC for X", or "merge the change spec".

## Install

```
/plugin marketplace add antstanley/skills
/plugin install spec-creator@skills
```

## Skill content

The skill itself lives at [`skills/spec-creator/SKILL.md`](skills/spec-creator/SKILL.md). Worked examples and templates are under [`skills/spec-creator/evals/`](skills/spec-creator/evals/) and [`skills/spec-creator/references/`](skills/spec-creator/references/).
