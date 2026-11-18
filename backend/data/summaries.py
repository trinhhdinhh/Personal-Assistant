"""Daily summaries: one row per day, built from the raw tables.

This is the only view of the data the agent and the dashboard use. The AI
model sees these rows, never raw health samples or mood entries (CLAUDE.md).

Conventions:
- A day's sleep is the night that ENDED that morning (SleepSession.local_date
  is the wake-up day), so "sleep before Tuesday" sits on Tuesday's row.
- Days with no data still get a row, with None values, so gaps stay visible
  and sample sizes (n) are counted honestly.
"""
from collections import defaultdict
from datetime import date, time, timedelta
from statistics import mean

from data.models import CalendarEvent, HealthSample, SleepSession
from data.timeutils import user_tz

LATE_END = time(21, 30)  # an event ending at or after this counts as late

# Real Apple Health data has many samples per metric per day, so each metric
# says how its samples combine into one daily number: total or average.
TOTALS = {"step_count": "steps", "active_energy": "active_energy", "workout_minutes": "workout_minutes"}
AVERAGES = {"heart_rate_variability": "hrv", "resting_heart_rate": "resting_hr",
            "readiness": "readiness", "state_of_mind_valence": "mood"}


def daily_summaries(start: date, end: date) -> list[dict]:
    """One row per day from start to end (both included), oldest first."""
    if end < start:
        raise ValueError("end must be on or after start")

    metrics = _health_by_day(start, end)
    sleep = _sleep_by_day(start, end)
    events = _events_by_day(start, end)

    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    return [_row(day, metrics.get(day, {}), sleep.get(day), events.get(day)) for day in days]


# ---------- reading the tables (one query each) ----------

def _health_by_day(start: date, end: date) -> dict[date, dict[str, list[float]]]:
    by_day: dict[date, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    rows = HealthSample.objects.filter(
        local_date__range=(start, end), metric__in=[*TOTALS, *AVERAGES],
    ).values_list("local_date", "metric", "value")
    for day, metric, value in rows:
        by_day[day][metric].append(value)
    return by_day


def _sleep_by_day(start: date, end: date) -> dict[date, int]:
    """Minutes asleep per wake-up day. Naps on the same day are added together."""
    by_day: dict[date, int] = defaultdict(int)
    rows = SleepSession.objects.filter(local_date__range=(start, end)).values_list("local_date", "asleep_minutes")
    for day, minutes in rows:
        by_day[day] += minutes
    return by_day


def _events_by_day(start: date, end: date) -> dict[date, dict]:
    by_day: dict[date, dict] = defaultdict(lambda: {"hours": 0.0, "late": False, "class": False})
    tz = user_tz()
    rows = CalendarEvent.objects.filter(
        local_date__range=(start, end), all_day=False,
    ).values_list("local_date", "occurred_at", "end_at", "category")
    for day, starts, ends, category in rows:
        info = by_day[day]
        info["hours"] += (ends - starts).total_seconds() / 3600
        local_end = ends.astimezone(tz)
        if local_end.time() >= LATE_END or local_end.date() > day:
            info["late"] = True
        if category == CalendarEvent.Category.CLASS:
            info["class"] = True
    return by_day


# ---------- building one row ----------

def _row(day: date, metrics: dict[str, list[float]], asleep_minutes: int | None, events: dict | None) -> dict:
    has_health = bool(metrics) or asleep_minutes is not None
    row = {"date": day, "sleep_hours": round(asleep_minutes / 60, 2) if asleep_minutes is not None else None}

    for metric, name in AVERAGES.items():
        values = metrics.get(metric)
        row[name] = round(mean(values), 2) if values else None

    for metric, name in TOTALS.items():
        values = metrics.get(metric)
        row[name] = round(sum(values)) if values else None

    # No workout sample on a day with other health data means no workout, not missing data.
    if row["workout_minutes"] is None and has_health:
        row["workout_minutes"] = 0

    row["booked_hours"] = round(events["hours"], 2) if events else 0.0
    row["late_event"] = events["late"] if events else False
    row["class_day"] = events["class"] if events else False
    return row
