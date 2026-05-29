# Change: Tolerate markdown emphasis in discharged `VERDICT:` lines

**Status:** Merged · **Date:** 2026-05-29 · **Merged:** 2026-05-29 · **Owner:** Ant Stanley · **Target:** apps/benchmark

The gate-efficacy machinery reads each discharged done-certificate's `VERDICT:` line to turn a gate run into a typed `GateEvent` ([06-scoring-and-statistics.md](../../06-scoring-and-statistics.md) → §Gate-efficacy probes). A live A2 recursive run surfaced a false negative: the `validate-done-certificate` gate writes its verdict line as a MARKDOWN-BOLD label under a `## Verdict` heading — the literal line is `**VERDICT:** DONE`, not the bare `VERDICT: DONE` the unit fixtures used. The parser required a bare label (after the colon it expected only whitespace before the verdict word), so the closing bold `**` between the colon and `DONE` defeated the regex: `extract_gate_events` returned no events, A2 emitted zero `GateEvent`s, and the arm falsely looked ungated. This change commits the parser to reading the `VERDICT:` line tolerant of markdown emphasis, so live `spec-builder` certificates (which bold the label) register as gate events. The fix is small and surfaced by a real live run; no schema change, no new canonical page, no domain change.

---

## Motivation

`extract_gate_events` (`benchmark/harness/arms/a2_a3.py`) is the mechanism that makes the gate difference observable from captured artifacts: a gates-on (A2) capture must yield `>= 1` GateEvent and a gates-off (A3) capture none. It does this by scanning each discharged certificate body for a `VERDICT:` line and mapping the verdict word onto the closed `GateVerdict` enum.

The two parsing regexes required a BARE label — `\bVERDICT:\s*(DONE|…)` — where `\s*` after the colon admits only whitespace before the verdict token. The unit fixtures in `benchmark/tests/test_a2_a3_arms.py` used exactly that bare shape (`VERDICT: DONE`), so the unit tests passed.

But the LIVE gate does not write a bare label. A captured A2 recursive run produced done-certificates whose discharged verdict line is markdown-bold under a `## Verdict` heading:

```
## Verdict

**VERDICT:** DONE
```

The closing `**` sits between the colon and `DONE`. The regex's `\s*` cannot match `**`, so the line never matched, `extract_gate_events` returned `[]`, A2 emitted zero GateEvents, and the live `test_live_a2_emits_gate_events_and_a3_emits_none` failed on `assert len(a2_events) >= 1`. The bare-vs-bold gap is exactly why the unit tests stayed green while the live certificate did not register.

Markdown emphasis around a label is ordinary markdown: the gate may equally write `**VERDICT:**`, `*VERDICT:*`, `__VERDICT:__`, or bare `VERDICT:`, and emphasis markers may sit between the colon and the verdict word. The spec should commit the parser to reading the label tolerant of that emphasis, so the witness stays sound — a genuinely discharged certificate registers regardless of how its label is styled — without weakening the gates-off (A3) case, which still carries the authored `(blank …)` placeholder and yields no event.

---

## Affected spec pages

| Canonical page | Nature of change |
|---|---|
| [`06-scoring-and-statistics.md`](../../06-scoring-and-statistics.md) | §Gate-efficacy probes → *Live-probe verdict mapping*: note that the organic-path `VERDICT:` line read by `extract_gate_events` is parsed tolerant of markdown emphasis, so live `spec-builder` / `validate-done-certificate` certificates (which bold the label, `**VERDICT:** DONE`) register as gate events |

No new canonical page is added; the schema (`canonical-types.schema.json`) is unchanged — this change introduces no entity, field, or enum and refines no type. The closed `GateVerdict` enum and the `DONE → PASS` / `PARTIAL → PARTIAL` / `NOT_DONE → FAIL` / `UNVERIFIED → UNVERIFIED` mapping are untouched. It is a prose clarification of one already-described parsing step plus the matching parser fix.

---

## Proposed changes

The block below is the prose as it should read in the canonical page after merge. It appends one clarifying sentence to the *Live-probe verdict mapping* paragraph under [06-scoring-and-statistics.md](../../06-scoring-and-statistics.md) → §Gate-efficacy probes (the paragraph that already names `extract_gate_events` and `_REVIEW_VERDICT_MAP`). The canonical page itself is NOT edited here — only this proposed-changes block is authored; the orchestrator merges the prose at integration.

### `06-scoring-and-statistics.md` → §Gate-efficacy probes, *Live-probe verdict mapping* (append one sentence)

