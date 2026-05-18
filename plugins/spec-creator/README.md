# spec-creator

Create or expand formal design specifications for an app, package, or codebase — numbered, layered, cross-linked markdown that defines what exists in the current branch.

Triggers on phrases like "create a spec", "spec out this app", "write design docs", "formalize the architecture", or when the user references using another project's specs as a template. The output is a numbered directory of markdown files plus a JSON Schema sidecar, layered as repo-wide globals + per-app specs.

## Install

```
/plugin marketplace add antstanley/skills
/plugin install spec-creator@skills
```

## Skill content

The skill itself lives at [`skills/spec-creator/SKILL.md`](skills/spec-creator/SKILL.md). Worked examples and templates are under [`skills/spec-creator/evals/`](skills/spec-creator/evals/) and [`skills/spec-creator/references/`](skills/spec-creator/references/).
