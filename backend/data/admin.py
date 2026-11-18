from django.contrib import admin

from data.models import CalendarEvent, HealthSample, SleepSession


@admin.register(HealthSample)
class HealthSampleAdmin(admin.ModelAdmin):
    list_display = ("metric", "value", "unit", "local_date", "source")
    list_filter = ("metric", "source")


@admin.register(SleepSession)
class SleepSessionAdmin(admin.ModelAdmin):
    list_display = ("local_date", "asleep_minutes", "occurred_at", "end_at", "source")


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "occurred_at", "end_at", "source")
    list_filter = ("category", "source")
