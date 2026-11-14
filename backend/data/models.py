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

from django.core.validators import MaxValueValidator, MinValueValidator
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
    """A single numeric measurement from the Watch.

    Metric names we use: "step_count", "heart_rate", "resting_heart_rate",
    "heart_rate_variability" (ms, SDNN), "active_energy" (kcal).
    """

    metric = models.CharField(max_length=100)
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


class Workout(SourceRecord):
    """One workout from the Watch. `occurred_at` is the start time."""

    activity = models.CharField(max_length=100)  # e.g. "Running", "Traditional Strength Training"
    end_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField()
    active_energy_kcal = models.FloatField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.activity} {self.duration_minutes}min @ {self.occurred_at:%Y-%m-%d %H:%M}"


class MoodEntry(SourceRecord):
    """One State of Mind log from the Health app. `occurred_at` is when it was logged.

    `valence` runs from -1 (very unpleasant) to 1 (very pleasant), as Apple
    records it. `labels` are feelings ("Stressed", "Calm") and `associations`
    are what it was about ("Work", "Health"). Several entries can exist per day;
    the agent only ever sees the daily average, never single entries.
    """

    class Kind(models.TextChoices):
        MOMENTARY = "momentary"  # "how do you feel right now"
        DAILY = "daily"  # "how was your day overall"

    kind = models.CharField(max_length=10, choices=Kind.choices)
    valence = models.FloatField(validators=[MinValueValidator(-1), MaxValueValidator(1)])
    labels = models.JSONField(default=list, blank=True)
    associations = models.JSONField(default=list, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(valence__gte=-1, valence__lte=1),
                name="moodentry_valence_minus1_to_1",
            ),
            models.CheckConstraint(
                condition=models.Q(kind__in=["momentary", "daily"]),
                name="moodentry_valid_kind",
            ),
        ]

    def __str__(self) -> str:
        return f"Mood {self.local_date}: {self.valence:+.2f} ({self.kind})"


class Suggestion(models.Model):
    """Advice the agent gave, saved so it can check later whether it helped.

    Flow:
    1. `save_suggestion` stores it with `baseline_value`: the metric's average
       over the `BASELINE_DAYS` before `start_date`.
    2. On or after `check_on`, `evaluate_suggestion` averages the metric from
       `start_date` up to `check_on` and fills in `outcome_value` and `outcome`.

    `metric` is one of the daily summary metrics, e.g. "mood", "readiness",
    "sleep_hours", "steps".
    """

    BASELINE_DAYS = 14

    class Outcome(models.TextChoices):
        PENDING = "pending"
        IMPROVED = "improved"
        NO_CHANGE = "no_change"
        WORSE = "worse"
        NOT_ENOUGH_DATA = "not_enough_data"

    created_at = models.DateTimeField(auto_now_add=True)
    text = models.TextField()  # what the agent told me, e.g. "Walk 3:00-3:45 on busy days"
    reason = models.TextField(blank=True)  # the evidence it was based on
    metric = models.CharField(max_length=50)
    higher_is_better = models.BooleanField(default=True)
    start_date = models.DateField()
    check_on = models.DateField()
    baseline_value = models.FloatField(null=True, blank=True)
    outcome_value = models.FloatField(null=True, blank=True)
    outcome = models.CharField(max_length=20, choices=Outcome.choices, default=Outcome.PENDING)
    evaluated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(check_on__gt=models.F("start_date")),
                name="suggestion_check_after_start",
            ),
            models.CheckConstraint(
                condition=models.Q(outcome__in=["pending", "improved", "no_change", "worse", "not_enough_data"]),
                name="suggestion_valid_outcome",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.text[:60]} [{self.metric}: {self.outcome}]"
