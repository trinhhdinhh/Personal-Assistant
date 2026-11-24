"""Editing the schedule from the Week page (demo today = Monday 2026-11-16)."""
import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.test import Client

from agent.briefing import week_view
from data.models import CalendarEvent


@pytest.fixture
def seeded(db, settings):
    settings.DEMO_TODAY = "2026-11-16"
    call_command("seed_synthetic", stdout=StringIO())


def _send(method, url, body=None):
    client = Client()
    return getattr(client, method)(url, data=json.dumps(body or {}), content_type="application/json")


def _day(label):
    return next(d for d in week_view()["days"] if d["label"] == label)


def _reseed():
    call_command("seed_synthetic", stdout=StringIO())


def test_added_event_shows_on_the_calendar_and_changes_the_forecast(seeded):
    before = _day("Sat")["booked"]
    res = _send("post", "/api/events", {"title": "Hackathon", "date": "2026-11-21",
                                        "start": "09:00", "end": "17:00", "category": "study"})
    assert res.status_code == 201
    sat = _day("Sat")
    added = next(e for e in sat["events"] if e["title"] == "Hackathon")
    assert (added["time"], added["mine"], added["editable"]) == ("9:00 AM–5:00 PM", True, True)
    assert sat["booked"] == before + 8  # the forecast reads the new event too


def test_edit_moves_an_event_and_survives_the_daily_reseed(seeded):
    late = next(e for e in _day("Wed")["events"] if e["title"] == "Late study")
    res = _send("put", f"/api/events/{late['id']}", {"title": "Late study", "date": "2026-11-18",
                                                    "start": "15:00", "end": "16:30", "category": "study"})
    assert res.status_code == 200
    _reseed()
    titles = [(e["title"], e["start"]) for e in _day("Wed")["events"]]
    assert ("Late study", "15:00") in titles and ("Late study", "21:00") not in titles  # no duplicate


def test_deleted_seeded_event_stays_deleted_after_reseed(seeded):
    gym = next(e for e in _day("Thu")["events"] if e["title"] == "Gym")
    assert _send("delete", f"/api/events/{gym['id']}").status_code == 200
    _reseed()
    assert "Gym" not in [e["title"] for e in _day("Thu")["events"]]


def test_past_days_and_bad_input_are_refused(seeded):
    past = CalendarEvent.objects.filter(local_date="2026-11-13").first()
    assert _send("delete", f"/api/events/{past.pk}").status_code == 400
    assert _send("post", "/api/events", {"title": "x", "date": "2026-11-13", "start": "09:00", "end": "10:00"}).status_code == 400
    assert _send("post", "/api/events", {"title": "x", "date": "2026-11-17", "start": "10:00", "end": "09:00"}).status_code == 400
    assert _send("post", "/api/events", {"title": "", "date": "2026-11-17", "start": "09:00", "end": "10:00"}).status_code == 400
    assert _send("post", "/api/events", {"title": "x", "date": "2026-11-17", "start": "09:00", "end": "10:00",
                                         "category": "party"}).status_code == 400
    assert _send("delete", "/api/events/999999").status_code == 400
