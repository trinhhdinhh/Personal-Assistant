"""Tool definitions the model sees, and the dispatcher the agent loop calls.

Best practices followed here:
- Each description says WHEN to call the tool, not just what it does.
- Every parameter has a description; fixed choices use `enum`.
- `strict: True` makes the API guarantee inputs match the schema
  (requires `additionalProperties: False`). Optional parameters are left out
  of `required` and get defaults in Python.
- Tools never crash the loop: `run_tool` turns any failure into an error
  result (`is_error=True`) the model can read and recover from.
"""
import json
import logging
from datetime import date, datetime
from typing import Callable

from agent import tools
from agent.tools import CONDITIONS, METRICS, ToolError

logger = logging.getLogger(__name__)

DATE = {"type": "string", "format": "date", "description": "A date like 2026-11-09."}

METRIC_HELP = (
    "Daily metrics: sleep_hours (the night that ENDED that morning), readiness (0-10), "
    "hrv (ms), resting_hr (bpm), mood (-1 very unpleasant to 1 very pleasant), steps, "
    "active_energy (kcal), workout_minutes, booked_hours (hours of calendar events). "
)
CONDITION_HELP = (
    "Yes/no conditions: busy_day (7h+ booked), late_event (an event ends 9:30pm or later), "
    "short_sleep (under 6h), workout_day, class_day."
)


def _schema(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}


TOOL_DEFINITIONS = [
    {
        "name": "query_data",
        "description": (
            "Get the user's daily numbers for a date range: one row per day. Call this when you need "
            "actual values to answer a question (e.g. 'how did I sleep last week?') or to check a claim "
            "before stating it. Returns daily values, days with data, and averages. Max 120 days. "
            + METRIC_HELP + CONDITION_HELP
        ),
        "input_schema": _schema({
            "start_date": DATE,
            "end_date": DATE,
            "metrics": {"type": "array", "items": {"type": "string", "enum": METRICS + CONDITIONS},
                        "description": "Which metrics or conditions to return. Ask only for what you need."},
        }, ["start_date", "end_date", "metrics"]),
    },
    {
        "name": "get_calendar",
        "description": (
            "Get the user's calendar events (date, start, end, hours, title, category) for a date range, "
            "plus booked hours per day. Call this when you need to know WHAT is scheduled, e.g. to explain "
            "why a day was heavy or to look at an upcoming week. Max 31 days. For open gaps use find_free_time."
        ),
        "input_schema": _schema({"start_date": DATE, "end_date": DATE}, ["start_date", "end_date"]),
    },
    {
        "name": "compare_periods",
        "description": (
            "Compare one metric's average between two date ranges, e.g. this week vs last week. Call this "
            "for questions like 'was last week better?' or 'how has my sleep changed?'. Returns both averages, "
            "the difference and percent change. " + METRIC_HELP
        ),
        "input_schema": _schema({
            "metric": {"type": "string", "enum": METRICS, "description": "The metric to compare."},
            "period_a_start": {**DATE, "description": "Start of the period of interest (usually the more recent one)."},
            "period_a_end": {**DATE, "description": "End of period A."},
            "period_b_start": {**DATE, "description": "Start of the period to compare against."},
            "period_b_end": {**DATE, "description": "End of period B."},
        }, ["metric", "period_a_start", "period_a_end", "period_b_start", "period_b_end"]),
    },
    {
        "name": "compute_correlation",
        "description": (
            "Check whether two things move together across days, e.g. whether busy days are followed by "
            "lower mood. Call this whenever the user asks if one thing affects another, or before you state "
            "any pattern. Use lag_days to look at later days: lag_days=1 compares x on a day with y the NEXT "
            "day. Because sleep_hours is the night ending that morning, 'late event -> sleep that night' is "
            "lag_days=1 and 'short sleep -> readiness that morning' is lag_days=0. For a yes/no x it also "
            "returns the average y on yes-days vs no-days, which is the easiest result to explain. "
            "Results show association only, never cause. " + METRIC_HELP + CONDITION_HELP
        ),
        "input_schema": _schema({
            "x": {"type": "string", "enum": METRICS + CONDITIONS, "description": "The possible influence."},
            "y": {"type": "string", "enum": METRICS, "description": "The outcome to check."},
            "start_date": {**DATE, "description": "First day of x to include. Use at least 28 days when possible."},
            "end_date": {**DATE, "description": "Last day of x to include."},
            "lag_days": {"type": "integer", "enum": [0, 1, 2, 3],
                         "description": "How many days after x to measure y. 0 = same day (default)."},
        }, ["x", "y", "start_date", "end_date"]),
    },
    {
        "name": "forecast_week",
        "description": (
            "Predict how each of the next 7 days will go (readiness, mood, sleep) by matching each day "
            "with past days that followed a similar day (busy or not, late event or not). Call this for "
            "'how is my week looking?', for warnings about rough days, or before suggesting schedule "
            "changes for the coming week. Returns a risk level (low/medium/high) and reasons per day."
        ),
        "input_schema": _schema({
            "start_date": {**DATE, "description": "First day to forecast. Defaults to today."},
        }, []),
    },
    {
        "name": "find_free_time",
        "description": (
            "Find open gaps in the user's calendar on one day. Call this before suggesting any activity at a "
            "specific time (a walk, a nap, a workout) so the suggestion fits a real gap."
        ),
        "input_schema": _schema({
            "date": DATE,
            "min_minutes": {"type": "integer", "description": "Shortest gap worth returning, 5-480. Default 30."},
            "day_start": {"type": "string", "description": "Earliest time to consider, 24-hour HH:MM. Default 08:00."},
            "day_end": {"type": "string", "description": "Latest time to consider, 24-hour HH:MM. Default 22:00."},
        }, ["date"]),
    },
    {
        "name": "make_ics_event",
        "description": (
            "Create a calendar file (.ics) for a suggested activity that the user can tap to add. Call this "
            "after find_free_time when you suggest something at a specific time. It does NOT add anything to "
            "the calendar; the user decides."
        ),
        "input_schema": _schema({
            "title": {"type": "string", "description": "Short event title, e.g. 'Walk outside'."},
            "date": DATE,
            "start_time": {"type": "string", "description": "Start time, 24-hour HH:MM."},
            "duration_minutes": {"type": "integer", "description": "Length in minutes, 5-480."},
            "notes": {"type": "string", "description": "Optional one-line reason shown in the event."},
        }, ["title", "date", "start_time", "duration_minutes"]),
    },
    {
        "name": "save_suggestion",
        "description": (
            "Record a suggestion you are giving the user so it can be checked later. Call this every time "
            "you make a concrete suggestion that should move one metric (e.g. 'stop studying past 10pm' -> "
            "sleep_hours up). Saves the metric's average over the 14 days before start_date as a baseline."
        ),
        "input_schema": _schema({
            "text": {"type": "string", "description": "The suggestion as shown to the user, one sentence."},
            "metric": {"type": "string", "enum": METRICS, "description": "The metric it should improve."},
            "direction": {"type": "string", "enum": ["up", "down"], "description": "Which way is better for this metric."},
            "start_date": {**DATE, "description": "First day the suggestion applies."},
            "check_after_days": {"type": "integer", "description": "Days to wait before checking, 3-28. Default 7."},
        }, ["text", "metric", "direction", "start_date"]),
    },
    {
        "name": "evaluate_suggestion",
        "description": (
            "Check whether past suggestions helped, by comparing the metric after the suggestion with its "
            "baseline. Call this for the weekly report, or when the user asks whether advice worked. "
            "Without suggestion_id it checks every suggestion that is due and lists the ones still waiting."
        ),
        "input_schema": _schema({
            "suggestion_id": {"type": "integer", "description": "One suggestion to check. Leave out to check all that are due."},
        }, []),
    },
]

