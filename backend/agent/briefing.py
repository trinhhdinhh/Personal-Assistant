"""The Week and Today pages, built from the agent's own tools with no model call.

Both pages are plain calculations over the same tools the agent uses, so
they load instantly, cost nothing, and show the same numbers every time.
The reasoning agent lives on the Ask page.

Suggestions here are rules over your own patterns: each one quotes the
pattern it rests on and its sample size. Nothing is saved when a page
loads; a suggestion is saved for follow-up only when the user adds it.
"""
from datetime import date, datetime, timedelta

from agent import tools
from agent.tools import BUSY_HOURS
from data.summaries import daily_summaries
from data.synthetic import mood_label as apple_mood_label
from data.timeutils import today

HISTORY_DAYS = 60
MINUS = "−"

# The patterns the pages explain: (x, y, lag, "when", "affects", unit)
FACTORS = [
    ("busy_day", "readiness", 1, "7h+ booked", "Next-day readiness", "pts"),
    ("late_event", "sleep_hours", 1, "Event ends 9:30pm+", "Sleep that night", "min"),
    ("short_sleep", "readiness", 0, "Sleep under 6h", "Readiness that morning", "pts"),
    ("workout_day", "mood", 1, "Workout day", "Next-day mood", "mood"),
]


class Calls:
    """Runs tools and counts them, so the page can say how many tool calls it took."""

    def __init__(self):
        self.count = 0

    def __call__(self, name: str, **kwargs) -> dict:
        self.count += 1
        return getattr(tools, name)(**kwargs)


# ---------- small formatting helpers ----------

def _signed(value: float, digits: int = 1) -> str:
    text = f"{abs(value):.{digits}f}" if digits else f"{round(abs(value))}"
    return "0" if float(text) == 0 else ("+" if value > 0 else MINUS) + text


def _hm(hours: float) -> str:
    minutes = round(hours * 60)
    return f"{minutes // 60}h {minutes % 60:02d}m"


def _clock(day: date, hhmm: str, plus_minutes: int = 0) -> str:
    moment = datetime.combine(day, datetime.strptime(hhmm, "%H:%M").time()) + timedelta(minutes=plus_minutes)
    return f"{moment:%H:%M}"


def _suggestion(key, title, why, evidence, track, time=None, ics=None) -> dict:
    """`track` is what gets saved if the user adds it: {text, metric, direction, start_date}."""
    return {"id": key, "title": title, "time": time, "why": why, "evidence": evidence, "ics": ics, "track": track}


# ---------- patterns ----------

def patterns(calls: Calls, start: date) -> dict:
    """The FACTORS over the last 60 days before `start`, keyed by x."""
    found = {}
    for x, y, lag, cause, effect, unit in FACTORS:
        r = calls("compute_correlation", x=x, y=y, lag_days=lag,
                  start_date=(start - timedelta(days=HISTORY_DAYS)).isoformat(),
                  end_date=(start - timedelta(days=1)).isoformat())
        groups = r.get("groups", {})
        yes, no = groups.get(f"{x}_yes", {}), groups.get(f"{x}_no", {})
        diff = groups.get("difference_yes_minus_no")
        if diff is None or r["strength"] not in {"moderate", "strong"}:
            continue
        size = {"pts": f"{_signed(diff)} pts", "min": f"{_signed(diff * 60, 0)} min", "mood": f"{_signed(diff, 2)} mood"}[unit]
        found[x] = {"cause": cause, "effect": effect, "size": size, "n": yes["days"],
                    "yes": yes[f"average_{y}"], "no": no[f"average_{y}"], "early": yes["days"] < tools.MIN_DAYS}
    return found


# ---------- Week page ----------

