"""The agent's tools: plain Python functions over the daily summaries.

Rules every tool follows:
- Works only from daily summaries (data/summaries.py) or calendar events,
  never raw health samples or mood entries (privacy rule in CLAUDE.md).
- Returns a small JSON-ready dict. Every number the agent may quote is in it.
- Adds a `notes` list when the result needs a caveat: fewer than 14 days of
  data, or that a correlation is not a cause.
- Raises ToolError with a message the model can act on when the input is bad.
- Never changes the calendar. `make_ics_event` only returns a file's text.

The JSON schemas the model sees live in agent/registry.py.
"""
import uuid
from datetime import date, datetime, time, timedelta, timezone
from statistics import StatisticsError, correlation, mean

from django.utils import timezone as dj_timezone

from agent.models import Suggestion
from data.models import CalendarEvent
from data.summaries import daily_summaries, mood_label
from data.timeutils import clock12, today, user_tz

MIN_DAYS = 14          # fewer days than this and a pattern is "early"
MAX_RANGE_DAYS = 120   # longest date range a tool accepts
BUSY_HOURS = 7.0       # a day with this many hours booked counts as busy
SHORT_SLEEP_HOURS = 6.0

# Numeric fields of a daily summary the agent can ask for.
METRICS = ["sleep_hours", "readiness", "hrv", "resting_hr", "mood", "steps",
           "active_energy", "workout_minutes", "booked_hours"]

# Yes/no facts about a day, derived from the summary.
CONDITIONS = ["busy_day", "late_event", "short_sleep", "workout_day", "class_day"]

# How big a change has to be to count as real, per metric (used by evaluate_suggestion).
MEANINGFUL_CHANGE = {
    "sleep_hours": 0.33, "readiness": 0.5, "hrv": 3, "resting_hr": 1, "mood": 0.1,
    "steps": 800, "active_energy": 50, "workout_minutes": 10, "booked_hours": 1,
}

NOT_CAUSATION = "This shows the two move together, not that one causes the other."


class ToolError(Exception):
    """Bad input. The message goes back to the model so it can fix the call."""


# ---------- shared helpers ----------

def _parse_date(text: str, field: str) -> date:
    try:
        return date.fromisoformat(text)
    except (TypeError, ValueError):
        raise ToolError(f"{field} must be a date like 2026-11-09, got {text!r}") from None


def _parse_range(start: str, end: str, max_days: int = MAX_RANGE_DAYS) -> tuple[date, date]:
    first, last = _parse_date(start, "start_date"), _parse_date(end, "end_date")
    if last < first:
        raise ToolError("end_date must be on or after start_date")
    if (last - first).days + 1 > max_days:
        raise ToolError(f"Date range is too long. Ask for at most {max_days} days at a time.")
    return first, last


def _parse_hhmm(text: str, field: str) -> time:
    try:
        return time.fromisoformat(text)
    except (TypeError, ValueError):
        raise ToolError(f"{field} must be a 24-hour time like 15:30, got {text!r}") from None


def _check_name(name: str, allowed: list[str], field: str) -> None:
    if name not in allowed:
        raise ToolError(f"{field} must be one of {allowed}, got {name!r}")


def _value(row: dict, name: str):
    """A metric or condition for one day. None means no data."""
    if name == "busy_day":
        return row["booked_hours"] >= BUSY_HOURS
    if name == "late_event":
        return row["late_event"]
    if name == "class_day":
        return row["class_day"]
    if name == "short_sleep":
        return None if row["sleep_hours"] is None else row["sleep_hours"] < SHORT_SLEEP_HOURS
    if name == "workout_day":
        return None if row["workout_minutes"] is None else row["workout_minutes"] > 0
    return row[name]


def _avg(values: list) -> float | None:
    values = [v for v in values if v is not None]
    return round(mean(values), 2) if values else None


def _local(moment: datetime) -> datetime:
    return moment.astimezone(user_tz())


def _early_note(n: int, what: str = "days with data") -> list[str]:
    if n < MIN_DAYS:
        return [f"Only {n} {what} (under {MIN_DAYS}), so treat this as early and uncertain."]
    return []


