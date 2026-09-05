---
name: design-guidelines
description: Create or update canonical design guidelines for a project's visual and interaction design. Use for "add design guidelines", "document our design system in the spec", or when spec-creator includes a design-guidelines page. Supports greenfield design discovery and adoption of an existing interface, producing .specs/design-guidelines.md or a thin per-package delta. Does not implement or redesign the UI.
---

# Design Guidelines

Write the design discipline that humans and agents use to extend a product consistently.
This is a companion to `development-guidelines`, at the same level in the canonical spec
set. Read [spec-creator](../spec-creator/SKILL.md) for its header, voice, layering, and
closing-block conventions. This skill owns the design page; spec-creator owns the wider
spec set. Run inline on the session model.

## Scope and authority

The page records adopted visual and interaction rules, their sources, and the evidence
needed to assess implementation. It covers human-facing visual surfaces: websites,
product interfaces, native apps, and reading surfaces. Select only relevant topics.
A backend-only library does not acquire a visual-design page automatically. If explicitly
asked for one, clarify the intended surface rather than inventing a brand for the library.

Distinguish three kinds of statement:

| Kind | What belongs in the canonical body | What must not be implied |
|---|---|---|
| Adopted policy | A settled commitment, such as visible keyboard focus | That every existing component already conforms |
| Observed implementation | Tokens, components, or behavior evidenced in this branch | That repetition proves deliberate intent or that code proves rendered usability |
| Enforcement | A check, command, or gate verified to exist | That an adopted requirement already has automated coverage |

This is the same policy exception used by development-guidelines. Record known gaps in
the closing Open questions and report them; do not weaken an adopted rule to match a bug.
Unconfirmed options stay out of the canonical body. Proposed screen changes or redesigns
follow spec-creator's change-spec workflow; writing guidelines does not implement them.

Existing brand commitments and the user's intent take precedence over generic taste
advice. Preserve the project's framework, token names, and design system. Avoid blanket
font bans, mandatory animation libraries, or a default premium/experimental aesthetic.

## Workflow

### 1 — Locate the spec set and inspect the project

Read `.specs/README.md`, existing design and development guidelines, package overviews,
and any supplied brief. Inspect existing `DESIGN.md`, brand documentation, token sources,
theme configuration, shared components, and representative screens. Use available browser
tools or current visual fixtures when relevant; if only source is available, state that
rendered appearance and interaction remain unverified. Do not install tools or start a
redesign merely to document the project.

Choose placement using the existing spec layout:

- Shared rules live at `.specs/design-guidelines.md`, scoped `Repo-wide`, beside
  `.specs/development-guidelines.md`.
- Genuine package differences live at `.specs/<package>/specs/NN-design.md`, using the
  next suitable reading-order number. Reuse an existing design page instead of adding
  a competing one. It opens with a Read first link to the global page and contains only
  deltas. Global rules may be narrower than one universal visual identity: unrelated
  products can share accessibility discipline while owning different brands locally.
- Screen-specific layouts, flows, and feature states belong in feature specs. The
  guidelines define reusable conventions rather than enumerate every screen.

Missing guidelines alone do not mean greenfield. Select the discovery path from the
surface's actual assets and implementation. A new package inside an established product
inherits applicable global decisions before resolving its own gaps.

### 2 — Discover and confirm design decisions

On first use, read [references/discovery.md](references/discovery.md). It supplies the
greenfield and existing-project paths and example questions. Both paths end with a short,
reviewable design summary before the canonical page is written.

- **Greenfield:** ask focused questions about the audience and primary tasks, brand and
  references, platforms and constraints, and unresolved visual/interaction direction.
  Offer concrete alternatives and explain their implications when the user has no
  preference. Do not silently select a complete visual identity.
- **Existing project:** inspect first, summarize observed choices with evidence, then ask
  follow-up questions to confirm intent and resolve gaps or inconsistencies. Establish
  whether the intended treatment is preserve, consolidate, or change. An isolated oddity
  is not a design-system rule merely because it exists in code.
- **Subsequent use:** read the established decisions and ask only about material changes
  or unresolved choices. Do not repeat onboarding or replace settled rules unprompted.

