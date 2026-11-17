"""The synthetic dataset must contain the planted patterns, and nothing else strong."""
from datetime import date
from statistics import correlation, mean

import pytest
from django.core.management import call_command

from data import synthetic
from data.models import CalendarEvent, HealthSample, SleepSession

HISTORY, NEXT_WEEK = synthetic.generate(seed=42)
PAIRS = list(zip(HISTORY, HISTORY[1:]))  # (yesterday, today)


def _mood(day):
    return day.metric("state_of_mind_valence")


def _avg_next_day(condition, value):
    """Average of value(today) for days whose yesterday matches / doesn't match condition."""
    hit = [value(b) for a, b in PAIRS if condition(a) and value(b) is not None]
    miss = [value(b) for a, b in PAIRS if not condition(a) and value(b) is not None]
    assert len(hit) >= 10 and len(miss) >= 10, "too few days to test the pattern"
    return mean(hit), mean(miss)


def test_same_seed_gives_same_data():
    again, _ = synthetic.generate(seed=42)
    assert [d.metric("readiness") for d in again] == [d.metric("readiness") for d in HISTORY]


def test_covers_60_days_before_demo_today():
    assert len(HISTORY) == 60
    assert HISTORY[0].date == date(2026, 9, 17)
    assert HISTORY[-1].date == date(2026, 11, 15)
    assert [d.date for d in NEXT_WEEK][0] == date(2026, 11, 16)


def test_busy_days_lower_next_day_mood():
    after_busy, otherwise = _avg_next_day(lambda d: d.is_busy, _mood)
    assert otherwise - after_busy > 0.25


def test_busy_days_lower_next_day_readiness():
    after_busy, otherwise = _avg_next_day(lambda d: d.is_busy, lambda d: d.metric("readiness"))
    assert otherwise - after_busy > 1


def test_late_events_shorten_sleep():
    after_late, otherwise = _avg_next_day(lambda d: d.has_late_event, lambda d: d.sleep.asleep_minutes)
    assert otherwise - after_late > 40


def test_workouts_raise_next_day_mood():
    after_workout, otherwise = _avg_next_day(lambda d: d.metric("workout_minutes") is not None, _mood)
    assert after_workout - otherwise > 0.2


def test_short_sleep_lowers_readiness():
    short = [d.metric("readiness") for d in HISTORY if d.sleep.asleep_minutes < 360]
    normal = [d.metric("readiness") for d in HISTORY if d.sleep.asleep_minutes >= 360]
    assert len(short) >= 5
    assert mean(normal) - mean(short) > 1.5


def test_class_days_have_fewer_steps():
    class_days = [d.metric("step_count") for d in HISTORY if d.is_class_day]
    other_days = [d.metric("step_count") for d in HISTORY if not d.is_class_day]
    assert mean(other_days) - mean(class_days) > 1500


def test_steps_and_hrv_are_unrelated():
    steps = [d.metric("step_count") for d in HISTORY]
    hrv = [d.metric("heart_rate_variability") for d in HISTORY]
    assert abs(correlation(steps, hrv)) < 0.3


def test_next_week_has_heavy_thursday_after_late_wednesday():
    wednesday, thursday = NEXT_WEEK[2], NEXT_WEEK[3]
    assert wednesday.has_late_event
    assert thursday.booked_hours == max(d.booked_hours for d in NEXT_WEEK) >= 8


def test_values_stay_in_range():
    for day in HISTORY:
        assert 0 <= day.metric("readiness") <= 10
        mood = _mood(day)
        assert mood is None or -1 <= mood <= 1
        for a, b in zip(day.events, day.events[1:]):
            assert a.end <= b.start, f"overlapping events on {day.date}"


@pytest.mark.django_db
def test_seed_command_replaces_only_synthetic_rows():
    real = HealthSample.objects.create(
        source="apple_health", occurred_at=HISTORY[0].samples[0].start, metric="step_count", value=1,
    )
    call_command("seed_synthetic")
    call_command("seed_synthetic")  # running twice must not duplicate

    assert SleepSession.objects.filter(source="synthetic").count() == 60
    assert CalendarEvent.objects.filter(source="synthetic").count() == sum(
        len(d.events) for d in HISTORY + NEXT_WEEK
    )
    assert HealthSample.objects.filter(source="synthetic", metric="readiness").count() == 60
    assert HealthSample.objects.filter(pk=real.pk).exists()
