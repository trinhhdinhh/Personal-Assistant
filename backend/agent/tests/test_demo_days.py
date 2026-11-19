"""The demo builds its synthetic data around the real date, so it must work on any day of the week.

The tests and the eval use Monday Nov 16; these check other days still show the planted
patterns, a forecast and follow-ups, and that run_eval leaves the demo data alone.
"""
from datetime import date, timedelta
from io import StringIO

import pytest
from django.core.management import call_command

from agent import llm, tools
from agent.models import Suggestion
from agent.tests.test_loop import FakeClient, reply, text
from data import synthetic
from data.models import SleepSession
from data.report import last_full_week, weekly_report

PATTERNS = [  # (condition, metric, lag, expected sign)
    ("busy_day", "mood", 1, -1), ("busy_day", "readiness", 1, -1), ("late_event", "sleep_hours", 1, -1),
    ("short_sleep", "readiness", 0, -1), ("workout_day", "mood", 1, 1), ("class_day", "steps", 0, -1),
]


def seed_for(settings, day: str):
    settings.DEMO_TODAY = day
    call_command("seed_synthetic", stdout=StringIO())
    call_command("seed_demo_suggestions", stdout=StringIO())
    return date.fromisoformat(day)


@pytest.mark.parametrize("day", ["2026-11-19", "2026-11-22"])  # a Thursday and a Sunday
def test_patterns_forecast_and_follow_ups_on_other_days(db, settings, day):
    today = seed_for(settings, day)
    start, end = synthetic.FIRST_DAY.isoformat(), (today - timedelta(days=1)).isoformat()
    for x, y, lag, sign in PATTERNS:
        result = tools.compute_correlation(x, y, start, end, lag)
        assert result["strength"] in {"moderate", "strong"} and result["r"] * sign > 0, (x, y)
    assert tools.compute_correlation("steps", "hrv", start, end)["strength"] in {"none", "weak"}

    forecast = tools.forecast_week()
    assert forecast["days"][0]["date"] == day and len(forecast["days"]) == 7
    assert len(weekly_report(last_full_week())["followUps"]) == 3


def test_demo_suggestions_move_with_today(db, settings):
    seed_for(settings, "2026-11-16")
    assert sorted(str(s.start_date) for s in Suggestion.objects.all()) == ["2026-11-02", "2026-11-03", "2026-11-06"]
    seed_for(settings, "2026-11-30")
    assert sorted(str(s.start_date) for s in Suggestion.objects.all()) == ["2026-11-16", "2026-11-17", "2026-11-20"]


def test_run_eval_leaves_the_demo_data_alone(transactional_db, settings, monkeypatch):
    seed_for(settings, "2026-12-03")
    monkeypatch.setattr(llm, "get_client", lambda: FakeClient([reply(text("Hi."))]))
    call_command("run_eval", only=[1], stdout=StringIO())
    assert SleepSession.objects.order_by("-local_date").first().local_date == date(2026, 12, 2)
