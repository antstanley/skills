# Change: Trim deferred SWE-bench Pro code to match the minimal canonical

**Status:** Merged · **Date:** 2026-05-27 · **Merged:** 2026-05-27 · **Owner:** Ant Stanley · **Target:** apps/benchmark

Removing SWE-bench Pro from the canonical spec trimmed the schema's `Suite.kind` and `Suite.oracleConvention` enums, but the implementation still carries the deferred values: `benchmark/harness/domain.py` lists `issue-fixing` / `swe-bench-pro` as valid, `benchmark/harness/scoring/resolution.py` attributes the resolution rule to SWE-bench Pro, and the domain tests build `Suite` / `TaskInstance` / `Campaign` fixtures around the `swe-bench-pro-public` slug — which the trimmed schema now rejects, leaving the test suite **red**. This change removes those references so the code and its tests match the minimal canonical. It is a code-only alignment with no canonical-page or schema delta; the [add-SWE-bench-Pro change spec](../2026-05-27-add_swe_bench_pro_suite.md) re-introduces all of them when the suite is added back.

---

## Motivation

The schema at `docs/benchmark/specs/canonical-types.schema.json` is the single validation authority — every domain record validates against it at construction (`benchmark/harness/domain.py:60`), and the domain tests assert that valid fixtures pass and invalid ones are rejected. When SWE-bench Pro was removed, `Suite.kind` lost `issue-fixing` and `Suite.oracleConvention` lost `swe-bench-pro`, so the fixtures that still use those values now raise `DomainValidationError`. Four tests fail (`test_round_trip_and_schema_valid[Suite]`, `test_unknown_field_rejected`, `test_slug_pattern_rejects_uppercase`, `test_unknown_suite_kind_rejected`). The minimal implementation cannot be green until the code stops referencing the deferred suite.

The fix is mechanical and self-contained: drop the two enum members from the mirror constants in `domain.py`, generalise one docstring in `resolution.py`, and re-point the test fixtures from the `swe-bench-pro-public` issue-fixing instance to the `greenfield-features` (or `local-fixture`) suite that the minimal canonical keeps. No production behaviour changes — the `container`/`local` backends, the driver, and the statistics never branched on `issue-fixing` — so this is purely removing now-unreachable vocabulary and stale test data.

---

## Affected spec pages

None. This is a code-only change. The canonical pages and `canonical-types.schema.json` were already trimmed when SWE-bench Pro was removed from the spec; this change brings the implementation and its tests into line with them, so there is no `Proposed changes` block and no `Type changes` fragment.

---

## Implementation notes

Precise edits. All references were located with `grep -rn "swe\|SWE\|issue-fix" benchmark` (excluding `__pycache__`).

```
1. benchmark/harness/domain.py
   - SUITE_KINDS: drop "issue-fixing" → ("greenfield", "local-fixture").
   - ORACLE_CONVENTIONS: drop "swe-bench-pro" → ("greenfield-hidden-tests", "local").
   (These constants mirror the schema enums; nothing branches on the removed values.)

2. benchmark/harness/scoring/resolution.py (module docstring, ~line 10)
   - "Resolution (SWE-bench Pro convention): a candidate resolves iff every failToPass
     test passes AND every passToPass test still holds." → drop the "(SWE-bench Pro
     convention)" attribution; state the rule plainly (matches 06-scoring-and-statistics.md,
     which now says "identical across every backend and oracle convention").

3. benchmark/tests/test_domain.py — re-point the shared fixtures off the issue-fixing
   instance to a suite the minimal canonical keeps:
   - Suite fixture (lines ~49-51): slug="greenfield-features", kind="greenfield",
     oracleConvention="greenfield-hidden-tests".
   - TaskInstance fixture (lines ~57-58) and its references (lines ~95, ~136, ~159):
     slug="greenfield__url_shortener", suite="greenfield-features" (greenfield has
     goldPatch=null; set dockerImage accordingly or use the local-fixture instance if a
     gold patch is needed by the test).
   - Campaign fixtures (lines ~85, ~404): suites=["greenfield-features"].
   - The test_unknown_suite_kind_rejected case should now assert that "issue-fixing"
     (a removed value) is rejected, rather than using it as a valid kind.
   - Membership assertions (lines ~375-376) already use "local-fixture"/"local" and stay.

4. Re-run: `uv run --project benchmark pytest benchmark/tests/test_domain.py -q` must be green.
```

This change is the inverse of the [add-SWE-bench-Pro change spec](../2026-05-27-add_swe_bench_pro_suite.md): when that suite is added back, it re-introduces `issue-fixing` / `swe-bench-pro` in both the schema and these same code constants and fixtures. The two change specs should not be in flight simultaneously.

---

## Merge plan

Code-only, so the "merge" is shipping the code rather than editing canonical pages.

1. Apply the edits in `Implementation notes`; confirm `benchmark/tests/test_domain.py` is green.
2. No canonical page or schema edit (they are already at the target state).
3. Flip this file's `**Status:**` to `Merged`, add `**Merged:** YYYY-MM-DD`, and move it to `docs/benchmark/specs/changes/merged/`.
4. Update `docs/README.md`: remove this file from the pending change-specs list.

---

## Assumptions and open questions

**Assumptions**

- No production code path branches on the `issue-fixing` kind or the `swe-bench-pro` oracle convention — they appear only as enum members and test data — so removing them changes no runtime behaviour. (Verified by grep: the only non-test references are the two `domain.py` constants and one `resolution.py` docstring.)

**Decisions**

- *Trim rather than re-broaden the schema.* **Code follows the minimal canonical.** The alternative — re-adding the enum values to the schema to make the tests pass — would re-introduce SWE-bench Pro into the canonical, which is exactly what the removal deferred. The code is brought down to the spec, not the spec back up to the code.
- *Documented as a change spec, not a silent edit.* **Paired with the add-back spec.** Recording the trim and its reversal as dated change specs keeps the deferral auditable; the add-back spec is the single place the SWE-bench Pro code returns.

**Open questions**

- *Fixture target — greenfield or local-fixture.* The shared `TaskInstance` fixture currently sets a `goldPatch`; greenfield instances have `goldPatch: null`. If a test relies on a non-null gold patch, the fixture should move to the `local-fixture` instance rather than `greenfield-features`. Which suite the shared fixture should default to is settled during implementation by what the existing assertions need.
