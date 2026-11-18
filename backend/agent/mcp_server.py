"""The MCP server behind the Claude connector (mounted at /mcp by config/asgi.py).

It only passes questions and answers through. The thinking is done by this
project's own agent (agent/loop.py), never by Claude's chat (CLAUDE.md):

- get_today_brief, get_week_forecast, get_weekly_report, get_recent_trends:
  read-only views built from daily summaries, the same data as the web pages.
- ask_agent: runs the custom agent read-only and returns its answer, the
  steps it took and the answer checks.

Nothing here writes: the agent runs with allow_writes=False, and calendar
files come back as text for you to add yourself. Every request needs an OAuth
token (agent/mcp_auth.py).
"""
import functools
import logging
import time
from datetime import date, timedelta
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import close_old_connections, connections
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError as McpToolError
from mcp.types import ToolAnnotations

from agent import tools
from agent.briefing import brief_view, week_view
from agent.loop import run_agent
from agent.mcp_auth import DjangoTokenVerifier
from agent.views import _history, _public
from data.report import last_full_week, weekly_report
from data.timeutils import today

logger = logging.getLogger(__name__)

SOURCE = "Life Agent (custom agent over your own data; every answer is checked before it is returned)"
READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False)
TREND_METRICS = ["sleep_hours", "readiness", "hrv", "resting_hr", "mood", "steps", "workout_minutes", "booked_hours"]

INSTRUCTIONS = (
    "Life Agent answers questions about the user's schedule and Apple Watch health data using their own "
    "agent. For any question that needs analysis, call ask_agent and show its answer as returned, with its "
    "steps and checks. Do not re-analyse the data, add numbers of your own, or describe links as causes. "
    "Use the get_* tools to show the daily brief, week forecast, weekly report or recent trends."
)


def build_server() -> MCPServer:
    server = MCPServer(
        name="Life Agent",
        instructions=INSTRUCTIONS,
        token_verifier=DjangoTokenVerifier(),
        auth=AuthSettings(
            issuer_url=settings.PUBLIC_URL,
            resource_server_url=f"{settings.PUBLIC_URL}/mcp",
            required_scopes=[settings.MCP_SCOPE],
            validate_token_resource=False,  # DjangoTokenVerifier only accepts tokens issued for this server
        ),
    )

    @server.tool(annotations=READ_ONLY, structured_output=True)
    @_db_call
    def get_today_brief() -> dict[str, Any]:
        """Today's brief: latest readiness and vitals, today's schedule with free gaps, up to three
        suggestions (each with the pattern it rests on and a calendar file), and a heads-up about the
        hardest day ahead. Use for "what's my day like?" or "today's brief"."""
        return {"source": SOURCE, **brief_view()}

    @server.tool(annotations=READ_ONLY, structured_output=True)
    @_db_call
    def get_week_forecast(start_date: str | None = None) -> dict[str, Any]:
        """How each of the next 7 days will probably go (predicted readiness, risk, reason), the patterns
        behind the prediction with their sample sizes, and suggested changes. Use for "how's my week
        looking?" when the user wants the forecast itself. start_date: YYYY-MM-DD, default today."""
        return {"source": SOURCE, **week_view(_date(start_date, "start_date"))}

    @server.tool(annotations=READ_ONLY, structured_output=True)
    @_db_call
    def get_weekly_report(week_start: str | None = None) -> dict[str, Any]:
        """The weekly report: sleep, readiness, HRV, steps, workouts and mood vs the week before, where the
        time went, the biggest changes, and follow-ups on past suggestions. week_start: any date in the
        week (YYYY-MM-DD); default is the last full week."""
        start = _date(week_start, "week_start") or last_full_week()
        return {"source": SOURCE, **weekly_report(start)}

    @server.tool(annotations=READ_ONLY, structured_output=True)
    @_db_call
    def get_recent_trends(days: int = 14) -> dict[str, Any]:
        """Average daily numbers for the last `days` days (7-60) compared with the same number of days
        before that. Daily summaries only."""
        if not 7 <= days <= 60:
            raise ValueError("days must be between 7 and 60")
        end = today() - timedelta(days=1)
        recent_start = end - timedelta(days=days - 1)
        before_end = recent_start - timedelta(days=1)
        before_start = before_end - timedelta(days=days - 1)
        recent = tools.query_data(recent_start.isoformat(), end.isoformat(), TREND_METRICS)
        before = tools.query_data(before_start.isoformat(), before_end.isoformat(), TREND_METRICS)
        return {
            "source": SOURCE,
            "recent": {"start": recent_start.isoformat(), "end": end.isoformat(),
                       "averages": recent["averages"], "days_with_data": recent["days_with_data"]},
            "before": {"start": before_start.isoformat(), "end": before_end.isoformat(),
                       "averages": before["averages"], "days_with_data": before["days_with_data"]},
            "note": "Averages of daily summaries. A difference between two periods is not a lasting pattern.",
        }

    @server.tool(annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=True),
                 structured_output=True)
    @_db_call
    def ask_agent(question: str, history: list[dict] | None = None) -> dict[str, Any]:
        """Ask the user's own Life Agent a question about their schedule, sleep, recovery, mood or activity,
        e.g. "why was last week rough?" or "do busy days affect my mood?". The agent plans, uses its tools
        on the user's data, checks its answer, and returns the answer, the steps it took and the checks.
        Show the answer as returned; do not add numbers or reasoning of your own. history: earlier turns as
        [{"role": "user"|"assistant", "content": "..."}] for follow-up questions."""
        question = (question or "").strip()
        if not question or len(question) > 1000:
            raise ValueError("question must be 1-1000 characters")
        turns = _history(history)
        if turns is None:
            raise ValueError("history must be a list of {role: user|assistant, content: text}")
        if not _take_daily_ask():
            raise ValueError(f"The daily limit of {settings.MCP_DAILY_ASK_LIMIT} questions is used up. Try again tomorrow.")

        started = time.monotonic()
        try:
            run = run_agent(question, turns, max_steps=settings.MCP_AGENT_MAX_STEPS, allow_writes=False)
        except ImproperlyConfigured:
            raise ValueError("The agent's model key is not set on the server.") from None
        logger.info("mcp ask_agent stop=%s steps=%s", run.stop, len(run.steps))  # never the question or answer
        return {"source": SOURCE, **_public(run, time.monotonic() - started)}

    return server


def _db_call(fn):
    """Tools run in worker threads, outside Django's request cycle, so start with a usable
    database connection and close this thread's connections afterwards. Expected failures
    are passed to Claude with their message."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        close_old_connections()
        try:
            return fn(*args, **kwargs)
        except (ValueError, tools.ToolError) as error:
            # A failure we expected (bad input, daily limit): Claude sees this message.
            # Anything else is a crash, and the SDK shows only a generic error.
            raise McpToolError(str(error)) from error
        finally:
            connections.close_all()  # this worker thread's connections only
    return wrapper


def _date(value: str | None, name: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{name} must be a date like 2026-11-16") from None


def _take_daily_ask() -> bool:
    """Count one ask_agent call against today's limit. False once the limit is reached."""
    key = f"mcp-asks-{today().isoformat()}"
    cache.add(key, 0, timeout=60 * 60 * 26)
    return cache.incr(key) <= settings.MCP_DAILY_ASK_LIMIT
