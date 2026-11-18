from datetime import date, datetime, timedelta, timezone

import pytest
from django.db import IntegrityError

from data.models import CalendarEvent, HealthSample, SleepSession
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
