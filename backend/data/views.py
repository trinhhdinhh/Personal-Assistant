from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

def report(request):
    return JsonResponse({"todo": "report"})

def forecast(request):
    return JsonResponse({"todo": "forecast"})

def brief(request):
    return JsonResponse({"todo": "brief"})

@csrf_exempt
@require_POST
def chat(request):
    return JsonResponse({"todo": "chat"})
