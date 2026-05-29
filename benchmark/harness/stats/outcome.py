"""Per-arm outcome statistics and the A1−A0 ablation table.

Implements ``docs/benchmark/specs/06-scoring-and-statistics.md`` (§Repetition
and Pass@k, §Confidence intervals and pairwise tests, §Reporting) and
``docs/benchmark/specs/04-metrics.md`` (§Bucket 1 — Outcome) over the
``CampaignRun`` the driver emits. Pure stdlib ``math`` — no scipy/numpy.

Every statistical formula is named, cited to a textbook source in a comment, and
verified against a known-answer value in ``benchmark/tests/test_stats.py``.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from benchmark.harness.domain import ScoreReport
    from benchmark.harness.driver import CampaignRun

# --- named limits / constants ----------------------------------------------

#: The reported confidence level for every binomial interval (``06`` §Confidence
#: intervals and pairwise tests — "95% binomial confidence interval").
CONFIDENCE_LEVEL = 0.95

#: Two-sided standard-normal critical value for ``CONFIDENCE_LEVEL`` (z_{0.975}).
#: Used by the Wilson score interval. 1.959963985 ≈ Φ⁻¹(0.975).
WILSON_Z_95 = 1.959963985

#: The two ablation arms this table compares; the delta row is A1 − A0
#: (``06`` §Reporting; ``02-arms.md`` defines the pairs — this task ships A1−A0).
BASELINE_ARM = "A0"
TREATMENT_ARM = "A1"

#: Small-sample threshold for McNemar's test (``06`` §Confidence intervals and
#: pairwise tests). When the discordant count ``b + c`` is at or below this, the
#: chi-square approximation is unreliable, so we use the EXACT binomial two-sided
#: test on (b, c) — the correct small-sample McNemar (Agresti,
#: *Categorical Data Analysis*, 3rd ed., §10.1.4; for tiny seeds this is what
#: applies). Above it, the chi-square with continuity correction is used.
MCNEMAR_EXACT_MAX_DISCORDANT = 25

#: The fair-coin success probability under McNemar's null (a discordant pair is
#: equally likely to favour either arm).
_MCNEMAR_NULL_P = 0.5

#: Continuity-corrected McNemar chi-square has 1 degree of freedom; its p-value
#: is the survival of a chi-square_1 = the survival of a standard normal at
#: sqrt(stat), i.e. ``erfc(sqrt(stat / 2))`` (chi-square_1 = Z²).
_CHI2_1DF_HALF = 2.0


# --- result records ---------------------------------------------------------


@dataclass(frozen=True)
class ConfidenceInterval:
    """A point estimate with its closed [low, high] 95% interval."""

    point: float
    low: float
    high: float
    level: float = CONFIDENCE_LEVEL


@dataclass(frozen=True)
class McNemarResult:
    """The McNemar paired-test outcome for an arm pair.

    ``b`` = instances the baseline (A0) resolved but the treatment (A1) did not;
    ``c`` = instances A1 resolved but A0 did not (the discordant pairs). ``delta``
    is the treatment-minus-baseline %Resolved over the shared instances. ``stat``
    is the McNemar statistic (chi-square with continuity correction) and ``exact``
    flags whether the p-value came from the exact small-sample binomial test.
    """

    b: int
    c: int
    n_pairs: int
    delta: float
    statistic: float
    p_value: float
    exact: bool


@dataclass(frozen=True)
class ArmOutcome:
    """Bucket-1 outcome statistics for a single arm."""

    arm: str
    n_trials: int
    n_instances: int
    pass_at_1: ConfidenceInterval
    pass_at_k: float
    k: int
    regression_rate: ConfidenceInterval


@dataclass(frozen=True)
class AblationTable:
    """The A0-vs-A1 ablation table: per-arm rows plus the A1−A0 delta row."""

    arms: tuple[ArmOutcome, ...]
    delta: McNemarResult | None


# --- Wilson score interval ---------------------------------------------------


def wilson_interval(
    successes: int, total: int, z: float = WILSON_Z_95
) -> ConfidenceInterval:
    """The Wilson score interval for a binomial proportion.

    Formula (Wilson 1927; see Brown, Cai & DasGupta 2001, "Interval Estimation
    for a Binomial Proportion", *Statistical Science* 16(2)):

        center = (p̂ + z²/2n) / (1 + z²/n)
        half   = (z / (1 + z²/n)) · sqrt( p̂(1−p̂)/n + z²/4n² )
        [low, high] = center ∓ half

    with p̂ = successes / total. Chosen over the normal approximation because it
    stays inside [0, 1] and behaves at small ``n`` and near 0/1 — our tiny seed
    (``06`` §Confidence intervals and pairwise tests). For ``total == 0`` the
    proportion is undefined; we report the whole [0, 1] interval with point 0.0.
    """
    if successes < 0 or total < 0 or successes > total:
        raise ValueError(
            f"invalid binomial counts: successes={successes}, total={total}"
        )
    if total == 0:
        return ConfidenceInterval(point=0.0, low=0.0, high=1.0)

    n = float(total)
    p_hat = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p_hat + z2 / (2.0 * n)) / denom
    margin = (z / denom) * math.sqrt(p_hat * (1.0 - p_hat) / n + z2 / (4.0 * n * n))
    low = max(0.0, center - margin)
    high = min(1.0, center + margin)
    return ConfidenceInterval(point=p_hat, low=low, high=high)


# --- per-arm outcome metrics -------------------------------------------------


def _scored_reports_for_arm(run: CampaignRun, arm: str) -> list[ScoreReport]:
    """Every ScoreReport from this arm's scored trials (failed excluded).

    ``CampaignRun.scored_results`` already drops ``failed`` (infra) trials, so
    this is the failed-trials-excluded rule of ``06`` §Repetition and Pass@k.
    """
    return [
        result.report
        for result in run.scored_results
        if result.report is not None and result.trial.arm == arm
    ]


def pass_at_1(reports: Sequence[ScoreReport]) -> ConfidenceInterval:
    """Pass@1: mean ``resolved`` over single scored trials, with a Wilson CI.

    ``06`` §Repetition and Pass@k / ``04`` §Bucket 1 — the headline outcome.
    Each scored trial is one Bernoulli draw; the success count is the number of
    ``resolved`` reports.
    """
    successes = sum(1 for r in reports if r.resolved)
    return wilson_interval(successes, len(reports))


def group_resolved_by_instance(
    reports: Iterable[ScoreReport],
    trial_instance: dict[str, str],
) -> dict[str, list[bool]]:
    """Group each scored trial's ``resolved`` flag by its TaskInstance slug.

    ``trial_instance`` maps a ScoreReport's ``trial`` id to its instance slug
    (ScoreReport itself carries no instance, only the trial id). The grouping is
    the basis of Pass@k (``06`` §Repetition and Pass@k): the ``k`` trials of an
    instance are the values of one key.
    """
    grouped: dict[str, list[bool]] = defaultdict(list)
    for report in reports:
        instance = trial_instance.get(report.trial)
        if instance is None:
            raise KeyError(f"no instance mapping for trial {report.trial!r}")
        grouped[instance].append(report.resolved)
    return dict(grouped)


def pass_at_k(resolved_by_instance: dict[str, list[bool]]) -> float:
    """Pass@k: fraction of instances resolved by at least one of their trials.

    ``06`` §Repetition and Pass@k / ``04`` §Bucket 1 — "fraction of instances
    resolved by at least one of ``k`` trials". An instance counts once if ANY of
    its scored trials resolved. Returns 0.0 when there are no instances.
    """
    if not resolved_by_instance:
        return 0.0
    hit = sum(1 for trials in resolved_by_instance.values() if any(trials))
    return hit / len(resolved_by_instance)


def regression_rate(reports: Sequence[ScoreReport]) -> ConfidenceInterval:
    """Regression rate: fraction of scored trials with ``regressed`` true.

    ``04`` §Bucket 1 — reported with a Wilson CI like the other proportions.
    """
    regressed = sum(1 for r in reports if r.regressed)
    return wilson_interval(regressed, len(reports))


def _trial_instance_map(run: CampaignRun) -> dict[str, str]:
    """Map every trial id in the run to its TaskInstance slug."""
    return {r.trial.id: r.trial.taskInstance for r in run.results}


def arm_outcome(run: CampaignRun, arm: str) -> ArmOutcome:
    """Compute the bucket-1 outcome statistics for one arm over a CampaignRun."""
    reports = _scored_reports_for_arm(run, arm)
    instance_map = _trial_instance_map(run)
    by_instance = group_resolved_by_instance(reports, instance_map)
    k = run.campaign.trialsPerInstance
    return ArmOutcome(
        arm=arm,
        n_trials=len(reports),
        n_instances=len(by_instance),
        pass_at_1=pass_at_1(reports),
        pass_at_k=pass_at_k(by_instance),
        k=k,
        regression_rate=regression_rate(reports),
    )


# --- McNemar paired delta ----------------------------------------------------


def _instance_resolved_any(resolved_trials: list[bool]) -> bool:
    """Reduce an instance's trials to a single resolved bool: resolved if ANY.

    PAIRING RULE (documented per the task): for the paired McNemar comparison we
    reduce each (arm, instance) to "did this arm EVER resolve the instance" — the
    Pass@k-style ``any`` over its trials. We pick ``any`` over majority because
    it matches the Pass@k notion of capability the table already reports, is
    well-defined for any trial count (including ``k == 1``, where it equals
    Pass@1 per instance), and avoids ties that a majority rule must break.
    """
    return any(resolved_trials)


def _exact_binomial_two_sided(b: int, c: int) -> float:
    """Two-sided exact binomial p-value for McNemar at small ``b + c``.

    Under McNemar's null a discordant pair favours either arm with p = 0.5, so
    the smaller count follows Binomial(n = b + c, 0.5). The exact two-sided
    p-value is ``min(1, 2 · P(X ≤ min(b, c)))`` (Agresti, *Categorical Data
    Analysis*, 3rd ed., §10.1.4). With n == 0 there is nothing to test → p = 1.0.
    """
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = math.fsum(math.comb(n, i) * (_MCNEMAR_NULL_P**n) for i in range(k + 1))
    return min(1.0, 2.0 * tail)


def _chi2_1df_sf(stat: float) -> float:
    """Survival function of chi-square with 1 dof at ``stat``.

    Chi-square_1 is the square of a standard normal, so its upper-tail p-value is
    ``P(|Z| > sqrt(stat)) = erfc(sqrt(stat / 2))`` (stdlib ``math.erfc``).
    """
    if stat <= 0.0:
        return 1.0
    return math.erfc(math.sqrt(stat / _CHI2_1DF_HALF))


def mcnemar_delta(
    baseline_resolved: dict[str, bool],
    treatment_resolved: dict[str, bool],
) -> McNemarResult:
    """McNemar's paired test of treatment (A1) vs baseline (A0).

    Inputs map a TaskInstance slug to its single resolved bool per arm (reduced
    by the pairing rule). Only instances present in BOTH arms are paired (``06``
    §Confidence intervals and pairwise tests — "the same instances run by both
    arms"). Builds the discordant counts:

        b = #{ baseline resolved AND treatment not }
        c = #{ treatment resolved AND baseline not }

    The statistic is the continuity-corrected McNemar chi-square
    ``(|b − c| − 1)² / (b + c)`` when ``b + c > 0`` (Edwards 1948). For the
    p-value: at small ``b + c`` (≤ ``MCNEMAR_EXACT_MAX_DISCORDANT``) we use the
    EXACT binomial two-sided test — the correct small-sample McNemar; otherwise
    the chi-square_1 survival of the statistic. ``delta`` is the treatment-minus-
    baseline %Resolved over the paired instances. With no discordant pairs the
    statistic is 0.0 and the p-value 1.0 (no crash, no div-by-zero).
    """
    shared = sorted(set(baseline_resolved) & set(treatment_resolved))
    n_pairs = len(shared)

    b = sum(1 for s in shared if baseline_resolved[s] and not treatment_resolved[s])
    c = sum(1 for s in shared if treatment_resolved[s] and not baseline_resolved[s])

    if n_pairs == 0:
        delta = 0.0
    else:
        base_rate = sum(baseline_resolved[s] for s in shared) / n_pairs
        treat_rate = sum(treatment_resolved[s] for s in shared) / n_pairs
        delta = treat_rate - base_rate

    discordant = b + c
    if discordant == 0:
        # No discordant pairs: nothing distinguishes the arms (well-defined edge).
        return McNemarResult(
            b=b,
            c=c,
            n_pairs=n_pairs,
            delta=delta,
            statistic=0.0,
            p_value=1.0,
            exact=True,
        )

    statistic = (abs(b - c) - 1) ** 2 / discordant
    # The continuity correction can drive the numerator negative when |b−c| < 1
    # (i.e. b == c); clamp so the reported statistic stays non-negative.
    statistic = max(0.0, statistic)

    if discordant <= MCNEMAR_EXACT_MAX_DISCORDANT:
        return McNemarResult(
            b=b,
            c=c,
            n_pairs=n_pairs,
            delta=delta,
            statistic=statistic,
            p_value=_exact_binomial_two_sided(b, c),
            exact=True,
        )
    return McNemarResult(
        b=b,
        c=c,
        n_pairs=n_pairs,
        delta=delta,
        statistic=statistic,
        p_value=_chi2_1df_sf(statistic),
        exact=False,
    )


def _arm_instance_resolved(run: CampaignRun, arm: str) -> dict[str, bool]:
    """Reduce an arm's scored trials to one resolved bool per instance.

    Uses the documented pairing rule (``_instance_resolved_any``).
    """
    reports = _scored_reports_for_arm(run, arm)
    instance_map = _trial_instance_map(run)
    by_instance = group_resolved_by_instance(reports, instance_map)
    return {
        instance: _instance_resolved_any(trials)
        for instance, trials in by_instance.items()
    }


# --- ablation table ----------------------------------------------------------


def ablation_table(
    run: CampaignRun,
    baseline_arm: str = BASELINE_ARM,
    treatment_arm: str = TREATMENT_ARM,
) -> AblationTable:
    """Build the A0-vs-A1 ablation table from a CampaignRun.

    Per-arm rows for ``baseline_arm`` then ``treatment_arm`` (each with Pass@1 +
    CI, Pass@k, regression rate + CI), plus the A1−A0 McNemar delta row (``06``
    §Reporting). The delta is computed only when BOTH arms scored at least one
    trial; otherwise it is ``None`` (the table still renders the per-arm rows).
    """
    rows = tuple(arm_outcome(run, arm) for arm in (baseline_arm, treatment_arm))

    base_resolved = _arm_instance_resolved(run, baseline_arm)
    treat_resolved = _arm_instance_resolved(run, treatment_arm)
    delta: McNemarResult | None = None
    if base_resolved and treat_resolved:
        delta = mcnemar_delta(base_resolved, treat_resolved)

    return AblationTable(arms=rows, delta=delta)


def _fmt_pct(value: float) -> str:
    """Format a proportion as a percentage with one decimal place."""
    return f"{value * 100:.1f}%"


def _fmt_ci(ci: ConfidenceInterval) -> str:
    """Render a point estimate with its 95% interval as ``p% [lo%, hi%]``."""
    return f"{_fmt_pct(ci.point)} [{_fmt_pct(ci.low)}, {_fmt_pct(ci.high)}]"


def render_ablation_table(table: AblationTable) -> str:
    """Render an ``AblationTable`` as a human-readable Markdown table.

    A header, one row per arm with the metric columns, then (when present) the
    A1−A0 delta row carrying the McNemar statistic, p-value, and discordant
    counts — the campaign output of ``06`` §Reporting.
    """
    header = (
        "| Arm | Pass@1 (95% CI) | Pass@k | k | Regression rate (95% CI) | n trials |"
    )
    rule = "| --- | --- | --- | --- | --- | --- |"
    lines = [header, rule]
    for row in table.arms:
        lines.append(
            f"| {row.arm} | {_fmt_ci(row.pass_at_1)} | {_fmt_pct(row.pass_at_k)} "
            f"| {row.k} | {_fmt_ci(row.regression_rate)} | {row.n_trials} |"
        )

    if table.delta is not None:
        d = table.delta
        kind = "exact binomial" if d.exact else "chi-square_1"
        delta_line = (
            f"\n**Delta {TREATMENT_ARM}−{BASELINE_ARM}** (paired, n={d.n_pairs}): "
            f"Δ%Resolved = {d.delta * 100:+.1f} pp; "
            f"McNemar χ² = {d.statistic:.3f} (cc), "
            f"p = {d.p_value:.4f} ({kind}); "
            f"discordant b={d.b}, c={d.c}."
        )
        lines.append(delta_line)
    else:
        lines.append(
            f"\n**Delta {TREATMENT_ARM}−{BASELINE_ARM}**: not computable "
            "(an arm has no scored trials)."
        )

    return "\n".join(lines)
