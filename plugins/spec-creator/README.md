# spec-creator

Create or expand formal design specifications for an app, package, or codebase — numbered, layered, cross-linked markdown that defines what exists in the current branch.

Triggers on phrases like "create a spec", "spec out this app", "write design docs", "formalize the architecture", or when the user references using another project's specs as a template. The output is a numbered directory of markdown files plus a JSON Schema sidecar, layered as repo-wide globals + per-package specs.

It also writes **change specs** — single documents under `.specs/changes/` that propose a delta to the canonical spec, carry inline schema changes and implementation pointers, and are merged back into the canonical spec once the change ships. Triggers on "propose a change to the spec", "draft a change spec", "RFC for X", or "merge the change spec".

The plugin ships a companion **`development-guidelines`** skill that writes the spec set's development-guidelines page — the "rules of the road" (toolchain, code style, defensive coding, limits, version control, testing, AI-agent rules, definition of done). It detects the repo's languages (TypeScript, JavaScript, Rust, Python), applies a coding style (Tiger Style or Clean Code), and assembles the page from per-language templates following the spec conventions above. Triggers on "add development guidelines", "generate coding guidelines", or "add coding standards to the spec"; spec-creator delegates to it when a spec set includes a development-guidelines page.

The companion **`design-guidelines`** skill writes `.specs/design-guidelines.md` beside
development guidelines. On first use it asks focused design questions for greenfield work,
or inspects an existing interface and confirms intentional decisions and gaps. Both paths
summarize the direction before authoring; repeat runs ask only about changed decisions.
It records visual foundations, interaction, accessibility, motion, and a design definition
of done, with thin per-package deltas where needed. Adopted policy is distinguished from
implemented behavior and existing enforcement. Triggers include "add design guidelines"
and "document our design system in the spec"; spec-creator invokes it for visual surfaces.
It documents design without implementing a redesign or requiring an external design tool.
Accessibility guidance establishes a confirmed target (recommending WCAG 2.2 AA for
web projects without one), applicable journey requirements, and automated/manual
acceptance evidence. It separates standard criteria from stronger project policies
and records barriers and untested behavior without implying conformance. See the
[accessibility reference](skills/design-guidelines/references/accessibility.md).

It also ships a companion **`spec-reviewer`** skill that reviews specs with semi-formal certificate templates. Three modes: review a **change spec against the canonical spec** for broken references, stale targets, and contradictions; review a **canonical spec against the implemented code** to find missing implementations, incorrect implementations, and shipped features the spec never captured; and review a **change spec against the code** to determine whether its proposed delta has shipped (none/partial/implemented) and, if partial, which gaps remain. Each review ends with a fixed verdict and concrete suggestions; the reviewer surfaces divergences and hands any authoring back to spec-creator. Triggers on "review this change spec", "does the implementation match the spec", "check the spec against the code", "find spec divergences", or "has this change spec been implemented".

Design acceptance can be captured with the reusable [evidence record](skills/design-guidelines/references/evidence-template.md): requirement links, tested revision, route/state, environment, observations and artifacts, including failed and untested results. Ask design-guidelines to "record design evidence" without reopening design discovery. Ask spec-reviewer to "review design drift" for an R2 comparison of global/package policy against current implementation and evidence; it reports scoped findings and remedies without silently redesigning the interface. See [design drift](skills/spec-reviewer/references/design-drift.md).

## The pipeline

spec-creator is the head of a three-plugin pipeline: **spec-creator** writes the spec → **[spec-planner](../spec-planner)** decomposes it into a dependency-ordered, reviewable task plan → **[spec-builder](../spec-builder)** implements that plan, gating each task through a correctness review and a definition-of-done check. The downstream plugins are optional and installed separately; spec-creator stands on its own.

## Install

```
/plugin marketplace add antstanley/skills
/plugin install spec-creator@skills
```

### Codex

```sh
codex plugin marketplace add antstanley/skills
codex plugin add spec-creator@skills
```

Both platforms use the same skill content and plugin version. See
[publishing guidance](../README.md) for validation and release details.

## Skill content

The main skill lives at [`skills/spec-creator/SKILL.md`](skills/spec-creator/SKILL.md). Worked examples and templates are under [`skills/spec-creator/evals/`](skills/spec-creator/evals/) and [`skills/spec-creator/references/`](skills/spec-creator/references/).

The companion guidelines skill lives at [`skills/development-guidelines/SKILL.md`](skills/development-guidelines/SKILL.md), with the language-agnostic Tiger Style core and per-language templates under [`skills/development-guidelines/references/`](skills/development-guidelines/references/).

The design-guidelines skill lives at [`skills/design-guidelines/SKILL.md`](skills/design-guidelines/SKILL.md), with [discovery guidance](skills/design-guidelines/references/discovery.md), a [page template](skills/design-guidelines/references/page-template.md), and [eval fixtures](skills/design-guidelines/evals/evals.json).

The companion review skill lives at [`skills/spec-reviewer/SKILL.md`](skills/spec-reviewer/SKILL.md), with one procedural review template per mode — [`skills/spec-reviewer/references/r1-change-vs-canonical.md`](skills/spec-reviewer/references/r1-change-vs-canonical.md) (change spec vs canonical), [`skills/spec-reviewer/references/r2-canonical-vs-code.md`](skills/spec-reviewer/references/r2-canonical-vs-code.md) (canonical vs code), and [`skills/spec-reviewer/references/r3-change-vs-code.md`](skills/spec-reviewer/references/r3-change-vs-code.md) (change spec vs code), each with a worked example.
