"""What the agent remembers between runs: the suggestions it made.

Each suggestion names one metric it should move and in which direction, plus
the baseline before it started. A week later `evaluate_suggestion` compares
the metric after the start date with that baseline.
"""
from django.db import models


class Suggestion(models.Model):
    class Direction(models.TextChoices):
        UP = "up"
        DOWN = "down"

    class Status(models.TextChoices):
        PENDING = "pending"          # not checked yet
        IMPROVED = "improved"        # moved the hoped-for way by a meaningful amount
        NO_CHANGE = "no_change"      # moved less than a meaningful amount
        WORSE = "worse"              # moved the other way by a meaningful amount
        NO_DATA = "no_data"          # not enough data to judge

    text = models.CharField(max_length=500)
    metric = models.CharField(max_length=50)  # a daily-summary field, e.g. "sleep_hours"
    direction = models.CharField(max_length=4, choices=Direction.choices)
    start_date = models.DateField()  # first day the suggestion applies
    check_on = models.DateField()    # first day it can be evaluated

    baseline = models.FloatField(null=True, blank=True)  # metric average in the 14 days before start_date
    baseline_days = models.PositiveIntegerField(default=0)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    result = models.FloatField(null=True, blank=True)  # metric average from start_date to check_on
    result_days = models.PositiveIntegerField(default=0)
    evaluated_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"#{self.pk} {self.text} ({self.metric} {self.direction}, {self.status})"
