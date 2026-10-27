from django.contrib import admin

from data.models import CalendarEvent, CheckIn, HealthSample, Note, SleepSession, Task


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


@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    list_display = ("local_date", "mood", "energy", "focus", "source")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "task_type", "status", "estimated_minutes", "actual_minutes")
    list_filter = ("status", "task_type")


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("__str__", "local_date", "source")
    exclude = ("embedding",)
