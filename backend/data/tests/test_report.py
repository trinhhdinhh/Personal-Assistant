"""Weekly report: numbers must match the daily summaries, and the JSON must fit the Report page."""
from datetime import date
from io import StringIO
from statistics import mean

import pytest
from django.core.management import call_command
from django.test import Client

from data.report import last_full_week, mood_label, weekly_report
from data.summaries import daily_summaries

THIS_WEEK, LAST_WEEK = date(2026, 11, 9), date(2026, 11, 2)
PAGE_KEYS = {"label", "stats", "days", "sleepThis", "sleepLast", "readinessThis",
             "moodThis", "timeUse", "changes", "followUps"}


@pytest.fixture
def seeded(db):
    call_command("seed_synthetic", today="2026-11-16", stdout=StringIO())


@pytest.fixture
def report(seeded):
    return weekly_report(THIS_WEEK)


def _stat(report, label):
    return next(s for s in report["stats"] if s["label"] == label)


def _week(start):
    return daily_summaries(start, date.fromordinal(start.toordinal() + 6))


def test_shape_matches_the_report_page(report):
    assert set(report) == PAGE_KEYS
    assert report["label"] == "NOV 9 – 15 vs NOV 2 – 8"
    assert [s["label"] for s in report["stats"]] == [
        "Avg sleep", "Avg readiness", "Avg HRV", "Avg steps", "Workouts", "Pleasant days"]
    for key in ("days", "sleepThis", "sleepLast", "readinessThis", "moodThis"):
        assert len(report[key]) == 7


def test_any_date_picks_its_monday_to_sunday_week(seeded):
    assert weekly_report(date(2026, 11, 12)) == weekly_report(THIS_WEEK)


def test_stats_match_the_daily_summaries(report):
    this, last = _week(THIS_WEEK), _week(LAST_WEEK)
    readiness = round(mean(r["readiness"] for r in this), 1)
    steps = round(mean(r["steps"] for r in this))
    workouts = sum(1 for r in this if r["workout_minutes"])

    assert _stat(report, "Avg readiness")["value"] == str(readiness)
    assert _stat(report, "Avg steps")["value"] == f"{steps:,}"
    assert _stat(report, "Workouts")["value"] == str(workouts)
    workout_change = workouts - sum(1 for r in last if r["workout_minutes"])
    assert int(_stat(report, "Workouts")["delta"].replace("−", "-")) == workout_change  # the page uses a real minus sign
    assert report["sleepThis"] == [r["sleep_hours"] for r in this]
    assert report["sleepLast"] == [r["sleep_hours"] for r in last]


def test_deltas_add_up_on_screen(report):
    """The delta must equal the difference of the shown values, so the page never looks wrong."""
    last = weekly_report(LAST_WEEK)
    this_value = float(_stat(report, "Avg readiness")["value"])
    last_value = float(_stat(last, "Avg readiness")["value"])
    shown = _stat(report, "Avg readiness")["delta"].replace("−", "-")
    assert float(shown) == pytest.approx(this_value - last_value)


def test_tones_follow_direction(report):
    for stat in report["stats"]:
        expected = {"+": "success", "−": "warning", "0": "muted"}[stat["delta"][0]]
        assert stat["tone"] == expected


def test_time_use_adds_up_to_booked_hours(report):
    booked = sum(r["booked_hours"] for r in _week(THIS_WEEK))
    assert sum(t["hours"] for t in report["timeUse"]) == pytest.approx(booked, abs=0.3)
    hours = [t["hours"] for t in report["timeUse"]]
    assert hours == sorted(hours, reverse=True)


def test_changes_never_claim_a_cause(report):
    assert 1 <= len(report["changes"]) <= 2
    for change in report["changes"]:
        text = (change["title"] + change["body"]).lower()
        assert not any(word in text for word in ("because", "caused", "due to", "led to"))


def test_week_without_data_shows_unknowns(db):
    report = weekly_report(date(2025, 1, 6))
    for stat in report["stats"]:
        assert stat["delta"] == "n/a" and stat["tone"] == "muted"
    assert report["sleepThis"] == [None] * 7
    assert report["changes"][0]["title"] == "A steady week"


def test_mood_labels():
    assert [mood_label(v) for v in (0.5, 0.0, -0.5, None)] == ["pleasant", "neutral", "unpleasant", None]


# ---------- the endpoint ----------

def test_default_week_is_the_last_full_week(settings):
    settings.DEMO_TODAY = "2026-11-16"
    assert last_full_week() == THIS_WEEK
    settings.DEMO_TODAY = "2026-11-22"  # Sunday: the current week isn't over yet
    assert last_full_week() == THIS_WEEK


def test_endpoint_returns_the_report(seeded, settings):
    settings.DEMO_TODAY = "2026-11-16"
    response = Client().get("/api/report")
    assert response.status_code == 200
    assert response.json()["label"] == "NOV 9 – 15 vs NOV 2 – 8"
    assert Client().get("/api/report?week=2026-11-02").json()["label"] == "NOV 2 – 8 vs OCT 26 – NOV 1"


def test_endpoint_rejects_a_bad_week(db):
    assert Client().get("/api/report?week=last-tuesday").status_code == 400
    assert Client().post("/api/report").status_code == 405
