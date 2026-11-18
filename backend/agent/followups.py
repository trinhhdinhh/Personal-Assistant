"""Follow-ups for the weekly report: did the suggestions the user took move their metric?

Each saved suggestion is checked with the same `evaluate_suggestion` tool the
agent uses, once its check date has passed. The report then shows the most
recent ones. Labels describe what the numbers did ("Improved"), never that
the suggestion caused it.
"""
from datetime import date

from agent import tools
from agent.models import Suggestion

MAX_SHOWN = 3

LABELS = {
    Suggestion.Status.IMPROVED: ("Improved", "success"),
    Suggestion.Status.NO_CHANGE: ("No clear change", "muted"),
    Suggestion.Status.WORSE: ("Got worse", "warning"),
    Suggestion.Status.NO_DATA: ("Not enough data", "muted"),
}

METRIC_NAMES = {
    "sleep_hours": "Sleep", "readiness": "Readiness", "hrv": "HRV", "resting_hr": "Resting HR",
    "mood": "Mood", "steps": "Steps", "active_energy": "Active energy",
    "workout_minutes": "Workout minutes", "booked_hours": "Booked hours",
}


def _show(metric: str, value: float | None) -> str:
    if value is None:
        return "–"
    if metric == "sleep_hours":
        return f"{value:.1f}h"
    if metric == "mood":
        return f"{value:+.2f}"
    if metric in {"steps", "active_energy"}:
        return f"{value:,.0f}"
    return f"{value:.1f}" if metric == "readiness" else f"{value:.0f}"


def follow_ups(up_to: date) -> list[dict]:
    """Suggestions whose check window ends on or before `up_to`, checked and newest first,
    then any still waiting. At most MAX_SHOWN."""
    tools.evaluate_suggestion()  # checks every pending suggestion that is due (by today's date)

    checked = Suggestion.objects.exclude(status=Suggestion.Status.PENDING).filter(check_on__lte=up_to)
    waiting = Suggestion.objects.filter(status=Suggestion.Status.PENDING).order_by("check_on")
    shown = [*checked.order_by("-check_on")[:MAX_SHOWN], *waiting[:MAX_SHOWN]][:MAX_SHOWN]
    return [_card(s) for s in shown]


def _card(s: Suggestion) -> dict:
    name = METRIC_NAMES.get(s.metric, s.metric)
    if s.status == Suggestion.Status.PENDING:
        return {"id": s.pk, "suggestion": s.text, "result": f"Checking {s.check_on:%b} {s.check_on.day}",
                "tone": "primary", "detail": f"{name} before: {_show(s.metric, s.baseline)} · n = {s.baseline_days}"}

    result, tone = LABELS[s.status]
    return {
        "id": s.pk,
        "suggestion": s.text,
        "result": result,
        "tone": tone,
        "detail": f"{name} {_show(s.metric, s.baseline)} → {_show(s.metric, s.result)} · n = {s.result_days} days after",
    }
