"""One table per data source.

Every record keeps:
- `source`: where it came from (e.g. "apple_health", "icloud", "shortcut", "synthetic")
- `occurred_at`: when it happened, timezone-aware, stored in UTC
- `local_date`: the calendar day in the user's timezone, derived on save
- `raw`: the original payload, never discarded

Bulk inserts skip `save()`, so importers must set `local_date` themselves
using `data.timeutils.to_local_date`.
"""
from datetime import datetime

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from pgvector.django import VectorField

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


def _score_field() -> models.PositiveSmallIntegerField:
    return models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])


class CheckIn(SourceRecord):
    """Daily self-report. One per local day; a resubmission updates the existing row."""

    mood = _score_field()
    energy = _score_field()
    focus = _score_field()
    note = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["local_date"], name="checkin_one_per_day"),
            *[
                models.CheckConstraint(
                    condition=models.Q(**{f"{f}__gte": 1, f"{f}__lte": 5}),
                    name=f"checkin_{f}_1_to_5",
                )
                for f in ("mood", "energy", "focus")
            ],
        ]

    def __str__(self) -> str:
        return f"CheckIn {self.local_date}: mood={self.mood} energy={self.energy} focus={self.focus}"


class Task(SourceRecord):
    """A to-do item. `occurred_at` is when it was created.

    `estimated_minutes` vs `actual_minutes` is what the Learn loop uses to
    correct duration estimates per `task_type`.
    """

    class Status(models.TextChoices):
        TODO = "todo"
        DONE = "done"
        DROPPED = "dropped"

    title = models.CharField(max_length=500)
    task_type = models.CharField(max_length=50, blank=True)  # e.g. "reading", "problem_set"
    estimated_minutes = models.PositiveIntegerField(null=True, blank=True)
    actual_minutes = models.PositiveIntegerField(null=True, blank=True)
    deadline = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.TODO)

    def __str__(self) -> str:
        return f"{self.title} [{self.status}]"


class Note(SourceRecord):
    """Free-text note (journal entry, check-in note, etc.) with an embedding for semantic search."""

    title = models.CharField(max_length=500, blank=True)
    body = models.TextField()
    embedding = VectorField(dimensions=settings.EMBEDDING_DIMENSIONS, null=True, blank=True)

    def __str__(self) -> str:
        return self.title or self.body[:60]
