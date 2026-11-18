"""One table per data source.

Every record keeps:
- `source`: where it came from (e.g. "apple_health", "icloud", "synthetic")
- `occurred_at`: when it happened, timezone-aware, stored in UTC
- `local_date`: the calendar day in the user's timezone, derived on save
- `raw`: the original payload, never discarded

Bulk inserts skip `save()`, so importers must set `local_date` themselves
using `data.timeutils.to_local_date`.
"""
from datetime import datetime

from django.db import models

from data.timeutils import to_local_date


class SourceRecord(models.Model):
    source = models.CharField(max_length=50)
    occurred_at = models.DateTimeField()
    local_date = models.DateField(db_index=True, editable=False)
    raw = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    def local_date_moment(self) -> datetime:
        """The moment whose local date this record belongs to. Override per model if needed."""
        return self.occurred_at

    def save(self, *args, **kwargs) -> None:
        self.local_date = to_local_date(self.local_date_moment())
        super().save(*args, **kwargs)


class HealthSample(SourceRecord):
    """A single numeric measurement, e.g. steps, heart rate, active energy."""

    metric = models.CharField(max_length=100)  # e.g. "step_count", "heart_rate"
    value = models.FloatField()
    unit = models.CharField(max_length=30, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["metric", "local_date"])]

    def __str__(self) -> str:
        return f"{self.metric}={self.value}{self.unit} @ {self.occurred_at:%Y-%m-%d %H:%M}"


class SleepSession(SourceRecord):
    """One night of sleep. `occurred_at` is bedtime, `end_at` is wake time.

    `local_date` is the WAKE-UP day, so "sleep before Tuesday" lines up with
    Tuesday's check-in.
    """

    end_at = models.DateTimeField()
    asleep_minutes = models.PositiveIntegerField()
    in_bed_minutes = models.PositiveIntegerField(null=True, blank=True)

    def local_date_moment(self) -> datetime:
        return self.end_at

    def __str__(self) -> str:
        return f"Sleep {self.local_date}: {self.asleep_minutes / 60:.1f}h"


class EventCategory(models.TextChoices):
    CLASS = "class"
    WORK = "work"
    STUDY = "study"
    GYM = "gym"
    SOCIAL = "social"
    OTHER = "other"


class CalendarEvent(SourceRecord):
    """A calendar event. `occurred_at` is the start time."""

    Category = EventCategory

    uid = models.CharField(max_length=255, unique=True)  # CalDAV UID, used to dedupe syncs
    title = models.CharField(max_length=500)
    end_at = models.DateTimeField()
    all_day = models.BooleanField(default=False)
    category = models.CharField(max_length=10, choices=EventCategory.choices, default=EventCategory.OTHER)
    calendar_name = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=500, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(category__in=EventCategory.values),
                name="calendarevent_valid_category",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.category}) @ {self.occurred_at:%Y-%m-%d %H:%M}"
