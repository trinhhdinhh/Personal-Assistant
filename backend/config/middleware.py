"""Turns the local JSON API off on the public server.

/api/... has no login (it serves the local Next.js pages), so when API_ENABLED
is off every /api/ path answers 404. Claude reaches the data through /mcp,
which requires an OAuth token.
"""
from django.conf import settings
from django.http import JsonResponse


def api_gate(get_response):
    def middleware(request):
        if not settings.API_ENABLED and request.path.startswith("/api/"):
            return JsonResponse({"error": "Not found."}, status=404)
        return get_response(request)
    return middleware
