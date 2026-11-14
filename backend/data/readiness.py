"""Readiness score (0-100): how recovered I am today.

Apple Health has no readiness score, so we compute our own from three Watch
numbers, each compared with MY normal (the average of the previous 28 days):

| Part        | Weight | Score 70 means        | Moves by                         |
|-------------|--------|-----------------------|----------------------------------|
| HRV         | 40%    | equal to my normal    | 15 points per 10% above/below    |
| Resting HR  | 30%    | equal to my normal    | 5 points per bpm (lower is better) |
| Sleep       | 30%    | -                     | 100 at 8h asleep, scaled linearly |

Each part is clamped to 0-100. A normal day with 8h of sleep scores 79.
A day with HRV 10% low, resting HR 3 bpm high and 6h sleep scores 61.

We need at least `MIN_BASELINE_DAYS` of history before trusting the normal;
before that, readiness is None (unknown), never guessed.
"""
from statistics import mean

BASELINE_DAYS = 28
MIN_BASELINE_DAYS = 7
SLEEP_TARGET_HOURS = 8

HRV_WEIGHT = 0.4
RHR_WEIGHT = 0.3
SLEEP_WEIGHT = 0.3


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def hrv_score(hrv: float, hrv_normal: float) -> float:
    percent_change = (hrv - hrv_normal) / hrv_normal * 100
    return _clamp(70 + 1.5 * percent_change)


def resting_hr_score(rhr: float, rhr_normal: float) -> float:
    return _clamp(70 - 5 * (rhr - rhr_normal))


def sleep_score(sleep_hours: float) -> float:
    return _clamp(sleep_hours / SLEEP_TARGET_HOURS * 100)


def readiness(hrv: float, hrv_normal: float, rhr: float, rhr_normal: float, sleep_hours: float) -> int:
    """Combine the three parts into one 0-100 score."""
    score = (
        HRV_WEIGHT * hrv_score(hrv, hrv_normal)
        + RHR_WEIGHT * resting_hr_score(rhr, rhr_normal)
        + SLEEP_WEIGHT * sleep_score(sleep_hours)
    )
    return round(score)


def baseline(previous_values: list[float]) -> float | None:
    """My normal: the average of the last `BASELINE_DAYS` values (oldest first).

    Returns None if there are fewer than `MIN_BASELINE_DAYS` values.
    """
    recent = previous_values[-BASELINE_DAYS:]
    if len(recent) < MIN_BASELINE_DAYS:
        return None
    return mean(recent)


def readiness_for_day(
    hrv: float | None,
    rhr: float | None,
    sleep_hours: float | None,
    previous_hrv: list[float],
    previous_rhr: list[float],
) -> int | None:
    """Readiness for one day, or None if any input or baseline is missing."""
    hrv_normal = baseline(previous_hrv)
    rhr_normal = baseline(previous_rhr)
    if None in (hrv, rhr, sleep_hours, hrv_normal, rhr_normal):
        return None
    return readiness(hrv, hrv_normal, rhr, rhr_normal, sleep_hours)
