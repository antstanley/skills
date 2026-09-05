# Design drift review (R2 adaptation)

Use for "review design drift", "has the UI drifted from our guidelines", or a scoped
comparison of implemented visual/interaction behavior to canonical design policy. This
is R2 applied to design, not a fourth mode or an automatic redesign. Read R2's complete
procedure and rubric. Produce a review and evidence record; do not edit the UI, accept
observed deviations as policy, or overwrite the canonical guidelines as a side effect.

## Establish the comparison

Read the current global design guidelines, applicable package deltas and their decisions.
Resolve inheritance before judging a local difference: an adopted compact admin layout
need not match an expressive marketing page. A package cannot silently weaken shared
accessibility commitments; an unresolved contradiction is a policy concern.

State routes/components and states in scope, canonical revision, implementation/build
identity, and available evidence. Select relevant typography, semantic colors, spacing,
component variants, responsive/content extremes, focus, motion and accessibility rules.
Map each to its actual token, component boundary and rendered or interactive behavior;
there is no universal palette, font ban or preferred aesthetic in this review.

Use [the design evidence record](../../design-guidelines/references/evidence-template.md)
for results and artifact/environment provenance, reusing an existing compatible record.
Check old evidence against the current requirements and relevant source/build changes.
Do not discard it solely because unrelated files changed; do not accept it merely because
an earlier task passed. Unknown revision, changed relevant code, missing artifacts or
inadequate state coverage leave current behavior unverified until appropriate evidence
is collected. Attribute supplied checks without claiming you ran them.

## Apply R2 in both directions

In the forward pass, separate policy adoption, implementation compliance and enforcement.
An adopted rule can be confirmed while its UI implementation is failed or not tested.
For each applicable rule, resolve source and then the evidence needed for its observable
claim. A token declaration does not prove a nested component uses it; screenshot appearance
does not prove subsequent focus movement. Capture available authorized checks, without
inventing commands, installing tools, or expanding into unrelated UI fixes.

In the reverse pass, inspect significant UI patterns in the selected surfaces for rules
missing from the spec. Repetition alone does not establish intentional policy. A new
component variant is a candidate omission to confirm, not a reason to redesign the page.
For each finding, record the guideline anchor, implementation location, route/state,
evidence IDs, impact on the adopted rule and a concrete remedy. Distinguish:

- **Implementation drift:** evidenced mismatch/missing behavior against settled policy.
  Preserve the rule and propose a scoped implementation change.
- **Documentation drift:** implementation differs and an authoritative accepted decision
  establishes the new intent. Propose the corresponding spec update; observed code alone
  is insufficient authority to replace policy.
- **Unspecified pattern or policy conflict:** report as unresolved, with the intent or
  inheritance decision needed. Do not choose a winner silently.
- **Verification gap:** the required observation is unavailable or stale. Name the exact
  recheck; absence of evidence is not evidence of a missing implementation.

Known disclosed barriers remain findings. Deferrals and exceptions do not become passes.
Keep an issue's historical result separate from current evidence; a verified fix can
close that scoped finding without claiming the entire site conforms.

## Report and hand off

Use the existing R2 verdicts: any proven MISSING/MISMATCH yields `DIVERGES`; otherwise
unverified compliance, unresolved policy or significant unspecified patterns yield
`CONCERNS`. `LIKELY_CONFORMS` only covers incomplete code context when every checked
claim has its required evidence; it is not a substitute for missing rendered/interaction
checks. `CONFORMS` is limited to the stated scope and requires the relevant forward and
reverse checks. Evidence labels are per observation, not replacements for these verdicts.

Keep the report beside an existing task/review. Otherwise choose an unused
`.specs/reviews/YYYY-MM-DD-<scope>-design-drift.md`, index it in `.specs/README.md`, and
link the evidence record. Include R2's premises, forward/reverse resolution, classified
findings, edge cases and verdict, plus the inspected scope and untested remainder.
Propose one concrete follow-up per finding; author fixes only when separately requested
or already authorized in the session. Creating a review does not adopt a formal
accessibility target or establish site-wide conformance.
