from datetime import date, datetime, timedelta, timezone

import pytest
from django.db import IntegrityError

from data.models import CalendarEvent, CheckIn, HealthSample, Note, SleepSession
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


def _checkin(**overrides) -> CheckIn:
    fields = dict(
        source="shortcut",
        occurred_at=datetime(2026, 10, 27, 14, 0, tzinfo=UTC),
        mood=4,
        energy=3,
        focus=5,
    )
    fields.update(overrides)
    return CheckIn(**fields)


@pytest.mark.django_db
def test_only_one_checkin_per_day():
    _checkin().save()
    with pytest.raises(IntegrityError):
        _checkin(occurred_at=datetime(2026, 10, 27, 20, 0, tzinfo=UTC)).save()


@pytest.mark.django_db
@pytest.mark.parametrize("field", ["mood", "energy", "focus"])
@pytest.mark.parametrize("bad_value", [0, 6])
def test_checkin_scores_must_be_1_to_5(field, bad_value):
    with pytest.raises(IntegrityError):
        _checkin(**{field: bad_value}).save()


@pytest.mark.django_db
def test_calendar_event_rejects_unknown_category():
    start = datetime(2026, 10, 27, 15, 0, tzinfo=UTC)
    with pytest.raises(IntegrityError):
        CalendarEvent.objects.create(
            source="icloud", occurred_at=start, end_at=start + timedelta(hours=1),
            uid="abc", title="Mystery", category="party",
        )


@pytest.mark.django_db
def test_note_embedding_round_trips():
    embedding = [0.0] * 1536
    embedding[0] = 1.0
    note = Note.objects.create(
        source="synthetic",
        occurred_at=datetime(2026, 10, 27, 15, 0, tzinfo=UTC),
        body="Felt foggy after a short night.",
        embedding=embedding,
    )
    note.refresh_from_db()
    assert len(note.embedding) == 1536
    assert note.embedding[0] == 1.0
