from datetime import date, datetime, timedelta, timezone

import pytest
from django.db import IntegrityError

from data.models import CalendarEvent, HealthSample, MoodEntry, SleepSession, Suggestion, Workout
from data.timeutils import to_local_date

UTC = timezone.utc


def test_to_local_date_converts_to_user_timezone():
    # 03:00 UTC on Oct 27 is still Oct 26 in Chicago (UTC-5 in October).
    assert to_local_date(datetime(2026, 10, 27, 3, 0, tzinfo=UTC)) == date(2026, 10, 26)
    assert to_local_date(datetime(2026, 10, 27, 15, 0, tzinfo=UTC)) == date(2026, 10, 27)


def test_to_local_date_rejects_naive_datetime():
    with pytest.raises(ValueError):
        to_local_date(datetime(2026, 10, 27, 3, 0))


@pytest.mark.django_db
def test_local_date_is_derived_on_save():
    sample = HealthSample.objects.create(
        source="apple_health",
        occurred_at=datetime(2026, 10, 27, 3, 0, tzinfo=UTC),
        metric="step_count",
        value=1200,
        unit="count",
        raw={"type": "HKQuantityTypeIdentifierStepCount"},
    )
    sample.refresh_from_db()
    assert sample.local_date == date(2026, 10, 26)
    assert sample.raw == {"type": "HKQuantityTypeIdentifierStepCount"}


@pytest.mark.django_db
def test_sleep_session_belongs_to_wake_up_day():
    bedtime = datetime(2026, 10, 27, 4, 30, tzinfo=UTC)  # 23:30 Oct 26 in Chicago
    sleep = SleepSession.objects.create(
        source="apple_health",
        occurred_at=bedtime,
        end_at=bedtime + timedelta(hours=7),
        asleep_minutes=400,
    )
    assert sleep.local_date == date(2026, 10, 27)


@pytest.mark.django_db
def test_calendar_event_rejects_unknown_category():
    start = datetime(2026, 10, 27, 15, 0, tzinfo=UTC)
    with pytest.raises(IntegrityError):
        CalendarEvent.objects.create(
            source="icloud", occurred_at=start, end_at=start + timedelta(hours=1),
            uid="abc", title="Mystery", category="party",
        )


def _mood(**overrides) -> MoodEntry:
    fields = dict(
        source="apple_health",
        occurred_at=datetime(2026, 10, 27, 14, 0, tzinfo=UTC),
        kind=MoodEntry.Kind.DAILY,
        valence=0.4,
        labels=["Calm"],
        associations=["Work"],
    )
    fields.update(overrides)
    return MoodEntry(**fields)


@pytest.mark.django_db
def test_several_mood_entries_allowed_per_day():
    _mood().save()
    _mood(kind=MoodEntry.Kind.MOMENTARY, occurred_at=datetime(2026, 10, 27, 20, 0, tzinfo=UTC)).save()
    assert MoodEntry.objects.filter(local_date=date(2026, 10, 27)).count() == 2


@pytest.mark.django_db
@pytest.mark.parametrize("bad_valence", [-1.5, 1.01])
def test_mood_valence_must_be_minus1_to_1(bad_valence):
    with pytest.raises(IntegrityError):
        _mood(valence=bad_valence).save()


@pytest.mark.django_db
def test_mood_rejects_unknown_kind():
    with pytest.raises(IntegrityError):
        _mood(kind="weekly").save()


@pytest.mark.django_db
def test_workout_belongs_to_start_day():
    start = datetime(2026, 10, 27, 23, 0, tzinfo=UTC)  # 18:00 Oct 27 in Chicago
    workout = Workout.objects.create(
        source="apple_health", occurred_at=start, end_at=start + timedelta(minutes=45),
        activity="Running", duration_minutes=45,
    )
    assert workout.local_date == date(2026, 10, 27)


def _suggestion(**overrides) -> Suggestion:
    fields = dict(
        text="Take a 30 min walk at 3pm on busy days",
        metric="mood",
        start_date=date(2026, 11, 2),
        check_on=date(2026, 11, 9),
        baseline_value=0.1,
    )
    fields.update(overrides)
    return Suggestion(**fields)


@pytest.mark.django_db
def test_new_suggestion_is_pending():
    suggestion = _suggestion()
    suggestion.save()
    suggestion.refresh_from_db()
    assert suggestion.outcome == Suggestion.Outcome.PENDING
    assert suggestion.outcome_value is None


@pytest.mark.django_db
def test_suggestion_check_must_come_after_start():
    with pytest.raises(IntegrityError):
        _suggestion(check_on=date(2026, 11, 2)).save()


@pytest.mark.django_db
def test_suggestion_rejects_unknown_outcome():
    with pytest.raises(IntegrityError):
        _suggestion(outcome="great").save()