for _tool in TOOL_DEFINITIONS:
    _tool["strict"] = True

TOOL_FUNCTIONS: dict[str, Callable[..., dict]] = {t["name"]: getattr(tools, t["name"]) for t in TOOL_DEFINITIONS}

# Tools that change stored data. Left out when the agent runs read-only (the Claude connector).
WRITE_TOOLS = {"save_suggestion"}


def tool_definitions(allow_writes: bool = True) -> list[dict]:
    """The tool list to send to the model, without write tools when `allow_writes` is False."""
    return [t for t in TOOL_DEFINITIONS if allow_writes or t["name"] not in WRITE_TOOLS]


def _json_default(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def run_tool(name: str, tool_input: dict, allowed: set[str] | None = None) -> tuple[str, bool]:
    """Run one tool call from the model. Returns (result text, is_error).

    The result text goes back to the model as the tool_result content. `allowed` limits
    which tools may run (a read-only run refuses write tools even if the model asks).
    """
    function = TOOL_FUNCTIONS.get(name)
    if function is None or (allowed is not None and name not in allowed):
        available = sorted(allowed if allowed is not None else TOOL_FUNCTIONS)
        return f"Unknown tool {name!r}. Available tools: {available}", True
    try:
        result = function(**tool_input)
    except ToolError as error:
        return str(error), True
    except TypeError as error:  # wrong or missing arguments
        return f"Bad arguments for {name}: {error}", True
    except Exception:
        logger.exception("Tool %s failed", name)
        return f"{name} failed with an internal error. Try different inputs or another tool.", True
    return json.dumps(result, default=_json_default), False
