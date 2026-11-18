"""Weekly report: one week vs the week before, for the Report page.

Plain calculations over the daily summaries, no AI, so the report is fast,
free, and always the same for the same data. The JSON shape matches the
`Report` type in frontend/lib/mock-data.ts.

Deltas are computed from the rounded numbers shown on screen, so what the
user sees always adds up (6.1 vs 5.4 shows +0.7).
"""
from collections import defaultdict
from datetime import date, timedelta
from statistics import mean

from agent.followups import follow_ups
from data.models import CalendarEvent
from data.summaries import PLEASANT, daily_summaries, mood_label  # noqa: F401  (mood_label re-exported)
from data.timeutils import today

DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MINUS = "−"  # typographic minus, as used in the UI

BUSY_HOURS = 7

# The six stat cards: key, card label, suffix after the value, unit after the delta,
# word for the "biggest changes" title, and how big a change must be to count as notable.
CARDS = [
    ("sleep", "Avg sleep", None, "m", "Sleep", 20),
    ("readiness", "Avg readiness", "/10", "", "Readiness", 0.5),
    ("hrv", "Avg HRV", "ms", " ms", "HRV", 3),
    ("steps", "Avg steps", None, "", "Steps", 800),
    ("workouts", "Workouts", None, "", "Workouts", 1),
    ("pleasant", "Pleasant days", "/{logged}", "", "Pleasant days", 1),
]


def last_full_week() -> date:
    """Monday of the most recent full Mon-Sun week before today."""
    now = today()
    return now - timedelta(days=now.weekday() + 7)


def weekly_report(week_start: date) -> dict:
    week_start -= timedelta(days=week_start.weekday())  # any date picks its Mon-Sun week
    prev_start = week_start - timedelta(days=7)

    this_rows = daily_summaries(week_start, week_start + timedelta(days=6))
    last_rows = daily_summaries(prev_start, prev_start + timedelta(days=6))
    this, last = _week_numbers(this_rows), _week_numbers(last_rows)

    return {
        "label": f"{_span(week_start)} vs {_span(prev_start)}",
        "stats": [_card(card, this, last) for card in CARDS],
        "days": DAY_LABELS,
        "sleepThis": [r["sleep_hours"] for r in this_rows],
        "sleepLast": [r["sleep_hours"] for r in last_rows],
        "readinessThis": [_round(r["readiness"], 1) for r in this_rows],
        "moodThis": [mood_label(r["mood"]) for r in this_rows],
        "timeUse": _time_use(week_start, prev_start),
        "changes": _changes(this, last),
        "followUps": follow_ups(week_start + timedelta(days=7)),  # checked suggestions (agent/followups.py)
    }


# ---------- one week's numbers, rounded as displayed ----------

def _week_numbers(rows: list[dict]) -> dict:
    sleep = _avg(rows, "sleep_hours")
    moods = [r["mood"] for r in rows if r["mood"] is not None]
    has_health = any(r["workout_minutes"] is not None for r in rows)
    return {
        "sleep": round(sleep * 60) if sleep is not None else None,  # minutes
        "readiness": _round(_avg(rows, "readiness"), 1),
        "hrv": _round(_avg(rows, "hrv"), 0),
        "steps": _round(_avg(rows, "steps"), 0),
        "workouts": sum(1 for r in rows if r["workout_minutes"]) if has_health else None,
        "pleasant": sum(1 for m in moods if m >= PLEASANT) if moods else None,
        "logged": len(moods),
        "busy_days": sum(1 for r in rows if r["booked_hours"] >= BUSY_HOURS),
        "late_events": sum(1 for r in rows if r["late_event"]),
    }


def _avg(rows: list[dict], key: str) -> float | None:
    values = [r[key] for r in rows if r[key] is not None]
    return mean(values) if values else None


def _round(value: float | None, digits: int) -> float | int | None:
    if value is None:
        return None
    return round(value) if digits == 0 else round(value, digits)


# ---------- formatting ----------

def _show(key: str, value) -> str:
    if value is None:
        return "–"
    if key == "sleep":
        return f"{value // 60}h {value % 60}m"
    if key == "steps":
        return f"{value:,}"
    return str(value)


def _signed(value: float, unit: str = "") -> str:
    if value == 0:
        return "0"
    sign = "+" if value > 0 else MINUS
    number = abs(value)
    text = f"{number:,}" if isinstance(number, int) else f"{number:g}"
    return f"{sign}{text}{unit}"


def _delta(key: str, this: dict, last: dict):
    if this[key] is None or last[key] is None:
        return None
    diff = this[key] - last[key]
    return round(diff, 1) if isinstance(diff, float) else diff


def _card(card: tuple, this: dict, last: dict) -> dict:
    key, label, suffix, unit, _, _ = card
    diff = _delta(key, this, last)
    tone = "muted" if not diff else ("success" if diff > 0 else "warning")
    return {
        "label": label,
        "value": _show(key, this[key]),
        "suffix": suffix.format(logged=this["logged"]) if suffix else None,
        "delta": "n/a" if diff is None else _signed(diff, unit),
        "tone": tone,
    }


def _span(start: date) -> str:
    end = start + timedelta(days=6)
    first = f"{start:%b} {start.day}".upper()
    last = str(end.day) if end.month == start.month else f"{end:%b} {end.day}".upper()
    return f"{first} – {last}"


# ---------- biggest changes ----------

def _changes(this: dict, last: dict) -> list[dict]:
    """The (at most two) stats that moved most relative to their notable size."""
    moved = []
    for key, _, _, unit, word, notable in CARDS:
        diff = _delta(key, this, last)
        if diff and abs(diff) >= notable:
            moved.append((abs(diff) / notable, key, word, unit, diff))
    moved.sort(reverse=True)

    changes = []
    for i, (_, key, word, unit, diff) in enumerate(moved[:2]):
        direction = "up" if diff > 0 else "down"
        body = f"{_show(key, this[key])} vs {_show(key, last[key])} the week before."
        if i == 0:  # context for the biggest change, stated as numbers only, never as a cause
            body += (f" This week had {this['busy_days']} busy days (7h+ booked) and {this['late_events']} late events,"
                     f" vs {last['busy_days']} and {last['late_events']}.")
        changes.append({"title": f"{word} {direction} {_signed(abs(diff), unit)[1:]}", "body": body})

    if not changes:
        changes.append({"title": "A steady week", "body": "Every measure stayed close to the week before."})
    return changes


# ---------- where the time went ----------

def _time_use(week_start: date, prev_start: date) -> list[dict]:
    hours: dict[str, dict[str, float]] = defaultdict(lambda: {"this": 0.0, "last": 0.0})
    events = CalendarEvent.objects.filter(
        local_date__range=(prev_start, week_start + timedelta(days=6)), all_day=False,
    ).values_list("local_date", "category", "occurred_at", "end_at")
    for day, category, starts, ends in events:
        week = "this" if day >= week_start else "last"
        hours[category][week] += (ends - starts).total_seconds() / 3600

    rows = []
    for category, h in hours.items():
        this_h, last_h = _tidy(h["this"]), _tidy(h["last"])
        if this_h or last_h:
            rows.append({"category": category.capitalize(), "hours": this_h, "delta": _signed(_tidy(this_h - last_h))})
    return sorted(rows, key=lambda r: r["hours"], reverse=True)


def _tidy(hours: float) -> float | int:
    """Round to one decimal, and drop the .0 so 4.0 shows as 4."""
    value = round(hours, 1)
    return int(value) if value == int(value) else value
