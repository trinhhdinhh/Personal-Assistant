"""The agent's tools must find the planted patterns in the synthetic data, and nothing stronger.

Synthetic history: 2026-09-17 to 2026-11-15. Demo today: Monday 2026-11-16.
"""
import json
from io import StringIO

import pytest
from django.core.management import call_command

from agent import tools
from agent.models import Suggestion
from agent.registry import TOOL_DEFINITIONS, TOOL_FUNCTIONS, run_tool
from agent.tools import ToolError

START, END = "2026-09-17", "2026-11-15"


@pytest.fixture
def seeded(db, settings):
    settings.DEMO_TODAY = "2026-11-16"
    call_command("seed_synthetic", stdout=StringIO())


def corr(x, y, lag=0, start=START, end=END):
    return tools.compute_correlation(x, y, start, end, lag)


# ---------- the planted patterns ----------

@pytest.mark.parametrize("x, y, lag, sign", [
    ("busy_day", "mood", 1, -1),          # 1. busy day -> lower mood next day
    ("busy_day", "readiness", 1, -1),     # 2. busy day -> lower readiness next day
    ("late_event", "sleep_hours", 1, -1),  # 3. late event -> less sleep that night
    ("short_sleep", "readiness", 0, -1),  # 4. short sleep -> lower readiness that morning
    ("workout_day", "mood", 1, 1),        # 5. workout -> better mood next day
    ("class_day", "steps", 0, -1),        # 6. class day -> fewer steps
])
def test_finds_planted_patterns(seeded, x, y, lag, sign):
    result = corr(x, y, lag)
    assert result["strength"] in {"moderate", "strong"}
    assert result["r"] * sign > 0
    assert result["groups"]["difference_yes_minus_no"] * sign > 0
    assert tools.NOT_CAUSATION in result["notes"]


def test_control_pair_is_not_a_pattern(seeded):
    assert corr("steps", "hrv")["strength"] in {"none", "weak"}


def test_short_ranges_are_flagged_as_early(seeded):
    result = corr("busy_day", "mood", 1, start="2026-11-01", end="2026-11-10")
    assert result["paired_days"] < tools.MIN_DAYS
    assert any("early" in note for note in result["notes"])


# ---------- data tools ----------

def test_query_data_returns_only_requested_daily_numbers(seeded):
    result = tools.query_data("2026-11-09", "2026-11-15", ["sleep_hours", "busy_day"])
    assert len(result["days"]) == 7
    assert set(result["days"][0]) == {"date", "sleep_hours", "busy_day"}
    assert result["days_with_data"]["sleep_hours"] == 7


def test_get_calendar_lists_events_with_local_times(seeded):
    result = tools.get_calendar("2026-11-19", "2026-11-19")
    assert [(e["start"], e["title"]) for e in result["events"]][:2] == [("07:00", "Gym"), ("08:30", "Study block")]
    assert result["booked_hours_by_day"]["2026-11-19"] == 8.25


def test_compare_periods(seeded):
    result = tools.compare_periods("sleep_hours", "2026-11-09", "2026-11-15", "2026-11-02", "2026-11-08")
    assert result["difference"] == round(result["period_a"]["average"] - result["period_b"]["average"], 2)
    assert result["notes"]  # 7 days each is under 14, so it is flagged


# ---------- looking ahead ----------

def test_forecast_flags_thursday_after_a_late_busy_wednesday(seeded):
    days = {d["weekday"]: d for d in tools.forecast_week()["days"]}
    assert list(days) == ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    assert days["Thu"]["risk"] == "high"
    assert days["Thu"]["expected_readiness"] < days["Mon"]["expected_readiness"]
    assert days["Sat"]["risk"] == "low"


def test_find_free_time_on_thursday(seeded):
    slots = tools.find_free_time("2026-11-19")["free_slots"]
    assert slots == [
        {"start": "08:00", "end": "08:30", "minutes": 30},
        {"start": "10:30", "end": "11:00", "minutes": 30},
        {"start": "12:15", "end": "16:00", "minutes": 225},
        {"start": "20:00", "end": "22:00", "minutes": 120},
    ]


def test_make_ics_event(db, settings):
    result = tools.make_ics_event("Walk, outside", "2026-11-19", "12:30", 20, "Your only long gap; busy day")
    ics = result["ics"]
    assert "BEGIN:VEVENT" in ics and "SUMMARY:Walk\\, outside" in ics
    assert "DTSTART:20261119T183000Z" in ics  # 12:30 Chicago = 18:30 UTC
    assert all(len(line) <= 75 for line in ics.split("\r\n"))
    assert result["filename"].endswith(".ics")


# ---------- following up ----------

def test_save_then_evaluate_suggestion(seeded):
    saved = tools.save_suggestion("Stop studying after 9pm", "sleep_hours", "up", "2026-11-02")
    assert saved["baseline_days"] == 14 and saved["check_on"] == "2026-11-09"

    result = tools.evaluate_suggestion(saved["suggestion_id"])["results"][0]
    assert result["status"] in {"improved", "no_change", "worse"}
    assert result["after"]["days"] == 7
    assert Suggestion.objects.get(pk=saved["suggestion_id"]).evaluated_at is not None


def test_evaluate_is_too_early_before_check_date(seeded):
    saved = tools.save_suggestion("Take a walk at lunch", "steps", "up", "2026-11-14")
    result = tools.evaluate_suggestion(saved["suggestion_id"])["results"][0]
    assert result["status"] == "too_early"
    assert tools.evaluate_suggestion()["still_waiting"][0]["suggestion_id"] == saved["suggestion_id"]


def test_unknown_suggestion_is_a_tool_error(seeded):
    with pytest.raises(ToolError):
        tools.evaluate_suggestion(999)


# ---------- registry ----------

def test_every_tool_has_a_strict_documented_schema():
    assert len(TOOL_DEFINITIONS) == 9
    for tool in TOOL_DEFINITIONS:
        schema = tool["input_schema"]
        assert tool["strict"] is True and schema["additionalProperties"] is False
        assert len(tool["description"]) > 80
        assert all("description" in p or p.get("format") == "date" for p in schema["properties"].values())
        assert set(schema["required"]) <= set(schema["properties"])
        assert callable(TOOL_FUNCTIONS[tool["name"]])


def test_run_tool_returns_json_or_a_readable_error(seeded):
    text, is_error = run_tool("find_free_time", {"date": "2026-11-19"})
    assert not is_error and json.loads(text)["weekday"] == "Thu"

    text, is_error = run_tool("query_data", {"start_date": "yesterday", "end_date": END, "metrics": ["mood"]})
    assert is_error and "2026-11-09" in text

    text, is_error = run_tool("delete_calendar", {})
    assert is_error and "Unknown tool" in text
