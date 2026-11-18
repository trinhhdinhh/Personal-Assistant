"""POST /api/chat: ask the agent a question.

Request:  {"question": "...", "history": [{"role": "user" | "assistant", "content": "..."}]}
Response: the answer, the steps the agent took, the answer checks, and any
          calendar files it made. Full tool results stay on the server.

A blocked answer is never sent: the user gets the "couldn't back it up"
message and the failed checks instead.
"""
import json
import logging
import time

from datetime import date

from django.core.exceptions import ImproperlyConfigured
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from agent import tools
from agent.briefing import brief_view, week_view
from agent.loop import AgentRun, run_agent
from agent.models import Suggestion

logger = logging.getLogger(__name__)

MAX_QUESTION = 1000   # characters
MAX_HISTORY = 10      # earlier messages kept for follow-up questions


def _bad(message: str) -> JsonResponse:
    return JsonResponse({"error": message}, status=400)


def _history(raw) -> list[dict] | None:
    """Earlier turns as plain text. Returns None if the shape is wrong."""
    if raw is None:
        return []
    if not isinstance(raw, list):
        return None
    turns = []
    for item in raw[-MAX_HISTORY:]:
        if (not isinstance(item, dict) or item.get("role") not in {"user", "assistant"}
                or not isinstance(item.get("content"), str)):
            return None
        turns.append({"role": item["role"], "content": item["content"][:4000]})
    # The conversation must start with the user for the model to accept it.
    while turns and turns[0]["role"] != "user":
        turns.pop(0)
    return turns


def _public(run: AgentRun, seconds: float) -> dict:
    """What the browser gets: no raw tool results, no blocked answer."""
    files = [
        {"filename": s.result["filename"], "ics": s.result["ics"], "summary": s.result["summary"]}
        for s in run.steps if s.tool == "make_ics_event" and s.ok
    ]
    return {
        "answer": run.answer,
        "stop": run.stop,
        "steps": [{"tool": s.tool, "input": s.input, "ok": s.ok, "summary": s.summary, "ms": s.ms} for s in run.steps],
        "checks": run.checks,
        "retries": run.retries,
        "files": files,
        "model": run.model,
        "model_calls": run.model_calls,
        "tokens": {"input": run.input_tokens, "output": run.output_tokens},
        "seconds": round(seconds, 1),
    }


@csrf_exempt  # local JSON API called by the Next.js server; add login before hosting (see CLAUDE.md)
@require_POST
def chat(request):
    try:
        body = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return _bad("Body must be JSON.")
    if not isinstance(body, dict):
        return _bad("Body must be a JSON object.")

    question = body.get("question")
    if not isinstance(question, str) or not question.strip():
        return _bad("question is required.")
    if len(question) > MAX_QUESTION:
        return _bad(f"question must be under {MAX_QUESTION} characters.")
    history = _history(body.get("history"))
    if history is None:
        return _bad("history must be a list of {role: user|assistant, content: text}.")

    started = time.monotonic()
    try:
        run = run_agent(question.strip(), history)
    except ImproperlyConfigured as error:
        return JsonResponse({"error": str(error)}, status=503)
    except Exception:
        logger.exception("Agent run failed")
        return JsonResponse({"error": "The agent hit an internal error. Please try again."}, status=500)
    return JsonResponse(_public(run, time.monotonic() - started))


# ---------- Week and Today pages (no model calls) ----------

def _date_param(request, name: str):
    """A ?name=YYYY-MM-DD query value, None if absent. Raises ValueError if malformed."""
    value = request.GET.get(name)
    return date.fromisoformat(value) if value else None


@require_GET
def forecast(request):
    """GET /api/forecast?start=2026-11-16 → the Week page. Default start is today."""
    try:
        return JsonResponse(week_view(_date_param(request, "start")))
    except ValueError:
        return _bad("start must be a date like 2026-11-16.")


@require_GET
def brief(request):
    """GET /api/brief?date=2026-11-16 → the Today page. Default is today."""
    try:
        return JsonResponse(brief_view(_date_param(request, "date")))
    except ValueError:
        return _bad("date must be a date like 2026-11-16.")


@csrf_exempt  # local JSON API; add login before hosting (see CLAUDE.md)
@require_POST
def save_suggestion(request):
    """POST /api/suggestions: the user added a suggestion, so remember it for follow-up.

    Body: {"text", "metric", "direction", "start_date"}. Adding the same suggestion twice
    returns the one already saved.
    """
    try:
        body = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return _bad("Body must be JSON.")
    if not isinstance(body, dict):
        return _bad("Body must be a JSON object.")

    existing = Suggestion.objects.filter(text=body.get("text"), start_date=body.get("start_date")).first() \
        if isinstance(body.get("text"), str) and _is_date(body.get("start_date")) else None
    if existing:
        return JsonResponse({"suggestion_id": existing.pk, "check_on": existing.check_on.isoformat(), "new": False})
    try:
        saved = tools.save_suggestion(text=body.get("text"), metric=body.get("metric"),
                                      direction=body.get("direction"), start_date=body.get("start_date"))
    except (tools.ToolError, AttributeError) as error:
        return _bad(str(error) or "text, metric, direction and start_date are required.")
    return JsonResponse({**saved, "new": True}, status=201)


def _is_date(value) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except (TypeError, ValueError):
        return False