# ---------- 1. query_data ----------

def query_data(start_date: str, end_date: str, metrics: list[str]) -> dict:
    first, last = _parse_range(start_date, end_date)
    if not metrics:
        raise ToolError("metrics must list at least one name")
    for name in metrics:
        _check_name(name, METRICS + CONDITIONS, "each metric")

    rows = daily_summaries(first, last)
    days = [{"date": r["date"].isoformat(), **{m: _value(r, m) for m in metrics}} for r in rows]
    return {
        "start_date": first.isoformat(),
        "end_date": last.isoformat(),
        "days": days,
        "days_with_data": {m: sum(1 for d in days if d[m] is not None) for m in metrics},
        "averages": {m: _avg([d[m] for d in days]) for m in metrics if m in METRICS},
    }


# ---------- 2. get_calendar ----------

def get_calendar(start_date: str, end_date: str) -> dict:
    first, last = _parse_range(start_date, end_date, max_days=31)
    events = CalendarEvent.objects.filter(local_date__range=(first, last)).order_by("occurred_at")

    items, hours_by_day = [], {}
    for e in events:
        hours = round((e.end_at - e.occurred_at).total_seconds() / 3600, 2)
        items.append({
            "date": e.local_date.isoformat(),
            "start": "all day" if e.all_day else f"{_local(e.occurred_at):%H:%M}",
            "end": "all day" if e.all_day else f"{_local(e.end_at):%H:%M}",
            "hours": None if e.all_day else hours,
            "title": e.title,
            "category": e.category,
        })
        if not e.all_day:
            key = e.local_date.isoformat()
            hours_by_day[key] = round(hours_by_day.get(key, 0) + hours, 2)

    return {"start_date": first.isoformat(), "end_date": last.isoformat(),
            "events": items, "booked_hours_by_day": hours_by_day}


# ---------- 3. compare_periods ----------

def compare_periods(metric: str, period_a_start: str, period_a_end: str,
                    period_b_start: str, period_b_end: str) -> dict:
    _check_name(metric, METRICS, "metric")
    a_first, a_last = _parse_range(period_a_start, period_a_end)
    b_first, b_last = _parse_range(period_b_start, period_b_end)

    a = [r[metric] for r in daily_summaries(a_first, a_last) if r[metric] is not None]
    b = [r[metric] for r in daily_summaries(b_first, b_last) if r[metric] is not None]
    a_avg, b_avg = _avg(a), _avg(b)

    result = {
        "metric": metric,
        "period_a": {"start": a_first.isoformat(), "end": a_last.isoformat(), "average": a_avg, "days_with_data": len(a)},
        "period_b": {"start": b_first.isoformat(), "end": b_last.isoformat(), "average": b_avg, "days_with_data": len(b)},
        "difference": None, "percent_change": None, "notes": [],
    }
    if a_avg is None or b_avg is None:
        result["notes"].append("One of the periods has no data for this metric.")
        return result

    result["difference"] = round(a_avg - b_avg, 2)
    if b_avg:
        result["percent_change"] = round((a_avg - b_avg) / abs(b_avg) * 100, 1)
    if min(len(a), len(b)) < MIN_DAYS:
        result["notes"].append(
            f"At least one period has under {MIN_DAYS} days with data. Describe this as a difference "
            "between these periods, not as a lasting pattern.")
    return result


# ---------- 4. compute_correlation ----------

def _strength(r: float) -> str:
    size = abs(r)
    if size < 0.1:
        return "none"
    if size < 0.3:
        return "weak"
    if size < 0.5:
        return "moderate"
    return "strong"


