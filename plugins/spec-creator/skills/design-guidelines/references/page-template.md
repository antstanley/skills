# Design-guidelines page template

Select relevant sections; remove instructional placeholders from the output. A small
product needs a short page. Do not populate absent token categories or impose one visual
identity across unrelated packages merely to complete this skeleton.

```markdown
# Design Guidelines

**Status:** Draft · **Date:** YYYY-MM-DD · **Owner:** <human owner> · **Scope:** Repo-wide

<What surfaces the page governs and what design discipline the project adopts. For a
greenfield project, explicitly distinguish adopted policy from UI not yet implemented.>

## Context and authority

<Audience and task context, referencing existing product specs rather than repeating them.>

| Source | Authority | Evidence scope |
|---|---|---|
| <relative link to actual token/theme source> | <exact values and aliases> | <what was inspected> |
| <existing brand document, if any> | <identity commitments> | <revision or scope> |

<State any unresolved conflict in the closing block. Preserve existing DESIGN.md as an
input; do not introduce a competing export or overwrite it as a side effect.>

## Design principles

| Adopted principle | Consequence for design |
|---|---|
| <project-specific principle> | <observable rule that guides another screen> |

## Visual foundations

| Foundation | Adopted usage | Source or implementation evidence |
|---|---|---|
| Semantic color and themes | <roles, contrast treatment, state meaning> | <source or explicitly unimplemented policy> |
| Typography | <roles, hierarchy, readability, fallbacks> | <source> |
| Layout and density | <grid, spacing rhythm, content width, surface differences> | <source> |
| Shape and elevation | <borders, radius, depth and their meanings> | <source> |
| Imagery and iconography | <asset treatment, consistency, accessible alternatives> | <source> |

## Interaction conventions

<Applicable navigation, keyboard/focus, forms and feedback rules. Reference existing
component/API contracts. State shared behavior; feature specs own specific flows.>

| State or pattern | Expected behavior | Applicable surfaces |
|---|---|---|
| <loading, empty, error, success, disabled, selected, focus, as applicable> | <concrete behavior> | <scope> |

## Adaptation and accessibility

<Settled platform/accessibility requirements, responsive reflow, input methods, text
expansion, localization, zoom, themes, and relevant content extremes. Cite a named
external standard from its authoritative source if one has been adopted.>

<Record the adopted target/version/level and applicable journeys. If the target is
unsettled, say so and put the decision in Open questions. State stronger project policies
separately. Use accessibility.md to select concrete keyboard/focus, semantics, contrast,
forms/feedback, interaction, and media requirements. Link authoritative criteria without
presenting the selected examples as the whole standard.>

## Motion

<Purpose, permitted and excluded contexts, authoritative timing/easing sources where
they exist, and the reduced-motion alternative. Static interfaces are a valid choice.>

## Content and UX voice

<Labels, instructions, error guidance, tone, and terminology needed across surfaces.>

## Design definition of done

| Requirement | Scope and expected result | Evidence | Existing enforcement |
|---|---|---|---|
| <adopted requirement> | <surface/state and observable result> | <render, interaction check, or source inspection> | <verified command or manual review; no invented automation> |

<For applicable accessibility requirements, specify the automated/manual checks needed
and the environments to record. Observed checks use verified / failed / not tested /
not applicable (with rationale). Name revision, journey/state, browser/platform,
assistive technology when used, and relevant viewport/zoom/theme/preferences. Missing
evidence remains not tested; retain barriers in Open questions. Do not claim full
conformance from a sampled journey, screenshots, or automated results alone.>

## Assumptions and open questions

**Assumptions**

- <Facts the discipline relies on, or (None at this stage.)>

**Decisions**

- *<label>.* **<adopted choice>.** <Why it fits the audience and context.>

**Open questions**

- *<gap>.* <Known implementation/evidence gap and the question about resolving it.>
```

For revision-specific acceptance results, use [evidence-template.md](evidence-template.md)
and link the record from its task/review rather than expanding the canonical page into a test log.

## Examples of accurate claims

- **Policy:** "Every interactive control has a visible keyboard-focus treatment."
- **Implementation:** "Shared buttons use the focus-ring token defined in the linked
  theme source." Write this only after verifying the definition and usage.
- **Enforcement:** "The component test command exercises focus restoration for dialogs."
  Name the real command and test only after inspecting them.
- **Gap:** "Legacy dialogs do not restore focus. Which change will bring them into line
  with the adopted interaction rule?" Keep this in Open questions and report it.

For a greenfield page, an adopted palette can appear as policy, but a nonexistent
`theme.css` must not appear as its implementation source. A Draft header does not excuse
false implementation claims.

## Package delta

Use the existing package page name, or `NN-design.md`, with the same header and closing
block. Open with a resolving link such as:

```markdown
Read first: [global design guidelines](../../design-guidelines.md).
This page records the workbench's density and interaction differences.
```

The relative link above is for `.specs/<package>/specs/NN-design.md`; adjust it for other
layouts. Include only scoped differences and their rationale. Shared accessibility
requirements remain inherited; a local preference does not silently override a global
requirement. Resolve contradictory policies explicitly. Index both layers from their
appropriate READMEs; do not add package-specific dependencies to the global guidelines.
