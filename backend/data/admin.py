from django.contrib import admin

from data.models import CalendarEvent, HealthSample, MoodEntry, SleepSession, Suggestion, Workout


@admin.register(HealthSample)
class HealthSampleAdmin(admin.ModelAdmin):
    list_display = ("metric", "value", "unit", "local_date", "source")
    list_filter = ("metric", "source")


@admin.register(SleepSession)
class SleepSessionAdmin(admin.ModelAdmin):
    list_display = ("local_date", "asleep_minutes", "occurred_at", "end_at", "source")


@admin.register(Workout)
class WorkoutAdmin(admin.ModelAdmin):
    list_display = ("activity", "duration_minutes", "local_date", "source")
    list_filter = ("activity", "source")


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "occurred_at", "end_at", "source")
    list_filter = ("category", "source")


@admin.register(MoodEntry)
class MoodEntryAdmin(admin.ModelAdmin):
    list_display = ("local_date", "kind", "valence", "source")
    list_filter = ("kind", "source")


@admin.register(Suggestion)
class SuggestionAdmin(admin.ModelAdmin):
    list_display = ("text", "metric", "start_date", "check_on", "outcome")
    list_filter = ("outcome", "metric")