def compute_correlation(x: str, y: str, start_date: str, end_date: str, lag_days: int = 0) -> dict:
    _check_name(x, METRICS + CONDITIONS, "x")
    _check_name(y, METRICS, "y")
    if not 0 <= lag_days <= 3:
        raise ToolError("lag_days must be between 0 and 3")
    first, last = _parse_range(start_date, end_date)

    rows = daily_summaries(first, last + timedelta(days=lag_days))
    pairs = []
    for i in range(len(rows) - lag_days):
        x_val, y_val = _value(rows[i], x), _value(rows[i + lag_days], y)
        if x_val is not None and y_val is not None:
            pairs.append((float(x_val), float(y_val)))

    later = "the same day" if lag_days == 0 else f"{lag_days} day{'s' if lag_days > 1 else ''} later"
    result = {
        "x": x, "y": y, "lag_days": lag_days,
        "meaning": f"{x} on a day, compared with {y} {later}",
        "start_date": first.isoformat(), "end_date": last.isoformat(),
        "paired_days": len(pairs), "r": None, "strength": None, "direction": None,
        "notes": _early_note(len(pairs), "paired days") + [NOT_CAUSATION],
    }

    if x in CONDITIONS:
        yes = [b for a, b in pairs if a == 1]
        no = [b for a, b in pairs if a == 0]
        result["groups"] = {
            f"{x}_yes": {"days": len(yes), f"average_{y}": _avg(yes)},
            f"{x}_no": {"days": len(no), f"average_{y}": _avg(no)},
        }
        if yes and no:
            result["groups"]["difference_yes_minus_no"] = round(_avg(yes) - _avg(no), 2)
        if min(len(yes), len(no)) < 5:
            result["notes"].append("One group has fewer than 5 days, so the averages are rough.")

    try:
        r = correlation([a for a, _ in pairs], [b for _, b in pairs])
    except StatisticsError:
        result["notes"].append("Not enough varied data to compute a correlation.")
        return result

    result["r"] = round(r, 2)
    result["strength"] = _strength(r)
    result["direction"] = "none" if result["strength"] == "none" else ("positive" if r > 0 else "negative")
    return result


# ---------- 5. forecast_week ----------

FORECAST_METRICS = ["readiness", "mood", "sleep_hours", "hrv"]


def _profile(prev_row: dict) -> tuple[bool, bool]:
    """What the day before looked like: (busy, had a late event)."""
    return _value(prev_row, "busy_day"), prev_row["late_event"]


def _risk(readiness_change: float | None, mood_change: float | None) -> str:
    readiness_change, mood_change = readiness_change or 0, mood_change or 0
    if readiness_change <= -1.0 or mood_change <= -0.2:
        return "high"
    if readiness_change <= -0.5 or mood_change <= -0.1:
        return "medium"
    return "low"


def forecast_week(start_date: str | None = None) -> dict:
    first = _parse_date(start_date, "start_date") if start_date else today()
    history = daily_summaries(first - timedelta(days=60), first - timedelta(days=1))
    upcoming = daily_summaries(first - timedelta(days=1), first + timedelta(days=6))  # includes the day before

    # Group past days by what the day before looked like.
    by_profile: dict[tuple, list[dict]] = {}
    for prev, row in zip(history, history[1:]):
        by_profile.setdefault(_profile(prev), []).append(row)
    baseline = {m: _avg([r[m] for r in history]) for m in FORECAST_METRICS}
    history_days = sum(1 for r in history if r["readiness"] is not None)

    days = []
    for prev, row in zip(upcoming, upcoming[1:]):
        busy_before, late_before = _profile(prev)
        similar = by_profile.get((busy_before, late_before), [])
        similar_n = sum(1 for r in similar if r["readiness"] is not None)
        expected = {m: _avg([r[m] for r in similar]) for m in FORECAST_METRICS} if similar_n >= 3 else dict(baseline)
        change = {m: (round(expected[m] - baseline[m], 2) if expected[m] is not None and baseline[m] is not None else None)
                  for m in FORECAST_METRICS}

        reasons = []
        if busy_before:
            reasons.append(f"the day before has {prev['booked_hours']}h booked (busy)")
        if late_before:
            reasons.append("an event runs late the night before")
        if row["booked_hours"] >= BUSY_HOURS:
            reasons.append(f"{row['booked_hours']}h booked this day, which tends to weigh on the next day")
        if similar_n < 3:
            reasons.append("too few similar past days, so this uses your overall average")

        days.append({
            "date": row["date"].isoformat(),
            "weekday": f"{row['date']:%a}",
            "booked_hours": row["booked_hours"],
            "busy": row["booked_hours"] >= BUSY_HOURS,
            "late_event": row["late_event"],
            "after_busy_day": busy_before,
            "after_late_event": late_before,
            "expected_readiness": expected["readiness"],
            "expected_mood": expected["mood"],
            "expected_mood_label": mood_label(expected["mood"]),
            "expected_sleep_hours": expected["sleep_hours"],
            "readiness_vs_usual": change["readiness"],
            "mood_vs_usual": change["mood"],
            "sleep_vs_usual": change["sleep_hours"],
            "similar_past_days": similar_n,
            "risk": _risk(change["readiness"], change["mood"]),
            "reasons": reasons,
        })

    return {
        "start_date": first.isoformat(),
        "method": "Each day is matched with past days whose previous day looked the same "
                  "(busy or not, late event or not), over the last 60 days.",
        "history_days_with_data": history_days,
        "usual": baseline,
        "days": days,
        "notes": _early_note(history_days) + [
            "A forecast from your own past patterns, not a certainty. " + NOT_CAUSATION],
    }