Ask in small rounds (usually one to three questions), skipping facts already supplied or
confirmed in the session. The summary distinguishes settled decisions, observed but
unconfirmed choices, proposed policy, and known implementation gaps. Ask for confirmation
only of material decisions that remain unresolved. If the user already approved the
direction or explicitly delegated those choices, state the summary and proceed without
another approval gate. If required answers are unavailable, leave discovery pending;
do not treat silence as agreement or publish guesses as adopted policy.

### 3 — Author the page

Read [references/page-template.md](references/page-template.md) and select applicable
sections. Resolve the spec owner and date using session/repository context. Follow the
standard Status/Date/Owner/Scope header and closing Assumptions/Decisions/Open questions.

Make decisions usable by someone building another screen:

- Explain a principle through observable consequences. "Calm" might mean stable layouts,
  state-change feedback, and no ambient animation on operational screens.
- Record visual foundations by semantic role, usage, and authoritative source. Link
  existing CSS/theme/token definitions instead of maintaining a second full inventory.
  Exact values belong in the page only when they are adopted policy or verified values;
  identify which, and avoid claiming a proposed token already exists.
- Specify applicable state behavior, responsive adaptations, keyboard/focus conventions,
  content extremes, and reduced-motion behavior. Brand expression can differ between
  marketing, operational, and reading surfaces without changing shared foundations.
- Name the adopted accessibility target and relevant platform conventions when settled.
  Verify any named external standard/version from its authoritative source. Do not
  claim compliance from a screenshot, a library choice, or an automated scan alone.
- Keep UX voice and labels here; development-guidelines owns coding style and toolchain.
  Reference existing component/API specs rather than duplicating their contracts.

For greenfield projects, the page establishes confirmed policy and explicitly says the
UI and enforcement are not implemented. It does not fabricate installed fonts, tokens,
components, screenshots, or passing checks. Leave undecided values in Open questions.

### 4 — Define design acceptance and expose gaps

Write a `## Design definition of done` with requirements that apply to relevant UI tasks.
For each requirement, identify the surface/state, expected behavior, and evidence type.
Link actual commands when automated checks exist; label manual review honestly. Examples:

- Inspect a dialog's keyboard entry, focus containment, dismissal, and focus restoration.
- Render the agreed narrow and wide layouts with representative long content; inspect
  reflow, clipped text, and control access.
- Check the selected loading, empty, error, and success states against their conventions.
- Verify the reduced-motion alternative for any motion added by the task.
- Compare representative current renders with adopted visual rules and applicable
  references; use token checks for exact values and visual review for hierarchy.

Select checks appropriate to the product and task, not an indiscriminate checklist.
Do not invent a test command or require visual snapshots on backend-only tasks. Missing
rendered evidence remains an explicit verification limitation, not a passing result.
Planned automation goes in Open questions; manual acceptance can be adopted now.

### 5 — Cross-link and hand off

When invoked independently, update `.specs/README.md` to index the global page and any
package delta. Update the package README and overview detail-pages table as applicable.
Preserve dependency direction: package pages link to globals; global guidelines do not
depend on package-specific pages. Verify relative links from their actual file locations.

When invoked by spec-creator, reuse its established scope, owner, date, and discovery
answers. Return the page paths, adopted decisions, unresolved questions, and gaps to its
Phase 4 cross-link pass; do not ask the same questions again.

Run the [spec-creator checklist](../spec-creator/references/checklist.md), applying the
policy/implementation distinction above. Tell the user what was written, what evidence
was inspected, and what remains unverified. Offer a change spec for surfaced implementation
work under spec-creator's existing rules; do not create it as a side effect.

Downstream, spec-planner reads `Design definition of done` and relevant package deltas for
UI tasks. Builder briefs carry those rules, and review uses code, rendered output, and
interaction evidence as appropriate. The authoring skill itself does not run a redesign.

## Supporting references

- [discovery.md](references/discovery.md): first-use questions, existing-project adoption,
  mixed contexts, and repeat-use behavior. Read before discovery.
- [page-template.md](references/page-template.md): adaptable page structure and examples
  of policy versus implementation. Read before authoring.
- [sources.md](references/sources.md): research provenance and the boundaries of the
  adaptation. Read when extending the skill's design guidance.
