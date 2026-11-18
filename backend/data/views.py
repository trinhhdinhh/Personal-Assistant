from datetime import date

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

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


def forecast(request):
    return JsonResponse({"todo": "forecast"})


def brief(request):
    return JsonResponse({"todo": "brief"})


@csrf_exempt
@require_POST
def chat(request):
    return JsonResponse({"todo": "chat"})
