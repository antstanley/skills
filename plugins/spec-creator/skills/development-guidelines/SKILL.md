---
name: development-guidelines
description: Add a development-guidelines page to a canonical spec — the "rules of the road" page (toolchain, code style, defensive coding, limits, version control, testing, AI-agent rules, definition of done) rendered in a chosen coding style for the languages a repo uses. Triggers on "add development guidelines", "add a dev-guidelines page to the spec", "generate coding guidelines", "write the development-guidelines spec", "add coding standards to the spec", or when spec-creator needs to write its development-guidelines.md page. Produces a single global spec page at docs/specs/development-guidelines.md (or a thin per-app delta) following spec-creator's conventions.
---

# Development Guidelines

A skill for writing the **development-guidelines** page of a canonical spec: the rules of the road for everyone — humans and agents — writing code in a repository. Toolchain, pervasive coding style, defensive coding, limits, version control, per-language conventions, testing, repository hygiene, AI-agent emphases, and a definition of done.

This skill is a companion to **spec-creator**. It produces one page in the spec set — the `development-guidelines.md` global spec — and follows every spec-creator convention (header, voice, closing block, cross-linking, layering). Read [`spec-creator`'s `SKILL.md`](../spec-creator/SKILL.md) first if you have not; this skill assumes its conventions and does not restate them.

## Core principle

**The guidelines page is a spec page.** It obeys the spec-creator rule: the body describes what is true in the current branch. For a guidelines page that means:

- **The discipline is canonical the moment it is written.** A guideline ("two assertions per function", "no `any`") is a rule the repo adopts; the page is its authoritative statement. That is what exists — the policy — so it belongs in the body.
- **Toolchain rows describe tools actually in use.** A `Toolchain` row for a linter that is not wired into the repo is a divergence. Either the tool is set up (it belongs) or it is aspirational (it goes in Open questions, not the table).
- **Enforcement gates describe gates that exist.** "A pre-push hook runs `lint`" is body text only if the hook exists. A planned gate ("we will add a coverage floor") is an Open question, not a body claim.

When in doubt, separate the *rule* (a guideline the repo commits to — body) from the *mechanism that enforces it* (a hook, a CI gate — body only if wired up, else Open questions). Flag any divergence to the user rather than papering over it.

## Parameters

Three inputs shape the page. Resolve all three before writing.

### Languages

The page carries one conventions section per language the repo uses. **Detect, then confirm.**

1. **Detect.** Inspect the repo for language signals:
   - `package.json` / `tsconfig.json` / `pnpm-lock.yaml` → TypeScript or JavaScript (presence of `tsconfig.json` or `.ts`/`.svelte` files distinguishes TypeScript from plain JavaScript).
   - `Cargo.toml` / `rust-toolchain.toml` / `.rs` files → Rust.
   - `pyproject.toml` / `requirements.txt` / `.python-version` / `.py` files → Python.
2. **Confirm.** Propose the detected set to the user and let them adjust — add, drop, or reorder. Order in the page follows the order the user confirms (primary language first).
3. **Fall back to asking** when nothing is detectable (a greenfield spec written before code exists). Offer the supported set: TypeScript, JavaScript, Rust, Python.

Supported language templates live in [`references/`](references/): [`typescript.md`](references/typescript.md), [`javascript.md`](references/javascript.md), [`rust.md`](references/rust.md), [`python.md`](references/python.md). If the user names a language with no template, write its section from the Tiger Style core principles by analogy and note in Open questions that the section was hand-written without a template.

### Coding style

The pervasive coding style the guidelines enforce. **Tiger Style is the only supported option for now** — a defensive, limits-everywhere, assert-heavily discipline with the priority order *safety, performance, developer experience*. Its language-agnostic core lives in [`references/tiger-style.md`](references/tiger-style.md). Do not ask the user to choose a style while it is the only option; state that the page uses Tiger Style and proceed. (The parameter exists so additional styles can be added later without reshaping the skill.)

### Version control

The page carries a `## Version control` section describing the repo's VCS conventions. **Detect, then confirm**, the same way as languages.

1. **Detect.** Look for the VCS directory at the repo root:
   - `.jj/` → jujutsu (`jj`).
   - `.git/` → git.
   - **Both present → prefer jj.** A jj repo on a Git backend has both directories; jj is the working front end, so the guidelines describe the jj workflow. (Treating it as git would tell contributors to run `git commit` against a jj working copy — the mismatch the rules exist to prevent.)
   - Neither → ask the user, or omit the section if the spec is for a context with no version control yet (rare; note it in Open questions).
2. **Confirm.** State the detected VCS to the user. Offer **optional git guidelines** even in a jj repo: a team may want the git conventions documented for contributors who reach for the Git backend directly, or for a planned migration. Include them only if the user asks.

The version-control blocks live in [`references/tiger-style.md`](references/tiger-style.md): a shared core plus a **jujutsu** variant and a **git** variant. Use the variant matching the detected VCS; include both only when the user wants the git guidelines alongside jj.

## Workflow

### 1 — Locate the spec set and decide placement

Find the spec the page joins. Global development guidelines live at `docs/specs/development-guidelines.md` (scope `Repo-wide`). This is the default and the right home for almost all of the content — the discipline is cross-cutting.

A **per-app** development-guidelines page (`docs/<app>/specs/NN-development.md`) is warranted only when an app has genuine deltas from the global rules (a different test runner, an extra language, a stricter limit). When it exists, it opens with a **Read first** pointer to the global page and documents only the deltas — never restating global rules. Per [§Layered structure in spec-creator](../spec-creator/SKILL.md). Confirm placement with the user if a per-app set already exists.

### 2 — Resolve parameters

Detect and confirm the languages and the VCS (above). State that the page uses Tiger Style. Note the spec owner and today's date for the header.

### 3 — Assemble the page

Build `development-guidelines.md` from the references, in this order:

```
# Development Guidelines
**Status: … · Date: … · Owner: … · Scope: Repo-wide**

(opening paragraph: rules of the road; list the pillars)

## Toolchain                              ← rows from each language file + version control + style
## <Style> — the pervasive style          ← references/tiger-style.md core
## Defensive coding and assertions
   ### Where to validate                  ← tiger-style.md
   ### Assertions in <language>           ← one per language, from each language file
   ### Errors are data, not exceptions    ← tiger-style.md
   ### Make invalid states unrepresentable← tiger-style.md
## Limits and bounds                       ← tiger-style.md (meta-rule only; values live per-app)
## Version control                         ← tiger-style.md (shared core + jj or git variant; per the VCS parameter)
## <Language> conventions                  ← one section per language, from each language file
   ### Formatting and linting
   ### Code style
   ### Naming
   ### Testing
   ### Documentation
## Repository hygiene                      ← tiger-style.md, adapted to the repo's layout
## Guidelines for AI agents                ← tiger-style.md, plus any language-specific slips
## Definition of done                      ← tiger-style.md, plus per-language additions
## Assumptions and open questions          ← mandatory closing block
```

Adapt every template to the repo. The references are starting points, not boilerplate to paste:

- Drop rows and rules for tooling the repo does not use.
- Replace placeholder limit values with the repo's named constants where they exist; the meta-rule (every limit is a named constant) stays, concrete values move to per-app specs.
- Use the version-control variant matching the detected VCS (per the Version control parameter): jujutsu, git, or both when the user asked for the optional git guidelines alongside jj.
- Keep the page in spec voice: present tense for what exists, past tense in Decisions, question form in Open questions. No marketing words, no emoji, no exclamation points.

### 4 — Write the closing block

Every spec page ends with `## Assumptions and open questions` (Assumptions / Decisions / Open questions). This is where:

- **Decisions** record the load-bearing choices: why this style, why this test runner, why this limit gate, why pre-push vs pre-commit. Use the `*label.* **choice.** why` format.
- **Open questions** hold every gate or tool named in the discipline but not yet wired up (the divergences from §Core principle), plus any genuinely undecided rule.

### 5 — Cross-link

Mandatory, and easy to skip:

1. **Update `docs/README.md`** — add `docs/specs/development-guidelines.md` to the global-specs list (create the index if absent). A page the index does not reference is invisible.
2. **If per-app**, update `docs/<app>/README.md` to point at the global specs, then list the per-app set, and confirm the page's **Read first** pointer resolves.
3. **Verify cross-links** — the architecture-principles page and the overview commonly link to the guidelines; check those references resolve, and add a link from `00-overview.md`'s detail-pages table if one is missing.
4. **Run the spec-creator checklist** at [`../spec-creator/references/checklist.md`](../spec-creator/references/checklist.md) — the Voice, Closing block, and Cross-links sections apply directly.

## When invoked by spec-creator

When spec-creator reaches the development-guidelines page in its Phase 3 (Write), it delegates here. In that case the spec set, owner, and date are already established — skip step 1, resolve languages (step 2), and produce the page (steps 3–4). spec-creator owns the final cross-link pass (step 5) as part of its Phase 4.

## Reference files

- [`references/tiger-style.md`](references/tiger-style.md) — The language-agnostic Tiger Style core: the pervasive-style section, defensive-coding philosophy (where to validate, errors as data, make invalid states unrepresentable), limits and bounds, version control, repository hygiene, AI-agent emphases, and the definition-of-done skeleton. Read first; it supplies every section that is not language-specific.
- [`references/typescript.md`](references/typescript.md) — TypeScript: toolchain rows, assertions, conventions (formatting, code style, naming, testing, documentation), definition-of-done additions.
- [`references/javascript.md`](references/javascript.md) — JavaScript (no type system): the same sections adapted to runtime-checked discipline.
- [`references/rust.md`](references/rust.md) — Rust: the same sections.
- [`references/python.md`](references/python.md) — Python: the same sections.