def week_view(start: date | None = None) -> dict:
    calls = Calls()
    start = start or today()
    forecast = calls("forecast_week", start_date=start.isoformat())
    found = patterns(calls, start)

    days = []
    for d in forecast["days"]:
        day = date.fromisoformat(d["date"])
        prev = f"{day - timedelta(days=1):%a}"
        parts = [f"{d['booked_hours']:g}h booked"] if d["busy"] else []
        if d["after_late_event"]:
            parts.append(f"after a late {prev}")
        elif d["after_busy_day"]:
            parts.append(f"after a busy {prev}")
        note = " ".join(parts)
        days.append({
            "label": d["weekday"], "date": str(day.day), "iso": d["date"],
            "booked": d["booked_hours"],
            "readiness": round(d["expected_readiness"], 1) if d["expected_readiness"] is not None else None,
            "risk": d["risk"].capitalize(),
            "note": note[:1].upper() + note[1:] if note else None,
            "today": day == today(),
        })

    end = start + timedelta(days=6)
    return {
        "label": f"{start:%b} {start.day} – {end:%b} {end.day}".upper() if end.month != start.month
                 else f"{start:%b} {start.day} – {end.day}".upper(),
        "similarDays": forecast["history_days_with_data"],
        "usualReadiness": forecast["usual"]["readiness"],
        "days": days,
        "factors": [{k: f[k] for k in ("cause", "effect", "size", "n", "early")} for f in found.values()],
        "adjustments": _week_adjustments(calls, forecast, found),
        "toolCalls": calls.count,
        "notes": forecast["notes"],
    }


def _week_adjustments(calls: Calls, forecast: dict, found: dict) -> list[dict]:
    risky = sorted((d for d in forecast["days"] if d["risk"] != "low"), key=lambda d: d["readiness_vs_usual"] or 0)
    if not risky:
        return []
    worst = risky[0]
    worst_day = date.fromisoformat(worst["date"])
    adjustments = []

    # 1. A late event the night before the hardest day: move it earlier that day.
    late = found.get("late_event")
    if worst["after_late_event"] and late:
        prev = worst_day - timedelta(days=1)
        events = calls("get_calendar", start_date=prev.isoformat(), end_date=prev.isoformat())["events"]
        late_events = [e for e in events if e["end"] != "all day" and (e["end"] >= "21:30" or e["end"] < e["start"])]
        if late_events:
            event = late_events[-1]
            length = round(event["hours"] * 60)
            slots = calls("find_free_time", date=prev.isoformat(), min_minutes=length, day_start="12:00", day_end="21:00")
            # Prefer the first afternoon gap that fits, so it ends well before the late cutoff.
            fits = slots["free_slots"]
            slot = next((s for s in fits if s["start"] >= "14:00"), fits[-1] if fits else None)
            if slot:
                begin = slot["start"]
                finish = _clock(prev, begin, length)
                title = f"Move {prev:%A}'s {event['title'].lower()} to {begin}–{finish}"
                why = (f"It ends at {event['end']}, the night before your hardest day. After late events you sleep "
                       f"{late['yes']:g}h vs {late['no']:g}h on other nights.")
                ics = calls("make_ics_event", title=event["title"], date=prev.isoformat(), start_time=begin,
                            duration_minutes=length, notes="Moved earlier so it doesn't run late before a heavy day.")
                adjustments.append(_suggestion(
                    f"move-{prev}", title, why, f"n = {late['n']} late nights",
                    {"text": title, "metric": "sleep_hours", "direction": "up", "start_date": worst["date"]},
                    time=f"{begin}–{finish}", ics=ics))

    # 2. A short walk in the longest gap on the hardest day.
    slots = calls("find_free_time", date=worst["date"], min_minutes=20, day_start="10:00", day_end="18:00")["free_slots"]
    if slots:
        slot = max(slots, key=lambda s: s["minutes"])
        finish = _clock(worst_day, slot["start"], 20)
        title = f"Add a 20-minute walk {worst_day:%A} at {slot['start']}"
        why = (f"{worst_day:%A} is your hardest day: {worst['booked_hours']:g}h booked, forecast readiness "
               f"{worst['expected_readiness']:.1f} vs your usual {forecast['usual']['readiness']:.1f}. "
               f"Your longest gap is {slot['start']}–{slot['end']}.")
        ics = calls("make_ics_event", title="Walk outside", date=worst["date"], start_time=slot["start"],
                    duration_minutes=20, notes="A short break on a heavy day.")
        adjustments.append(_suggestion(
            f"walk-{worst['date']}", title, why, f"{forecast['history_days_with_data']} days of history",
            {"text": title, "metric": "steps", "direction": "up", "start_date": worst["date"]},
            time=f"{slot['start']}–{finish}", ics=ics))

    # 3. Protect sleep before the day after the hardest one, if it's risky too.
    short = found.get("short_sleep")
    after = next((d for d in risky if date.fromisoformat(d["date"]) == worst_day + timedelta(days=1)), None)
    if after and short:
        title = f"Wind down by 22:30 on {worst_day:%A}"
        why = (f"{date.fromisoformat(after['date']):%A} is forecast {after['risk']} risk too. Mornings after under 6h "
               f"of sleep, your readiness averages {short['yes']:g} vs {short['no']:g}.")
        ics = calls("make_ics_event", title="Wind down", date=worst["date"], start_time="22:30",
                    duration_minutes=30, notes="Screens off, lights low.")
        adjustments.append(_suggestion(
            f"winddown-{worst['date']}", title, why, f"n = {short['n']} short nights",
            {"text": title, "metric": "sleep_hours", "direction": "up", "start_date": after["date"]},
            time="22:30", ics=ics))
    return adjustments


