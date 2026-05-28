# Change: Refine the run-image content-integrity check to hidden-only lines

**Status:** Merged · **Date:** 2026-05-28 · **Merged:** 2026-05-28 · **Owner:** Ant Stanley · **Target:** apps/benchmark

The live runtime-verification self-test ([05-harness-architecture.md](../../05-harness-architecture.md) → §Runtime verification) asserts the provisioned RUN image carries no hidden-test content. The first real `BENCHMARK_RUN_CONTAINER_LIVE=1` run surfaced a false positive in the *content* half of that assertion: it flagged the clean run image as carrying hidden-test content because the content fingerprints included boilerplate the hidden suite shares with the run-visible `base/` skeleton — `from __future__ import annotations` and the public-API `import` lines — which cleared the bare length filter. The path-leak half (no `hidden/` path in the run image) was correct, so the integrity rule itself held; only the content heuristic over-fired. This change refines the spec's commitment so the content check compares against **hidden-only** lines (the hidden suite's substantive lines minus any also present in the run-visible base skeleton), keeping the witness sound without weakening it. The fix is already implemented and committed; this change spec catches the prose up to it. No schema change, no new canonical page, no plan.

---

## Motivation

The content-integrity check exists to catch a genuine leak: a hidden acceptance-test body line appearing inside the RUN image, which would let a run arm overfit the very tests it is later scored on. The check works by reading the hidden suite's test bodies on the scoring side and asserting none of those lines appear in the provisioned RUN image.

The original heuristic kept any hidden-test line at least `MIN_FINGERPRINT_LENGTH` (24) characters long as a "distinctive" fingerprint. But a hidden test file and the run-visible `base/` skeleton legitimately share generic boilerplate that easily clears 24 characters — `from __future__ import annotations` (33 chars) and the public-API `import` lines. Those lines are run-visible *by design* (they live in `base/`, which the run image copies), so finding them in the RUN image is expected, not a leak. The first live `BENCHMARK_RUN_CONTAINER_LIVE=1` run on the greenfield `text_toolkit` instance hit exactly this: the RUN image was clean, but the content check raised a `ContainerCheckError` on a shared boilerplate line.

The length filter alone cannot distinguish leaked hidden content from shared boilerplate. The discriminator is *provenance*: a line that also appears in the run-visible base skeleton is legitimately run-visible and is not evidence of a leak; a line that appears **only** in the hidden suite is. The spec should commit to that hidden-only comparison so the witness stays sound — a real hidden-only line in the run image is still caught — while the shared-boilerplate false positive is eliminated.

---

## Affected spec pages

| Canonical page | Nature of change |
|---|---|
| [`05-harness-architecture.md`](../../05-harness-architecture.md) | §Runtime verification: refine the *integrity rule, observed not assumed* bullet so the content check is stated against hidden-only lines (hidden suite substantive lines minus base-skeleton lines), not any sufficiently long hidden-test line |

No new canonical page is added; the schema (`canonical-types.schema.json`) is unchanged — this change introduces no entity, field, or enum, and refines no type. It is a prose refinement of one already-merged bullet.

---

## Proposed changes

The block below is the prose as it should read in the canonical page after merge. It replaces the current *integrity rule, observed not assumed* bullet under [05-harness-architecture.md](../../05-harness-architecture.md) → §Runtime verification.

### `05-harness-architecture.md` → §Runtime verification (Modify the *integrity rule* bullet)

> - **The integrity rule, observed not assumed.** The run image carries no file from the instance's `hidden/` tree and no *hidden-only* test content — checked by inspecting the provisioned image, not by trusting the build. The content half compares the image against the hidden suite's substantive (sufficiently long) `failToPass` / `passToPass` body lines **minus** any line also present in the run-visible `base/` skeleton: boilerplate the hidden suite shares with `base/` (the `from __future__ import annotations` line, public-API `import` lines) is legitimately run-visible and is not a leak, while a genuinely hidden-only line appearing in the run image is still caught.

---

## Type changes

None. This change adds no entity, field, or enum and refines no type; `canonical-types.schema.json` and `benchmark/harness/domain.py` are untouched. It refines the prose of one already-merged §Runtime-verification bullet to match the committed content-check logic.

---

## Implementation notes

The fix is already implemented and committed; these notes ground the merged prose against the code, they are not work for an implementing agent.

The content-integrity check lives in `benchmark/harness/run_container_check.py`:

- `hidden_test_fingerprints(instance)` now reads the hidden suite's substantive lines (those at least `MIN_FINGERPRINT_LENGTH` = 24 long) and **subtracts** the run-visible base skeleton's substantive lines before returning the fingerprints — so a hidden line also present in `base/` is not counted as a leak.
- `_substantive_lines(root)` (new helper) collects the stripped lines at least `MIN_FINGERPRINT_LENGTH` long across the `*.py` files under a tree; it is applied to the base skeleton at `instance.repo` / `RUN_BASE_SUBDIR` (new constant, `"base"`) and the result subtracted from the hidden fingerprints.
- `assert_run_image_clean` is unchanged in shape: the path-leak half (`_is_hidden_path`) still rejects any `hidden/` path, and the content half still scans the image for the remaining (now hidden-only) fingerprints.

This false positive was surfaced by a real `BENCHMARK_RUN_CONTAINER_LIVE=1` run (the path-leak half passed; only the content heuristic misfired on shared boilerplate). On the greenfield `text_toolkit` instance the base subtraction drops the fingerprint count from 64 to 59 — the 5 shared boilerplate lines (`from __future__ import annotations` plus the public-API `import` lines) — while keeping the distinctive `assert …` body lines.

---

## Merge plan

1. Apply the `Proposed changes` block to `05-harness-architecture.md` → §Runtime verification (replace the current *integrity rule, observed not assumed* bullet); bump that page's `**Date:**` to the merge date if it carries one.
2. No `Type changes` to fold — `canonical-types.schema.json` is unchanged.
3. No new canonical page; nothing to index beyond existing entries.
4. Flip this file's `**Status:**` to `Merged`, add `**Merged:** YYYY-MM-DD`, and move it to `docs/benchmark/specs/changes/merged/`.
5. Add a one-line entry to the Merged list in `docs/README.md`.

---

## Assumptions and open questions

**Assumptions**

- The run-visible `base/` skeleton is the only legitimate source of run-side content shared with the hidden suite; subtracting its substantive lines is sufficient to eliminate the boilerplate false positives without masking a real leak. Any hidden line not also in `base/` is treated as hidden-only and still flagged.
- The greenfield `text_toolkit` instance is representative for the count check (64 → 59); the subtraction is keyed off `instance.repo` / `base`, so it generalises to any instance carrying a base skeleton, and degrades to a no-op (empty subtraction) when no `base/` tree exists.

**Decisions**

- *Provenance, not length, is the discriminator.* **A line is a leak only if it is hidden-only.** The length filter alone cannot separate leaked hidden content from boilerplate shared with `base/`; subtracting the base skeleton's substantive lines makes the content check sound while keeping it observed-at-runtime.
- *Refine, do not relax.* **The path-leak half is unchanged and the content half still fires on hidden-only lines.** The change removes a false positive; it does not weaken the integrity rule.

**Open questions**

- *Non-`*.py` base content.* `_substantive_lines` scans only `*.py` files under `base/`; if a future base skeleton shared substantive non-Python content with the hidden suite, that boilerplate would not be subtracted. Out of scope while the suites are Python-only.