> On the organic path, `extract_gate_events` reads each discharged certificate's `VERDICT:` line tolerant of markdown emphasis around the label: the live `validate-done-certificate` / `semi-formal-review` gates write the label BOLD under a `## Verdict` heading (the literal captured line is `**VERDICT:** DONE`), and italic (`*VERDICT:*`) or underscore-bold (`__VERDICT:__`) shapes are equally valid markdown, so the parser absorbs the emphasis markers around the label and between the colon and the verdict token. A bare `VERDICT: DONE` and a bolded `**VERDICT:** DONE` therefore both register as the same gate event, while an undischarged A3 certificate — still carrying the authored `**Verdict:** (blank …)` placeholder — continues to yield no event.

---

## Type changes

None. This change adds no entity, field, or enum and refines no type; `canonical-types.schema.json` and `benchmark/harness/domain.py` are untouched. The closed `GateVerdict` enum (`PASS | FAIL | PARTIAL | UNVERIFIED`) and the verdict-to-enum maps are unchanged. It clarifies the prose of one §Gate-efficacy-probes paragraph to match the (now emphasis-tolerant) parser.

---

## Implementation notes

The fix is minimal and lives in `benchmark/harness/arms/a2_a3.py`:

- `_VALIDATE_VERDICT_RE` and `_REVIEW_VERDICT_RE` are made tolerant of optional markdown emphasis around the `VERDICT:` label and between the colon and the verdict token. The previous bare form `\bVERDICT:\s*(…)\b` becomes `VERDICT[*_]*:\s*[*_]*\s*(…)\b` (`re.IGNORECASE` kept): the `[*_]*` runs absorb the closing/opening emphasis markers (`**`, `*`, `__`) on the label and after the colon. This matches all of `VERDICT: DONE`, `**VERDICT:** DONE`, `*VERDICT:* PARTIAL`, `**VERDICT:**  NOT_DONE`, and `__VERDICT:__ DONE`.
- The `_BLANK_VERDICT_MARKER` skip is unchanged and still fires first: an undischarged (A3) certificate carrying `**Verdict:** (blank …)` continues to yield no event, and the `(blank …)` text is not a verdict token so the broadened regex does not misread it.
- The `_VALIDATE_VERDICT_MAP` / `_REVIEW_VERDICT_MAP` mappings are unchanged. The double-count guard is unchanged: a validate certificate carrying both a validate verdict and (elsewhere) a review verdict still yields up to two events by design; a single bold verdict line yields exactly one.
- A regression test in `benchmark/tests/test_a2_a3_arms.py` exercises a captured certificate whose verdict line is the real live shape (`## Verdict` + `**VERDICT:** DONE`) and asserts exactly one validate GateEvent mapped to `PASS`, plus the bare form still works and `*VERDICT:* PARTIAL` maps to PARTIAL.

This false negative was surfaced by a real `BENCHMARK_RUN_A2_A3_LIVE=1` run: the live A2 discharged its certificates with a bolded label, the bare-only regex missed it, and `assert len(a2_events) >= 1` failed even though the gates had genuinely run.

---

## Merge plan

1. Apply the `Proposed changes` block to `06-scoring-and-statistics.md` → §Gate-efficacy probes (append the clarifying sentence to the *Live-probe verdict mapping* paragraph); bump that page's `**Date:**` to the merge date if it carries one.
2. No `Type changes` to fold — `canonical-types.schema.json` is unchanged.
3. No new canonical page; nothing to index beyond existing entries.
4. Flip this file's `**Status:**` to `Merged`, add `**Merged:** YYYY-MM-DD`, and move it to `docs/benchmark/specs/changes/merged/`.
5. Add a one-line entry to the Merged list in `docs/README.md`.

---

## Assumptions and open questions

**Assumptions**

- The only styling the live gate applies to the `VERDICT:` label is markdown emphasis (`*` / `_` runs) around the label and between the colon and the verdict token; the verdict TOKEN itself (`DONE`, `CORRECT`, …) is always written bare. The `[*_]*` runs cover the observed bold shape and the equally-valid italic / underscore-bold shapes; a future gate that interposed other characters would need a further widening, but no such shape has been observed.
- The captured certificate body preserves the literal `**VERDICT:** DONE` line (the merged-certificate capture path is byte-faithful), so reading the bytes is sufficient; no markdown rendering/normalisation happens before the parser sees the line.

**Decisions**

- *Tolerate emphasis, do not normalise.* **The regex absorbs the emphasis markers in place rather than stripping markdown from the body first.** A targeted widening of the two label regexes is the smallest sound change and keeps the parser a single pass over the captured bytes.
- *Refine, do not relax the A3 case.* **The `_BLANK_VERDICT_MARKER` skip and the verdict-to-enum maps are unchanged.** An undischarged A3 certificate still yields no event; the change only stops a genuinely discharged certificate from being missed because its label is bold.

**Open questions**

- *Live re-run.* Should the live A2/A3 container witness be re-run under the fix to confirm the bolded live certificates now register `>= 1` GateEvent end to end, before this change spec is marked `Merged`? The build proves it against a captured-shape fixture; only a live run proves the end-to-end path on freshly-generated certificates.
