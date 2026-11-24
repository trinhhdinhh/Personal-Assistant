import json
from datetime import date

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from data import schedule

from data.report import last_full_week, weekly_report


@require_GET
def report(request):
    """Weekly report. ?week=2026-11-09 picks a week; default is the last full week."""
    week = request.GET.get("week")
    if week:
        try:
            start = date.fromisoformat(week)
        except ValueError:
            return JsonResponse({"error": "week must be a date like 2026-11-09"}, status=400)
    else:
        start = last_full_week()
    return JsonResponse(weekly_report(start))


# ---------- Editing the schedule from the Week page ----------

def _body(request) -> dict:
    try:
        body = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        raise schedule.ScheduleError("Body must be JSON.") from None
    if not isinstance(body, dict):
        raise schedule.ScheduleError("Body must be a JSON object.")
    return body


@csrf_exempt  # local JSON API; add login before hosting (see CLAUDE.md)
@require_POST
def add_event(request):
    """POST /api/events  {"title", "date": "2026-11-19", "start": "14:00", "end": "15:30", "category"}"""
    try:
        event = schedule.add_event(_body(request))
    except schedule.ScheduleError as error:
        return JsonResponse({"error": str(error)}, status=400)
    return JsonResponse({"id": event.pk}, status=201)


@csrf_exempt  # local JSON API; add login before hosting (see CLAUDE.md)
@require_http_methods(["PUT", "DELETE"])
def change_event(request, event_id: int):
    """PUT /api/events/<id> with the same body as POST edits it; DELETE removes it."""
    try:
        if request.method == "DELETE":
            schedule.remove_event(event_id)
            return JsonResponse({"deleted": event_id})
        event = schedule.edit_event(event_id, _body(request))
    except schedule.ScheduleError as error:
        return JsonResponse({"error": str(error)}, status=400)
    return JsonResponse({"id": event.pk})
