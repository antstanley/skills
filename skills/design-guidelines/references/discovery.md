# Design discovery

Discovery resolves decisions that change what builders should produce. It is not a
mandatory questionnaire: use existing context, ask the next useful question, and stop
when the direction is sufficiently settled to write accurate guidelines.

## First-use routing

| Evidence | Path |
|---|---|
| No UI, brand, or established visual system | Greenfield discovery |
| Existing UI or meaningful brand/design assets, even without a guidelines file | Existing-project adoption; ask about remaining greenfield aspects |
| A new surface within an existing product | Inherit shared decisions, then discover local differences |
| Existing canonical guidelines | Incremental update; revisit only affected decisions |

Do not equate missing `DESIGN.md` with absence of design. Existing screenshots can also be
stale: compare their target, theme, and revision with current styles before relying on them.

## Greenfield conversation

Start with what the user has already supplied. Cover these topics only where unresolved:

| Topic | Useful question | Decision it informs |
|---|---|---|
| Audience and success | Who uses this, and what should they accomplish most often? | Task hierarchy, clarity, and appropriate density |
| Product surfaces | Is the current scope a marketing site, working interface, reading surface, native app, or a combination? | Surface-specific behavior and platform expectations |
| Identity | Are there brand assets or references to follow, and what do you like or dislike about them? | Typography, color, imagery, and expression |
| Constraints | Which devices, input methods, accessibility needs, languages, or existing systems must it support? | Adaptation and interaction requirements |
| Accessibility target | Is an accessibility target already adopted, and which journeys and platform constraints matter most? For an unspecified web target, propose WCAG 2.2 AA. | Confirmed target/scope and additional commitments; follow [accessibility guidance](accessibility.md) |
| Remaining direction | Should this use a compact working layout or a spacious guided flow, and why? | A concrete choice appropriate to the audience |

Usually ask one to three questions per round. Offer two or three relevant directions when
the user is unsure, with practical implications. Do not ask users to supply hex values or
score abstract taste dials unless that is how they want to work. Translate preferences
into proposed rules, for example "restrained motion" into state-change transitions with
a reduced-motion alternative. A numeric motion score alone is not an acceptance criterion.

Example: the user says "a calm scheduling app for receptionists on desktop and tablets."
Do not ask again who it is for or which devices it supports. Ask whether speed for trained
staff or guidance for occasional staff takes priority, and whether an existing brand must
be followed. Use the answers to propose density and interaction conventions.

If the user says "choose for me," make context-appropriate recommendations, state the
chosen direction in the summary, and proceed. This is explicit delegation, not silence.

## Existing-project adoption

Inspect representative evidence before asking the user to describe what is already there:

1. Read design/brand documents, existing guidelines, and relevant product specs.
2. Inspect token and theme definitions, global styles, component variants, and assets.
3. Sample important surfaces and states. Where tools permit, inspect current renders and
   keyboard behavior; otherwise name the missing evidence.
4. Compare patterns across surfaces. Separate shared foundations from local differences
   and accidental one-offs. Conflicting old docs and code are a question, not permission
   to silently declare whichever is easiest authoritative.

Prepare a short evidence summary:

| Observation | Evidence | Follow-up |
|---|---|---|
| Most controls share a tokenized radius | Theme source and shared input/button components | Confirm only if intent or scope is uncertain |
| One legacy form uses unrelated colors | Form styles differ from shared semantic tokens | Is this a deliberate exception or inconsistency to consolidate? |
| Marketing pages animate; work screens are static | Current representative renders | Confirm whether this surface distinction is intentional |
| No focus tests were found | Test configuration and source inspection | Separate the adopted keyboard rule from absent automation |
| An automated audit passed, but keyboard activation was not inspected | Audit scope and missing interaction evidence | Record the audit's bounded result and mark the remaining journey checks not tested |

Establish the desired treatment if it is not already clear:

- **Preserve:** document the incumbent identity and intentional behavior.
- **Consolidate:** adopt a consistent rule from existing patterns and list implementation
  gaps; do not silently update components.
- **Change:** record the requested direction and distinguish policy from proposed UI
  changes. Route implementation work through a change spec when requested.

Questions should reference evidence: "The shared theme uses compact controls, while the
new settings screen uses larger spacing. Is settings an intentional exception?" is more
useful than asking the user to pick a design style from scratch.

## Reviewable summary before writing

Use a short paragraph or table covering:

- Surfaces and audiences in scope.
- Existing authorities and adopted principles.
- Direction for typography, color, density, interaction, and motion as far as settled.
- Shared rules versus package-specific differences.
- Accessibility target and scope, stronger project policies, observed barriers, and
  required evidence as far as settled; a target is not a compliance claim.
- Observed inconsistencies, proposed policies, and evidence limitations.
- Remaining material decisions requiring an answer.

Invite correction or confirmation of unresolved decisions before writing them as policy.
Previously confirmed decisions do not need approval again. When an unresolved detail is
nonblocking, agree the settled part and place that detail in Open questions. If a major
choice is unresolved and the user is unavailable, report the pending question and retain
the discovery summary; do not manufacture agreement.

## Subsequent runs

Read existing guidelines and their Decisions first. Inspect the requested change and
relevant evidence. Ask only about new contradictions or missing choices. Preserve unrelated
decisions and their rationale. A request to add dark-mode guidance is not authorization
to change the brand, density, or component library.
