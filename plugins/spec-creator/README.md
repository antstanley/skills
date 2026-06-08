# spec-creator

Create or expand formal design specifications for an app, package, or codebase — numbered, layered, cross-linked markdown that defines what exists in the current branch.

Triggers on phrases like "create a spec", "spec out this app", "write design docs", "formalize the architecture", or when the user references using another project's specs as a template. The output is a numbered directory of markdown files plus a JSON Schema sidecar, layered as repo-wide globals + per-package specs.

It also writes **change specs** — single documents under `.specs/changes/` that propose a delta to the canonical spec, carry inline schema changes and implementation pointers, and are merged back into the canonical spec once the change ships. Triggers on "propose a change to the spec", "draft a change spec", "RFC for X", or "merge the change spec".

The plugin ships a companion **`development-guidelines`** skill that writes the spec set's development-guidelines page — the "rules of the road" (toolchain, code style, defensive coding, limits, version control, testing, AI-agent rules, definition of done). It detects the repo's languages (TypeScript, JavaScript, Rust, Python), applies a coding style (Tiger Style or Clean Code), and assembles the page from per-language templates following the spec conventions above. Triggers on "add development guidelines", "generate coding guidelines", or "add coding standards to the spec"; spec-creator delegates to it when a spec set includes a development-guidelines page.

It also ships a companion **`spec-reviewer`** skill that reviews specs with semi-formal certificate templates. Three modes: review a **change spec against the canonical spec** for broken references, stale targets, and contradictions; review a **canonical spec against the implemented code** to find missing implementations, incorrect implementations, and shipped features the spec never captured; and review a **change spec against the code** to determine whether its proposed delta has shipped (none/partial/implemented) and, if partial, which gaps remain. Each review ends with a fixed verdict and concrete suggestions; the reviewer surfaces divergences and hands any authoring back to spec-creator. Triggers on "review this change spec", "does the implementation match the spec", "check the spec against the code", "find spec divergences", or "has this change spec been implemented".

## The pipeline

spec-creator is the head of a three-plugin pipeline: **spec-creator** writes the spec → **[spec-planner](../spec-planner)** decomposes it into a dependency-ordered, reviewable task plan → **[spec-builder](../spec-builder)** implements that plan, gating each task through a correctness review and a definition-of-done check. The downstream plugins are optional and installed separately; spec-creator stands on its own.

## Install

```
/plugin marketplace add antstanley/skills
/plugin install spec-creator@skills
```

## Skill content

The main skill lives at [`skills/spec-creator/SKILL.md`](skills/spec-creator/SKILL.md). Worked examples and templates are under [`skills/spec-creator/evals/`](skills/spec-creator/evals/) and [`skills/spec-creator/references/`](skills/spec-creator/references/).

The companion guidelines skill lives at [`skills/development-guidelines/SKILL.md`](skills/development-guidelines/SKILL.md), with the language-agnostic Tiger Style core and per-language templates under [`skills/development-guidelines/references/`](skills/development-guidelines/references/).

The companion review skill lives at [`skills/spec-reviewer/SKILL.md`](skills/spec-reviewer/SKILL.md), with one procedural review template per mode — [`skills/spec-reviewer/references/r1-change-vs-canonical.md`](skills/spec-reviewer/references/r1-change-vs-canonical.md) (change spec vs canonical), [`skills/spec-reviewer/references/r2-canonical-vs-code.md`](skills/spec-reviewer/references/r2-canonical-vs-code.md) (canonical vs code), and [`skills/spec-reviewer/references/r3-change-vs-code.md`](skills/spec-reviewer/references/r3-change-vs-code.md) (change spec vs code), each with a worked example.
