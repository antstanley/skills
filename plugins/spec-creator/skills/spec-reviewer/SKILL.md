---
name: spec-reviewer
description: Review a canonical spec or a change spec for inconsistencies, divergence, and implementation status, using semi-formal certificate templates. Three modes — (1) review a change spec against the canonical spec it targets for broken references, stale targets, and contradictions; (2) review a canonical spec against the implemented code to find missing implementations, incorrect implementations, and shipped features the spec never captured; (3) review a change spec against the code to determine whether its proposed delta has shipped (none/partial/implemented) and, if partial, which gaps remain. Triggers on "review the spec", "review this change spec", "check the change spec against the canonical spec", "does the implementation match the spec", "check the spec against the code", "find spec divergences", "is the spec still accurate", "spec conformance review", "validate the change spec before merge", "has this change spec been implemented", "is the change spec done", "how much of the change spec is implemented".
---

# Spec Reviewer

A skill for reviewing specifications with a disciplined, certificate-style method: state premises, resolve every reference through a fixed sequence, trace concrete claims, classify each divergence, and end with a verdict and actionable suggestions. It catches the failure modes that ordinary reading misses — a change spec that points at a heading that no longer exists, a canonical page that quietly describes a feature the code never shipped.

This skill is a companion to **spec-creator**. It reviews the specs that skill produces and obeys its conventions. Read [`spec-creator`'s `SKILL.md`](../spec-creator/SKILL.md) first if you have not; this skill assumes the canonical-vs-change distinction, the layered structure, and the "describes-what-exists" core principle, and does not restate them.

The review method is a semi-formal certificate procedure: literal numbered steps, a resolution sequence with STOP rules, mandatory checkpoints before any verdict, and a worked example. Each mode has its own full template — [`references/r1-change-vs-canonical.md`](references/r1-change-vs-canonical.md), [`references/r2-canonical-vs-code.md`](references/r2-canonical-vs-code.md), and [`references/r3-change-vs-code.md`](references/r3-change-vs-code.md) — read the relevant one before reviewing; do not reconstruct the steps from memory.

## Core principle

**A review produces a verdict backed by traced evidence, not an impression.** Every issue the review reports is tied to a specific reference that did not resolve, a specific spec claim that did not map to code, or a specific contradiction between two pieces of prose. The verdict follows a fixed rubric, so the same spec earns the same verdict regardless of who runs the review.

The skill inherits spec-creator's reality rule and uses it as the test for its code-facing modes: **a canonical body claim that no code backs is a divergence.** The reviewer's job is to surface it — flag it, route it to an Open question or a change spec — never to soften it into "deferred" or quietly edit the body to match a half-built feature.

## When to apply this skill

Three review modes. Pick by what the user points at.

- **Change-spec consistency review (Template R1).** The user has a change spec under `docs/specs/changes/` and wants it checked against the canonical spec it targets — before acceptance or before merge. Triggers: "review this change spec", "is the change spec consistent with the spec", "validate the change spec before merge", "does this RFC still line up with the spec".
- **Spec–code conformance review (Template R2).** The user wants the canonical spec checked against the implementation: what the spec claims that the code lacks (missing), what the code does differently (incorrect), and what the code ships that the spec never mentions (unspec'd). Triggers: "does the implementation match the spec", "check the spec against the code", "find spec divergences", "is the spec still accurate", "audit the spec against what we built".
- **Change-spec implementation review (Template R3).** The user wants to know whether a change spec's proposed delta has actually shipped — and if only partly, which gaps remain. The output is an implementation status (NONE / PARTIAL / IMPLEMENTED) with a gap list. Triggers: "has this change spec been implemented", "is the change spec done", "how much of the change spec is implemented", "did we finish the tagging change", "is this RFC ready to mark Implemented".

Modes can run together when the user asks for a full review ("review the whole spec set"): run R2 on each canonical page, then R1 on any pending change spec. Use R3 instead of R1 when the question is about implementation progress rather than consistency — and R3 then R1 in sequence when confirming a change spec is both fully built and still consistent before flipping it to Implemented and merging.

Skip if the request is to *write* or *change* a spec rather than review one — that is spec-creator's job. Skip the certificate templates for a one-line typo fix in a spec; just fix it.

## Inputs

Resolve these before reviewing.

1. **Locate the spec set.** Find `docs/specs/` (global) and `docs/<app>/specs/` (per-app). Read `docs/README.md` to learn the layout. For R1 and R3, also locate the change spec under `docs/specs/changes/`.
2. **Read the canonical pages in scope, end to end.** You cannot judge a delta or a claim without the base. Read the canonical schema (`canonical-types.schema.json`) too — many divergences are schema-vs-prose or schema-vs-code. For R3, read the change spec's `Type changes` fragment and `Implementation notes` closely — they name the entities, fields, migrations, and call sites the code must show.
3. **For R2 and R3, locate the implementing code.** For R2, map each canonical page to the package, module, or routes it describes. For R3, start from the change spec's `Implementation notes` `file:line` pointers and widen as needed. If the mapping is unclear, ask the user which paths to check rather than guessing.
4. **Confirm the mode.** State which template you are applying (R1, R2, R3, or a combination) before producing the review, so the user can redirect if you picked wrong.

## Workflow

### 1 — Decide whether the templates apply

The certificate templates exist to catch cross-reference and cross-artifact errors. Skip them, and review normally, when:

- The spec change is trivial (a typo, a date bump, a formatting fix).
- There are no references to resolve and no code to map (a single self-contained prose page with no entities, no cross-links).

Otherwise apply the matching template literally.

### 2 — Apply the template

Open the matching template — [`references/r1-change-vs-canonical.md`](references/r1-change-vs-canonical.md) (change spec vs canonical), [`references/r2-canonical-vs-code.md`](references/r2-canonical-vs-code.md) (canonical vs code), or [`references/r3-change-vs-code.md`](references/r3-change-vs-code.md) (change spec vs code) — and follow it step by step. Write out each step's result; do not summarize past a checkpoint. The resolution sequences (which page/heading/symbol/code-counterpart a reference points to) are mandatory — trace each one rather than assuming the obvious target.

When modes combine:

- **R2 + R1 (full spec-set review):** run R2 first (establish whether the canonical base is itself accurate), then R1 (check the proposed delta against that base). A change spec built on a stale canonical page is worth knowing about before reviewing the delta.
- **R3 + R1 (clearing a change spec to Implemented/merge):** run R3 first (confirm the code is fully built), then R1 (confirm the change spec is still consistent with canonical). Only flip the change spec to Implemented when R3 returns IMPLEMENTED.

### 3 — Report the verdict and suggestions

Each template ends with a fixed verdict block (`VERDICT / CONFIDENCE / SUMMARY`) followed by concrete, actionable suggestions — one per issue found, phrased as the edit that resolves it. Map each suggestion to a remedy that respects spec-creator's rules:

- **Stale or broken reference in a change spec** → fix the path/heading, or refresh the Modify block against the current canonical text.
- **Contradiction between change spec and canonical** → resolve in the change spec (it is the document allowed to describe the future), never by silently editing the canonical body.
- **Spec claim with no code (R2)** → flag as a divergence; offer to move it to an Open question or to draft a change spec. Do not edit the body to pretend the feature exists.
- **Code feature absent from the spec (R2)** → offer to add a body section (the code is the reality), following spec-creator's section conventions.
- **Incorrect implementation (R2)** → name which side is the intended source of truth, and route accordingly: spec stale → update the page; code wrong → flag to the user, the fix is a code change, not a spec edit.
- **Unimplemented or partial change spec (R3)** → report the status and the gap list; the next steps are code changes that close the gaps, and the change spec stays at `Accepted`. When R3 returns IMPLEMENTED, the next step is the lifecycle move — flip the change spec to `Implemented` and proceed to merge (R1 + the merge procedure). The reviewer does not write the missing code or flip the status unprompted.

The reviewer suggests and routes; it does not rewrite canonical pages or change specs unprompted. Offer the edits; let the user choose. When the user accepts an edit that writes or changes a spec, that work is **spec-creator's** — hand back to it for the actual authoring and its Phase 4 cross-link pass.

## When invoked by spec-creator

spec-creator may delegate here at three points: after drafting a change spec (run R1 to confirm the delta is consistent before presenting it); during its investigation phase when the user reports the code may have drifted from an existing spec (run R2 to enumerate divergences before any rewrite); and when the user asks to merge a change spec (run R3 first to confirm the proposed delta has actually shipped before the merge proceeds). In each case the spec set, owner, and date are already established — skip input step 1, confirm the mode, and produce the review. spec-creator owns any resulting edits and the final cross-link pass.

## Reference files

- [`references/r1-change-vs-canonical.md`](references/r1-change-vs-canonical.md) — **R1**, the change-spec-vs-canonical template: reference resolution, consistency trace, schema check, verdict rubric, worked example. Read before reviewing a change spec.
- [`references/r2-canonical-vs-code.md`](references/r2-canonical-vs-code.md) — **R2**, the canonical-vs-code template: claim resolution forward pass, coverage reverse pass, divergence classification, verdict rubric, worked example. Read before reviewing a spec against the implementation.
- [`references/r3-change-vs-code.md`](references/r3-change-vs-code.md) — **R3**, the change-spec-vs-code template: expectation extraction, implementation resolution, status determination (NONE / PARTIAL / IMPLEMENTED), gap list, worked example. Read before checking whether a change spec has shipped.
- [`../spec-creator/references/change-specs.md`](../spec-creator/references/change-specs.md) — the change-spec document type and merge procedure. Read before R1 and R3; the merge plan is what R1 protects, and R3 gates the move to Implemented before that merge.
- [`../spec-creator/references/checklist.md`](../spec-creator/references/checklist.md) — the pre-handoff checklist. Its Branch-reality and Cross-links sections are the structural rules R1 and R2 verify against.
