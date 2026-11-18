from django.contrib import admin

from agent.models import Suggestion


@admin.register(Suggestion)
class SuggestionAdmin(admin.ModelAdmin):
    list_display = ("text", "metric", "direction", "start_date", "check_on", "status")
    list_filter = ("status", "metric")
