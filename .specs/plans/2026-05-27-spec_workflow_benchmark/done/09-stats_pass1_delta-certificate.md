# Done Certificate — Task 09: Stats — Pass@1 and the A1−A0 delta

**Task:** [09-stats_pass1_delta.md](09-stats_pass1_delta.md) · **Plan:** [plan.md](../plan.md)
**State:** Validated 2026-05-27

> This certificate is a verification protocol for Task 09. A validating agent discharges it:
> for each obligation, collect the named evidence, run the named checks, set the Status, then
> derive the Conclusion by the rubric below. Do not mark an obligation SATISFIED without its
> evidence; do not record DONE with any non-SATISFIED obligation.

## Definition

DONE(Task 09) ≡ every obligation O1…O4 below holds, each backed by the evidence the obligation
names — not by assertion.

## Premises

- **P1 — Goal.** The A0-vs-A1 ablation table — per-arm %Resolved with binomial CIs and Pass@k, and the A1−A0 paired McNemar delta.
- **P2 — Obligations.** Done iff O1…O4 all hold; O4 is the Reviewable item.
- **P3 — Invariants.** Consumes Task 07/08 `ScoreReport`s; must not modify the score reports, only aggregate them.

## Obligations

- **O1 — The table reports A0 and A1 metrics with CIs, Pass@k, regression rate, and the McNemar delta.**
  - *Claim:* per-arm %Resolved (Pass@1) with 95% binomial CIs, Pass@k, regression rate, and the A1−A0 paired McNemar delta are all rendered on the seed instances.
  - *Evidence to collect:* run the stats over the seed campaign; read the table — expect all named columns and the delta row present.
  - *Checks:* resolve the McNemar computation to operate on *paired* instances (discordant pairs), not on independent proportions; confirm the binomial CI uses the trial count `n`.
  - *Status:* SATISFIED — Rendered the ablation table over a seed-like campaign (3 instances x 2 reps/arm). All named columns present: per-arm Pass@1 with 95% CI (`A0 50.0% [18.8%, 81.2%]`, `A1 83.3% [43.6%, 97.0%]`), Pass@k (66.7% / 100.0%), regression rate with CI (16.7% / 0.0%), n trials, plus the delta row (`Δ%Resolved = +33.3 pp; McNemar χ² = 0.000 (cc), p = 1.0000 (exact binomial); discordant b=0, c=1`). Checks: `mcnemar_delta` (`outcome.py:306–310`) pairs on `shared = set(baseline) & set(treatment)` and builds discordant counts b/c — paired, not independent proportions. `wilson_interval` (`outcome.py:139–144`) uses `n = float(total)` (the trial count) throughout. Renderer at `outcome.py:408–443` emits all columns and the A1−A0 delta row.

- **O2 — The statistics are verified against synthetic inputs with known answers.**
  - *Claim:* CI, Pass@k, and McNemar return the expected values on synthetic score reports with hand-computed answers.
  - *Evidence to collect:* run the synthetic-input tests → expect each statistic matches its hand-computed value.
  - *Status:* SATISFIED — `benchmark/tests/test_stats.py` (18 tests) ran green within `pytest` (127 passed, 1 skipped). Each statistic checked against a hand-computed answer: Wilson at 0/10, 5/10, 10/10 to textbook values (`[0, 0.27753]`, `[0.23659, 0.76341]`, `[0.72247, 1.0]`); Pass@1 vs Pass@k where they differ (1/3 vs 1.0); McNemar textbook b=8, c=2 → χ²=2.5 (continuity-corrected) and exact two-sided p=0.109375 = 2·56/1024; the b+c=0 edge → stat 0, p 1.0; only-shared-instances pairing; regression rate and the failed-trials-excluded rule. These known answers were independently recomputed and confirmed at gate 1.

- **O3 — Meets the repo definition of done.**
  - *Claim:* tests pass, lint and format clean, deps locked, limits named (per plan.md baseline).
  - *Evidence to collect:* run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` — expect all clean.
  - *Status:* SATISFIED — `bash scripts/check.sh` (exit 0): `uv sync` clean (33 packages, no resolution change); `ruff format --check` → 68 files already formatted; `ruff check` → All checks passed; `pyright` → 0 errors, 0 warnings; `pytest` → 127 passed, 1 skipped (the documented opt-in `BENCHMARK_RUN_A1_LIVE` test). `uv sync --frozen` clean and `jj diff --name-only` shows no `pyproject.toml`/lockfile touched — NO new deps; stdlib `math` only. Limits named as module constants (`CONFIDENCE_LEVEL`, `WILSON_Z_95`, `MCNEMAR_EXACT_MAX_DISCORDANT`, `_MCNEMAR_NULL_P`) in `outcome.py:29–55`.

- **O4 — Reviewable: read the A0-vs-A1 table; confirm delta and intervals against a re-run. (M2 capstone.)**
  - *Claim:* a reviewer reads the A0-vs-A1 table and confirms the delta and intervals against a re-run within their stated bounds.
  - *Evidence to collect:* render the table; re-run the campaign and confirm the second table's values fall within the first's intervals.
  - *Status:* SATISFIED — Exercised: rendered the A0-vs-A1 table, then re-ran `ablation_table` on a freshly-built identical campaign. Both renders are byte-identical (A0 Pass@1 50.0% [18.8%, 81.2%], A1 83.3% [43.6%, 97.0%]; Δ = +33.3 pp; McNemar p = 1.0000 exact). The re-run's per-arm point estimates and the delta all fall within the first table's intervals (asserted: each `low ≤ point ≤ high`; `delta`/`p_value` equal). The computation is deterministic over the same score reports, so a reviewer confirms the delta and intervals against a re-run within their stated bounds.

## Regression check

No existing callers — stats is a new leaf consuming score reports. Confirm Task 07/08 score reports load into the stats layer unchanged : PRESERVED — `jj diff --stat` touches only `stats/__init__.py` (extended exports), the new `stats/outcome.py`, and the new `tests/test_stats.py` (846 insertions, 1 deletion). The stats read score reports through `run.scored_results` / `run.results` (read-only comprehensions in `outcome.py:153–163, 219–221`) and never mutate a `ScoreReport`; the synthetic tests build from the REAL driver types (`CampaignRun`, `TrialResult`, `Trial`, `ScoreReport`), so Task 07/08 reports load unchanged. No domain/driver code modified.

## Residue

- Cost-matched %Resolved, conformance, and gate metrics are added to the report in Tasks 15/13/14 and assembled in Task 16; this task is the outcome columns and the A1−A0 delta only.

## Conclusion

<!-- Validator derives this from the obligation statuses and the regression check, per the rubric. -->
VERDICT: DONE
CONFIDENCE: high
SUMMARY: O1–O4 all SATISFIED with collected evidence — the rendered A0-vs-A1 table carries Pass@1+CI, Pass@k, regression rate, and the paired McNemar A1−A0 delta; synthetic known-answer tests pass; check.sh is fully clean with no new deps; and a re-run reproduces the delta and intervals within bounds — and the score-report consumption is PRESERVED (stats is a read-only new leaf), so by the rubric the task is DONE.