# ---------- 6. find_free_time ----------

def find_free_time(date: str, min_minutes: int = 30, day_start: str = "08:00", day_end: str = "22:00") -> dict:
    day = _parse_date(date, "date")
    window_start, window_end = _parse_hhmm(day_start, "day_start"), _parse_hhmm(day_end, "day_end")
    if window_end <= window_start:
        raise ToolError("day_end must be after day_start")
    if not 5 <= min_minutes <= 480:
        raise ToolError("min_minutes must be between 5 and 480")

    tz = user_tz()
    lo, hi = datetime.combine(day, window_start, tz), datetime.combine(day, window_end, tz)
    busy = sorted(
        (max(e.occurred_at, lo), min(e.end_at, hi))
        for e in CalendarEvent.objects.filter(local_date=day, all_day=False)
        if e.end_at > lo and e.occurred_at < hi
    )

    gaps, cursor = [], lo
    for start, end in busy:
        if start > cursor:
            gaps.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < hi:
        gaps.append((cursor, hi))

    free = [
        {"start": f"{_local(s):%H:%M}", "end": f"{_local(e):%H:%M}", "minutes": int((e - s).total_seconds() // 60)}
        for s, e in gaps if (e - s) >= timedelta(minutes=min_minutes)
    ]
    return {"date": day.isoformat(), "weekday": f"{day:%a}", "window": f"{day_start}-{day_end}",
            "free_slots": free, "events_in_window": len(busy)}


# ---------- 7. make_ics_event ----------

def _ics_text(text: str) -> str:
    """Escape text for an .ics file (RFC 5545)."""
    return (text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
            .replace("\r\n", "\\n").replace("\n", "\\n"))


def _ics_fold(line: str) -> str:
    """.ics lines must be at most 75 characters; longer ones continue on lines starting with a space."""
    parts = [line[i:i + 74] for i in range(0, len(line), 74)] or [""]
    return "\r\n ".join(parts)


def make_ics_event(title: str, date: str, start_time: str, duration_minutes: int, notes: str = "") -> dict:
    day = _parse_date(date, "date")
    starts_at = _parse_hhmm(start_time, "start_time")
    title = title.strip()
    if not title or len(title) > 120:
        raise ToolError("title must be 1-120 characters")
    if not 5 <= duration_minutes <= 480:
        raise ToolError("duration_minutes must be between 5 and 480")

    start = datetime.combine(day, starts_at, user_tz()).astimezone(timezone.utc)
    end = start + timedelta(minutes=duration_minutes)
    stamp = "%Y%m%dT%H%M%SZ"
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Personal Life Agent//EN", "BEGIN:VEVENT",
        f"UID:{uuid.uuid4()}@life-agent",
        f"DTSTAMP:{datetime.now(timezone.utc):{stamp}}",
        f"DTSTART:{start:{stamp}}",
        f"DTEND:{end:{stamp}}",
        f"SUMMARY:{_ics_text(title)}",
    ]
    if notes:
        lines.append(f"DESCRIPTION:{_ics_text(notes)}")
    lines += ["END:VEVENT", "END:VCALENDAR"]

    slug = "-".join(title.lower().split())[:40]
    return {
        "filename": f"{day.isoformat()}-{slug}.ics",
        "ics": "\r\n".join(_ics_fold(line) for line in lines) + "\r\n",
        "summary": f"{title}, {day:%a %b} {day.day} at {clock12(f'{starts_at:%H:%M}')} for {duration_minutes} min",
        "note": "This is a file for the user to add if they choose. Nothing was added to their calendar.",
    }


# ---------- 8. save_suggestion ----------

def save_suggestion(text: str, metric: str, direction: str, start_date: str, check_after_days: int = 7) -> dict:
    _check_name(metric, METRICS, "metric")
    _check_name(direction, ["up", "down"], "direction")
    if not 3 <= check_after_days <= 28:
        raise ToolError("check_after_days must be between 3 and 28")
    text = text.strip()
    if not text or len(text) > 500:
        raise ToolError("text must be 1-500 characters")
    first = _parse_date(start_date, "start_date")

    before = [r[metric] for r in daily_summaries(first - timedelta(days=MIN_DAYS), first - timedelta(days=1))
              if r[metric] is not None]
    suggestion = Suggestion.objects.create(
        text=text, metric=metric, direction=direction, start_date=first,
        check_on=first + timedelta(days=check_after_days),
        baseline=_avg(before), baseline_days=len(before),
    )
    return {
        "suggestion_id": suggestion.pk,
        "metric": metric, "direction": direction,
        "baseline": suggestion.baseline, "baseline_days": len(before),
        "check_on": suggestion.check_on.isoformat(),
        "notes": _early_note(len(before), "days of baseline data"),
    }


# ---------- 9. evaluate_suggestion ----------

def _evaluate(s: Suggestion) -> dict:
    info = {"suggestion_id": s.pk, "text": s.text, "metric": s.metric, "direction": s.direction,
            "start_date": s.start_date.isoformat(), "check_on": s.check_on.isoformat()}

    now = today()
    if now < s.check_on:
        return {**info, "status": "too_early", "days_left": (s.check_on - now).days}

    after = [r[s.metric] for r in daily_summaries(s.start_date, s.check_on - timedelta(days=1))
             if r[s.metric] is not None]
    s.result, s.result_days = _avg(after), len(after)

    if s.baseline is None or s.result is None or len(after) < 3:
        s.status = Suggestion.Status.NO_DATA
    else:
        change = s.result - s.baseline if s.direction == "up" else s.baseline - s.result
        size = MEANINGFUL_CHANGE[s.metric]
        s.status = (Suggestion.Status.IMPROVED if change >= size
                    else Suggestion.Status.WORSE if change <= -size
                    else Suggestion.Status.NO_CHANGE)
    s.evaluated_at = dj_timezone.now()
    s.save()

    return {
        **info, "status": s.status,
        "before": {"average": s.baseline, "days": s.baseline_days},
        "after": {"average": s.result, "days": s.result_days},
        "difference": round(s.result - s.baseline, 2) if s.result is not None and s.baseline is not None else None,
        "meaningful_change": MEANINGFUL_CHANGE[s.metric],
        "notes": ["Shows what changed after the suggestion, not proof that the suggestion caused it."],
    }


def evaluate_suggestion(suggestion_id: int | None = None) -> dict:
    if suggestion_id is not None:
        suggestion = Suggestion.objects.filter(pk=suggestion_id).first()
        if suggestion is None:
            raise ToolError(f"No suggestion with id {suggestion_id}. Call evaluate_suggestion "
                            "without an id to see every suggestion that is due.")
        return {"results": [_evaluate(suggestion)]}

    due = Suggestion.objects.filter(status=Suggestion.Status.PENDING, check_on__lte=today())
    waiting = Suggestion.objects.filter(status=Suggestion.Status.PENDING, check_on__gt=today())
    return {
        "results": [_evaluate(s) for s in due],
        "still_waiting": [{"suggestion_id": s.pk, "text": s.text, "check_on": s.check_on.isoformat()} for s in waiting],
    }