# ---------- Today page ----------

def brief_view(day: date | None = None) -> dict:
    calls = Calls()
    day = day or today()

    # Health data arrives after the fact, so use the latest day that has it.
    recent = calls("query_data", start_date=(day - timedelta(days=21)).isoformat(), end_date=day.isoformat(),
                   metrics=["sleep_hours", "readiness", "hrv", "resting_hr", "mood"])["days"]
    with_data = [r for r in recent if r["readiness"] is not None]
    latest = with_data[-1] if with_data else None
    before = with_data[-15:-1]

    def usual(metric):
        values = [r[metric] for r in before if r[metric] is not None]
        return sum(values) / len(values) if values else None

    health = None
    if latest:
        sleep_avg, hrv_avg, rhr_avg = usual("sleep_hours"), usual("hrv"), usual("resting_hr")
        score = latest["readiness"]
        health = {
            "asOf": latest["date"],
            "readiness": {"score": round(score, 1), "max": 10,
                          "level": "Ready" if score >= 7 else "Steady" if score >= 5 else "Take it easy"},
            "vitals": [
                {"label": "Sleep", "value": _hm(latest["sleep_hours"]),
                 "note": f"{_signed((latest['sleep_hours'] - sleep_avg) * 60, 0)}m vs avg" if sleep_avg else ""},
                {"label": "HRV", "value": f"{latest['hrv']:.0f} ms", "note": f"avg {hrv_avg:.0f}" if hrv_avg else ""},
                {"label": "Resting HR", "value": f"{latest['resting_hr']:.0f} bpm",
                 "note": ("normal" if abs(latest["resting_hr"] - rhr_avg) <= 2 else f"avg {rhr_avg:.0f}") if rhr_avg else ""},
            ],
            "mood": apple_mood_label(latest["mood"]) if latest["mood"] is not None else None,
        }

    events = calls("get_calendar", start_date=day.isoformat(), end_date=day.isoformat())["events"]
    free = calls("find_free_time", date=day.isoformat(), min_minutes=30)["free_slots"]
    forecast = calls("forecast_week", start_date=day.isoformat())
    found = patterns(calls, day)
    suggestions, walk_slot = _today_suggestions(calls, day, events, free, forecast, found)

    schedule = [{"start": e["start"], "end": e["end"], "title": e["title"], "kind": "event"}
                for e in events if e["start"] != "all day"]
    if walk_slot:
        schedule.append({"start": walk_slot[0], "end": walk_slot[1], "title": "Free · walk suggested", "kind": "suggested"})
    schedule.sort(key=lambda item: item["start"])

    return {
        "date": day.isoformat(),
        "dateLabel": f"{day:%a} · {day:%b} {day.day}".upper(),
        "health": health,
        "schedule": schedule,
        "freeSlots": free,
        "suggestions": suggestions,
        "headsUp": _heads_up(forecast, day),
        "toolCalls": calls.count,
    }


