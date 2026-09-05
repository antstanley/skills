# Accessibility in design guidelines

Accessibility is part of the shared design contract. This reference helps author that
contract and its acceptance criteria; it does not turn guideline creation into a full
accessibility audit or authorize UI fixes, tool installation, or changes to project scope.

## Establish the target

Read existing accessibility policies, design decisions, component documentation, and
product constraints first. Record the adopted standard/version/level, applicable surfaces,
important journeys, and any additional project commitments. A target states intent, not
verified conformance or a legal conclusion.

For web projects without a settled target, recommend **WCAG 2.2 Level AA**. Confirm that
recommendation using the skill's existing discovery rules, or adopt it when the user has
delegated the choice. Do not silently replace an existing target or treat silence as
agreement. If the choice is nonblocking, author settled requirements and leave the target
question open. A narrow incremental update does not trigger unrelated onboarding.

Use the [W3C Recommendation](https://www.w3.org/TR/WCAG22/) as the authority and its
[Understanding guidance](https://www.w3.org/WAI/WCAG22/Understanding/) for interpretation.
For AA, account for all applicable A and AA criteria in the declared scope; the examples
below are not an exhaustive checklist. Conformance covers full pages and complete
processes, not only the components sampled during discovery.

For native or mixed products, establish platform-specific accessibility guidance and
assistive-technology expectations. Do not assert that a web checklist alone establishes
native accessibility. Verify any named platform requirements from their official sources.

## Discover without prescribing users' abilities

| Starting point | Inspect or ask | Record |
|---|---|---|
| Greenfield | Existing commitments; important journeys; target platforms/input methods; known assistive-technology needs; component-library constraints | Confirmed policy, absent implementation, and planned acceptance evidence |
| Existing project | Current semantic structure, keyboard behavior, themes/contrast, zoom/reflow, forms/status feedback, and relevant media; available audits and tests | Observed barriers, intentional identity, target, and evidence limits |
| Existing guidelines | Decisions and only the surfaces affected by the requested update | Target inherited; new contradictions or gaps made explicit |

Do not require users to disclose disabilities or name every assistive technology before
writing useful guidelines. Offer a practical testing proposal when that detail is unknown.
Ask one to three material questions at a time, reusing supplied answers. Preserve identity
while identifying barriers; brand preference does not make a failed requirement pass.

## Requirements to make concrete

Select relevant areas for the product. Link specific criteria from the adopted standard
when translating them into acceptance rules; verify thresholds, levels, and exceptions
rather than inventing a simplified universal rule.

| Area | Decisions and observable expectations |
|---|---|
| Keyboard and focus | All applicable actions work by keyboard; focus order is meaningful and visible; sticky content does not obscure focus contrary to the target; skip navigation works on activation; modal entry, containment, exit, and focus restoration are defined. |
| Visual adaptation | Text and control contrast meet applicable criteria in supported themes; information is not conveyed by color alone; zoom, reflow, and text-spacing changes preserve content and controls. |
| Semantics | Headings, landmarks, reading order, accessible names, roles, and states express the interface; prefer native controls where they meet the need. |
| Forms and feedback | Persistent labels/instructions, associated and understandable errors, recovery guidance, and announced status changes are specified for relevant flows. |
| Input and timing | Applicable target-size and spacing rules, alternatives to dragging/complex gestures, timeout handling, and accessible authentication are specified where those interactions exist. |
| Motion | Define preference-aware alternatives, pause/stop controls where required, and flashing limits; separate extra project motion policy from the selected conformance level. |
| Content and media | Meaningful images have appropriate alternatives; decorative images do not add noise; captions, transcripts, and audio description follow the applicable media criteria; instructions use clear language. |

Do not confuse stronger design preferences with standard minima. For example, WCAG 2.2
Target Size (Minimum) is AA while Target Size (Enhanced) is AAA, and Animation from
Interactions is AAA. A project can adopt stronger target sizes or reduced-motion rules
without claiming that every such rule is mandated by AA. Preserve the criteria's actual
conditions and exceptions. Component-library selection does not prove conformance.

## Acceptance and evidence

Put accessibility acceptance in `Design definition of done`, so existing planner and
builder handoffs inherit it for applicable UI tasks. Each item names the journey/state,
adopted criterion or project policy, expected behavior, and evidence needed. Keep supporting
evidence with the task/review artifacts and reference it instead of copying audit logs
into the canonical policy page.

Combine available automated checks with manual keyboard, visual, and assistive-technology
checks appropriate to the changed journeys. Name automated commands only after confirming
they exist. A screenshot cannot establish focus movement, announcements, or keyboard
activation. DOM/accessibility-tree inspection alone does not prove screen-reader behavior.
Automated tools alone do not establish accessibility; see
[W3C evaluation guidance](https://www.w3.org/WAI/test-evaluate/).

| Evidence result | Meaning |
|---|---|
| `verified` | The named check was performed and met the expectation in the recorded scope and environment. |
| `failed` | Evidence shows the expectation is unmet; record the barrier and affected journey. |
| `not tested` | Required evidence is missing, unavailable, stale, or insufficient; never count it as a pass. |
| `not applicable` | The criterion does not apply to this surface/state, with an explicit reason; an inaccessible implementation is not a reason. |

Record the revision, route/screen and state, browser/platform, assistive technology and
version when used, viewport/zoom, theme, and motion preference as relevant. A greenfield
project has acceptance requirements but no passing UI results. These labels describe
individual evidence items; they do not replace the spec pipeline's completion verdicts.

Example: for skip navigation, test first-Tab visibility, activate the link, and verify
subsequent keyboard navigation proceeds from main content. Test reduced-motion behavior
when it is adopted policy. Report only what those observations establish; one journey
does not establish site-wide conformance.

## Barriers and unresolved decisions

Keep the adopted requirement in the body and place known barriers, missing verification,
and unsettled targets in the closing Open questions. Identify the affected surface and
the evidence needed to resolve the gap. Offer implementation change specs through the
existing handoff workflow; do not create or implement them automatically.

An owner-approved deferral or documented design exception does not make a failed
criterion conformant. Package deltas inherit shared requirements; surface-specific
applicability needs a rationale. Resolve contradictory policy explicitly and do not
weaken the target to match existing defects.
