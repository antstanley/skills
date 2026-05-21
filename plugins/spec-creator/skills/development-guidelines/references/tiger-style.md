# Tiger Style — core (language-agnostic)

The sections below are the parts of a development-guidelines page that do not depend on the language. Drop them into the page in the order shown in the SKILL workflow, adapting each to the repo. They are written in spec voice (present tense, no marketing words); keep them that way.

Tiger Style is a defensive coding discipline. Its design priorities are **safety, performance, developer experience — in that order**. When the three pull in different directions, safety wins. The whole style follows from one habit: assume anything you did not produce is wrong, and anything you did not assert can be violated.

---

## `<Style>` — the pervasive style

> Heading on the page: `## Tiger Style — the pervasive style`

This project adopts **Tiger Style** as its pervasive coding style. This is not a recommendation; it is the default. Deviations require a written reason in the change description.

The short form: **be defensive and validate everything**. Assume any input you did not produce is wrong. Assume any invariant you did not assert can be violated. Make every limit explicit, every error handled, every assumption checked.

The design priorities — **safety, performance, developer experience, in that order** — apply throughout. When they conflict, safety wins.

Load-bearing principles:

- **Zero technical debt.** Do it right the first time. The "second time" often does not arrive; shipping a sound foundation is the only sustainable rate of progress.
- **Simple, explicit control flow.** No recursion (use iteration with an explicit bound). No clever combinators that hide branches. Linear flow over chains that hide a non-trivial control structure.
- **Limits on everything.** Every loop, queue, retry, cache, and payload size has an explicit, declared upper bound. An unbounded loop is bounded by an assertion on an invariant in its body.
- **Assertions are first-class code.** They detect programmer errors. The only correct response to a violated assertion is to crash. Aim for an average of at least two assertions per function — preconditions, postconditions, invariants.
- **Always say *why*.** Comments and commit descriptions explain the rationale, not the action. The action is in the code.

---

## Defensive coding and assertions

> Heading on the page: `## Defensive coding and assertions`

### Where to validate

Validate at every boundary where data crosses from a place you do not control into one you do.

| Boundary | What to validate | How |
|---|---|---|
| External request → handler | Body shape, sizes, IDs, enums | Schema validation against `canonical-types.schema.json` (or its derived types) before the handler sees the data |
| Adapter → core | Domain invariants | Assert preconditions at the top of every core function |
| Core → adapter | Adapter contract | Assert the shape of what the adapter returns |
| Disk / blob read | Round-trip integrity | Re-validate on read, even data you wrote; pair the check with the write site |
| Wire decode | Frame discriminant + payload shape | Reject unknown frames; do not best-effort parse |
| Third-party API response | Status, content type, body shape | Treat third parties as adversarial; never deserialize and trust the result |

> The per-language `### Assertions in <language>` subsections (one per selected language) slot in here, between "Where to validate" and "Errors are data".

### Errors are data, not exceptions

- Every error is a value with a typed reason. The boundary layer translates errors into stable codes that survive client upgrades.
- **Every error is handled or explicitly propagated.** Swallowing an error is a bug.
- **Retry policies are explicit and bounded** — max attempts, backoff schedule, jitter.
- **Never log a secret.** Errors that carry data scrub anything that could be a credential.

### Make invalid states unrepresentable

- Use the type system. Tagged ID types (`Id<Tag>` newtypes, branded strings) catch wrong-id-type bugs before they run. The same pattern fits units — `Cents`, `Seconds`, `Bytes`.
- Model state with enums / tagged unions, not free strings; match exhaustively with no fallthrough.
- Non-empty collection types for things that must have at least one element. Pre-validated string types (`Email`, `Url`) for any string with structure.

---

## Limits and bounds

> Heading on the page: `## Limits and bounds`

Every limit is **declared as a named constant**, named with its units, and referenced everywhere it applies. No magic numbers.

The *existence* of a limit is non-negotiable; concrete values are an app concern and live in the per-app specs, not here. Each limit names the domain it bounds — request body size, header size, frame payload, queue depth, retry count, per-user concurrency, token TTL, collection cardinality.

Reaching a limit is an **observable event**: log it structured, increment a counter, and where appropriate emit a warning event. Reaching a hard limit either rejects the input or backpressures the producer; it never silently drops.

---

## Version control

> Heading on the page: `## Version control`. Match this block to the repo's actual VCS — detect `.jj/` (jujutsu) vs `.git/` (git) and keep only the relevant rules.

- **Commits are small and well-described.** One coherent change per commit. Squash noise before pushing.
- **Empty commit descriptions are not accepted.** Describe the *why* before pushing.
- **Conventional Commits** for the subject line: `type(scope): subject`, types from the standard set (`feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `build`, `ci`, `perf`, `style`). Enforced in the pre-push hook and re-run in CI.
- **Branch model.** The integration branch (`main`) stays releasable. Feature work happens on named branches; pull requests target the integration branch.
- **Do not rewrite published history** unless the pull request is yours and unmerged. If a force-push is required, call it out.
- **Destructive operations need explicit confirmation** — history rewrites, branch deletion, hard resets, force-fetches — even when they look like the cleanest path.

---

## Repository hygiene

> Heading on the page: `## Repository hygiene`. Adapt paths to the repo's actual layout.

- **`docs/`** is the canonical home for specs and decisions.
- **Local, untracked operator data** lives in a gitignored directory; never commit environment-specific config or secrets.
- **The pre-push hook** runs format-check, lint, and the fast test tier. CI re-runs the same plus the slow tier.
- **Generated code is checked in** and grep-able; a CI job regenerates and fails the build if the checked-in output drifts.

---

## Guidelines for AI agents

> Heading on the page: `## Guidelines for AI agents`. These are not different rules — they are emphasis on the places agents tend to slip. Add language-specific slips from the per-language files.

1. **The pervasive style applies to you too.** Defensive validation and explicit limits are not optional, even on a small change.
2. **Add assertions as you go.** Every function you touch leaves with at least two meaningful assertions. Asserting a constant truth does not count.
3. **No silent error swallowing.** Every error is handled. Every match on a tagged union is exhaustive.
4. **Stay inside the architecture.** Adding I/O directly to a core module is the most common slip — define a port, implement an adapter, call into it.
5. **Do not add backwards-compat shims.** If a type changes, change every caller. There is no published API to preserve.
6. **Do not invent fields** not in the canonical types document. Update the schema and regenerate first.
7. **Tests run before claiming complete.** "Compiles" is not "works". Run the tests and report the actual output.
8. **Test positive and negative space together.** A new feature ships with tests for what it accepts *and* what it rejects.
9. **Limits are explicit.** A new loop, queue, retry, cache, or buffer ships with a named constant for its bound in the same change.
10. **Prefer small, frequent commits** over rolling up a huge change.
11. **No comments that paraphrase the code.** Comments explain *why*, in full sentences.
12. **Do not run destructive version-control operations without explicit confirmation.**
13. **Do not skip pre-commit / pre-push hooks.** If a hook fails, fix the underlying issue.

---

## Definition of done

> Heading on the page: `## Definition of done`. Append per-language items (test-runner names, format/lint commands) from the language files.

A change is done when:

- The behaviour is exercised by a test (unit, integration, or end-to-end as appropriate).
- The change includes **negative-space tests** for every new validation path.
- Every new or touched function has at least two meaningful assertions.
- Every new bound is a named constant in the relevant module.
- Format, lint, and the fast test tier all pass locally.
- If domain types changed, `canonical-types.schema.json` is updated and any generated types are regenerated.
- The commit description states the *why*.
- The change description lists what changed at the architecture level.