def _today_suggestions(calls, day, events, free, forecast, found):
    suggestions, walk_slot = [], None
    is_class_day = any(e["category"] == "class" for e in events)

    # 1. A walk in a free gap on class days, when class days really do have fewer steps.
    steps = calls("compute_correlation", x="class_day", y="steps", lag_days=0,
                  start_date=(day - timedelta(days=HISTORY_DAYS)).isoformat(),
                  end_date=(day - timedelta(days=1)).isoformat())
    gaps = [s for s in free if "10:00" <= s["start"] < "18:00" and s["minutes"] >= 30]
    if is_class_day and gaps and steps["strength"] in {"moderate", "strong"}:
        slot = max(gaps, key=lambda s: s["minutes"])
        finish = _clock(day, slot["start"], 30)
        walk_slot = (slot["start"], finish)
        groups = steps["groups"]
        title = "Take a walk in your free gap"
        suggestions.append(_suggestion(
            f"walk-{day}", title,
            f"On class days you average {groups['class_day_yes']['average_steps']:,.0f} steps vs "
            f"{groups['class_day_no']['average_steps']:,.0f} on other days.",
            f"n = {groups['class_day_yes']['days']} class days",
            {"text": f"{title} ({slot['start']}–{finish})", "metric": "steps", "direction": "up", "start_date": day.isoformat()},
            time=f"{slot['start']}–{finish}",
            ics=calls("make_ics_event", title="Walk outside", date=day.isoformat(), start_time=slot["start"],
                      duration_minutes=30, notes="Class days tend to have fewer steps.")))

    # 2. Protect tonight's sleep if tomorrow looks hard.
    tomorrow = next((d for d in forecast["days"] if d["date"] == (day + timedelta(days=1)).isoformat()), None)
    short = found.get("short_sleep")
    if tomorrow and short and (tomorrow["risk"] != "low" or tomorrow["busy"]):
        title = "Lights out by 23:00 tonight"
        risk = "" if tomorrow["risk"] == "low" else f" and is forecast {tomorrow['risk']} risk"
        suggestions.append(_suggestion(
            f"sleep-{day}", title,
            f"Tomorrow has {tomorrow['booked_hours']:g}h booked{risk}. "
            f"Mornings after under 6h of sleep, your readiness averages {short['yes']:g} vs {short['no']:g}.",
            f"n = {short['n']} short nights",
            {"text": title, "metric": "sleep_hours", "direction": "up", "start_date": tomorrow["date"]},
            time="22:45",
            ics=calls("make_ics_event", title="Wind down for bed", date=day.isoformat(), start_time="22:45",
                      duration_minutes=15, notes="Heavy day tomorrow.")))

    # 3. Keep a planned workout, when workouts are linked with better next-day mood.
    gym = next((e for e in events if e["category"] == "gym"), None)
    workout = found.get("workout_day")
    if gym and workout:
        title = "Keep today's gym session"
        suggestions.append(_suggestion(
            f"gym-{day}", title,
            f"The day after a workout your mood averages {workout['yes']:+.2f} vs {workout['no']:+.2f} otherwise.",
            f"n = {workout['n']} workout days",
            {"text": title, "metric": "mood", "direction": "up", "start_date": (day + timedelta(days=1)).isoformat()},
            time=f"{gym['start']}–{gym['end']}"))
    return suggestions, walk_slot


def _heads_up(forecast: dict, day: date) -> dict | None:
    ahead = [d for d in forecast["days"] if d["date"] > day.isoformat() and d["risk"] != "low"]
    if not ahead:
        return None
    worst = min(ahead, key=lambda d: d["readiness_vs_usual"] or 0)
    weekday = f"{date.fromisoformat(worst['date']):%A}"
    reason = ""
    if worst["after_late_event"]:
        reason = " after a late night"
    elif worst["after_busy_day"]:
        reason = " after a busy day"
    booked = f"{worst['booked_hours']:g}h booked" if worst["booked_hours"] >= BUSY_HOURS else "a heavy stretch"
    return {
        "day": weekday,
        "text": (f"{weekday} has {booked}{reason}. On days like that your readiness has averaged "
                 f"{worst['expected_readiness']:.1f}, vs your usual {forecast['usual']['readiness']:.1f}."),
    }
