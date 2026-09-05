# Design evidence record

Use this record when asked to capture design acceptance evidence, or when a design task
needs a reviewable evidence handoff. It records observations against adopted requirements;
it neither adopts new design policy nor changes the UI. Reuse the project's existing
artifact layout. With a plan, keep the record beside its task/review artifacts; otherwise
use `.specs/reviews/YYYY-MM-DD-<scope>-design-evidence.md`. Choose an unused descriptive
name and link it from the task or review. Do not overwrite historical results.

Resolve global design guidelines and applicable package deltas before selecting checks.
Each row links to its exact requirement and records a route/screen, state, expected
behavior and evidence. Keep source inspection, rendered appearance, keyboard interaction,
and assistive-technology results separate when they prove different things. Reuse shared
environment details by ID rather than copying them into every row.

A revision alone is insufficient when testing a dirty tree: record relevant changed paths
and content hashes or a saved patch. Record the tested build, not merely the checkout at
report-writing time. Supplied evidence is attributed to its author/report; never label it
as an independent check you performed. Before reusing older evidence, establish that its
requirements, relevant implementation and environment still apply. A different commit
alone does not invalidate unrelated evidence, but an unverified relationship leaves the
current claim `not tested`. Missing metadata, missing artifacts and stale observations
remain explicit; preserve the historical outcome separately from the current assessment.

Use the existing accessibility evidence labels: `verified`, `failed`, `not tested`, or
`not applicable` with rationale. A failed criterion stays failed after an approved deferral.
An unavailable browser or screen reader leaves the relevant check not tested. A source
assertion cannot prove rendered behavior, and an automated scan or screenshot cannot prove
keyboard activation or screen-reader announcements. Refer to
[accessibility.md](accessibility.md) for the policy/evidence boundary.

Adapt this skeleton, removing placeholders. Do not invent evidence to fill a field.

```markdown
# Design evidence — <scope>

**Date:** YYYY-MM-DD · **Collector:** <human/agent/tool identity> · **Scope:** <surfaces>
**Requirements:** <global guideline and applicable package-delta links/anchors>
**Implementation:** <tested revision/build; relevant dirty-file hashes or patch if needed>
**Related task/review:** <resolving link, when one exists>

## Environments

| ID | Browser/platform | Viewport, zoom/text size | Theme/motion | Assistive technology | Tools |
|---|---|---|---|---|---|
| E1 | <name/version, OS; device or emulation> | <actual values> | <actual preferences> | <name/version or not used/unavailable> | <actual command/version or manual method> |

## Results

| ID | Requirement | Route/screen and state | Environment | Expected behavior | Method and actual observation | Evidence | Current result and rationale |
|---|---|---|---|---|---|---|---|
| D1 | <link/anchor and criterion or project rule> | <journey/state> | E1 | <observable expectation> | <steps and actual outcome; performed here or supplied by whom> | <artifact link plus capture revision/date; or unavailable> | <verified / failed / not tested / not applicable; why> |

## Coverage and limits

<Requirements/states inspected and those excluded, with reasons. Missing environment or
artifact metadata. Full process coverage versus sampled components. Outstanding browser,
keyboard or assistive-technology checks. No broader claim than these results support.>

## Follow-up

| Result ID | Barrier or missing evidence | Resolution evidence needed | Owner/tracking |
|---|---|---|---|
| <D1> | <known failure or verification gap> | <concrete recheck> | <known owner/link or unassigned> |

<For a recheck, link the previous record and identify the result being superseded. Keep
historical failures available; only a new applicable passing check resolves a current gap.>
```

These row labels do not replace spec-reviewer verdicts or builder done certificates.
Keep large logs/screenshots with the project's review artifacts and link them, rather
than copying them into canonical policy. Verify local links. If temporary evidence must
be cleaned up, retain a compact durable record/archive in an agreed location and update
references before removing its source files. Never claim a removed artifact still exists.
