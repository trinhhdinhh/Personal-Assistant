"""Week and Today pages, built from the synthetic data (demo today = Monday 2026-11-16)."""
from io import StringIO

import pytest
from django.core.management import call_command
from django.test import Client

from agent.briefing import brief_view, week_view
from agent.models import Suggestion


@pytest.fixture
def seeded(db, settings):
    settings.DEMO_TODAY = "2026-11-16"
    call_command("seed_synthetic", stdout=StringIO())


# ---------- Week ----------

def test_week_flags_thursday_and_explains_why(seeded):
    week = week_view()
    days = {d["label"]: d for d in week["days"]}
    assert week["label"] == "NOV 16 – 22"
    assert days["Mon"]["today"] and days["Thu"]["risk"] == "High" and days["Sat"]["risk"] == "Low"
    assert days["Thu"]["note"] == "8.25h booked after a late Wed"
    assert {f["cause"] for f in week["factors"]} >= {"7h+ booked", "Event ends 9:30pm+"}
    assert next(f for f in week["factors"] if f["cause"] == "Sleep under 6h")["early"]  # only 11 short nights


def test_week_adjustments_fit_real_gaps_and_come_with_files(seeded):
    adjustments = {a["id"]: a for a in week_view()["adjustments"]}
    move = adjustments["move-2026-11-18"]
    assert move["time"] == "14:45–16:15"  # Wed's first afternoon gap, well before 9:30pm
    assert "BEGIN:VEVENT" in move["ics"]["ics"]
    assert move["track"] == {"text": move["title"], "metric": "sleep_hours", "direction": "up", "start_date": "2026-11-19"}
    assert adjustments["walk-2026-11-19"]["time"] == "12:15–12:35"


def test_pages_save_nothing_on_load(seeded):
    week_view()
    brief_view()
    assert Suggestion.objects.count() == 0


# ---------- Today ----------

def test_brief_uses_latest_health_day_and_todays_calendar(seeded):
    brief = brief_view()
    assert brief["dateLabel"] == "MON · NOV 16"
    assert brief["health"]["asOf"] == "2026-11-15"  # today's health data hasn't arrived yet
    titles = [item["title"] for item in brief["schedule"]]
    assert titles[0] == "CS 4100 Lecture" and "Free · walk suggested" in titles
    assert brief["headsUp"]["day"] == "Thursday"


def test_brief_suggestions_quote_their_pattern(seeded):
    suggestions = {s["id"]: s for s in brief_view()["suggestions"]}
    walk = suggestions["walk-2026-11-16"]
    assert walk["time"] == "14:45–15:15" and "class days" in walk["why"] and walk["ics"]
    assert suggestions["gym-2026-11-16"]["ics"] is None  # already on the calendar


# ---------- endpoints ----------

def test_forecast_and_brief_endpoints(seeded):
    client = Client()
    assert client.get("/api/forecast").json()["days"][0]["iso"] == "2026-11-16"
    assert client.get("/api/brief?date=2026-11-17").json()["date"] == "2026-11-17"
    assert client.get("/api/brief?date=soon").status_code == 400


def test_adding_a_suggestion_saves_it_once(seeded):
    client = Client()
    body = {"text": "Take a walk", "metric": "steps", "direction": "up", "start_date": "2026-11-16"}
    first = client.post("/api/suggestions", body, content_type="application/json")
    again = client.post("/api/suggestions", body, content_type="application/json")
    assert first.status_code == 201 and first.json()["new"]
    assert again.json() == {"suggestion_id": first.json()["suggestion_id"], "check_on": "2026-11-23", "new": False}
    assert Suggestion.objects.count() == 1


def test_bad_suggestion_is_rejected(seeded):
    response = Client().post("/api/suggestions", {"text": "x", "metric": "vibes", "direction": "up",
                                                  "start_date": "2026-11-16"}, content_type="application/json")
    assert response.status_code == 400 and "metric" in response.json()["error"]
