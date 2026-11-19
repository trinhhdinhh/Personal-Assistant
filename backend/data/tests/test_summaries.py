"""Daily summaries must match the synthetic generator day by day, and handle real-data cases."""
from datetime import date, datetime, timedelta
from io import StringIO
from zoneinfo import ZoneInfo

import pytest
from django.core.management import call_command

from data import synthetic
from data.models import CalendarEvent, HealthSample, SleepSession
from data.summaries import daily_summaries

CHICAGO = ZoneInfo("America/Chicago")
HISTORY, NEXT_WEEK = synthetic.generate(seed=42)

ROW_KEYS = {
    "date", "sleep_hours", "readiness", "hrv", "resting_hr", "mood", "steps", "active_energy",
    "workout_minutes", "booked_hours", "late_event", "class_day",
}


@pytest.fixture
def seeded(db):
    call_command("seed_synthetic", today="2026-11-16", stdout=StringIO())


def _at(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=CHICAGO)


# ---------- against the synthetic dataset ----------

def test_one_row_per_day_in_order(seeded):
    rows = daily_summaries(synthetic.FIRST_DAY, NEXT_WEEK[-1].date)
    assert [r["date"] for r in rows] == [d.date for d in HISTORY + NEXT_WEEK]


def test_rows_hold_daily_numbers_only(seeded):
    """Privacy rule: the agent gets these rows, so no raw payloads or extra fields."""
    for row in daily_summaries(synthetic.FIRST_DAY, synthetic.TODAY):
        assert set(row) == ROW_KEYS


def test_history_matches_the_generator(seeded):
    rows = daily_summaries(synthetic.FIRST_DAY, HISTORY[-1].date)
    for day, row in zip(HISTORY, rows):
        assert row["sleep_hours"] == round(day.sleep.asleep_minutes / 60, 2)
        assert row["readiness"] == day.metric("readiness")
        assert row["hrv"] == day.metric("heart_rate_variability")
        assert row["resting_hr"] == day.metric("resting_heart_rate")
        assert row["steps"] == day.metric("step_count")
        assert row["mood"] == day.metric("state_of_mind_valence")  # None on days without a log
        assert row["workout_minutes"] == (day.metric("workout_minutes") or 0)
        assert row["booked_hours"] == round(day.booked_hours, 2)
        assert row["late_event"] == day.has_late_event
        assert row["class_day"] == day.is_class_day


def test_next_week_has_calendar_but_no_health(seeded):
    rows = daily_summaries(NEXT_WEEK[0].date, NEXT_WEEK[-1].date)
    assert [r["booked_hours"] for r in rows] == [round(d.booked_hours, 2) for d in NEXT_WEEK]
    for row in rows:
        assert row["sleep_hours"] is None and row["readiness"] is None and row["mood"] is None
        assert row["workout_minutes"] is None  # unknown, not "no workout"
    thursday = rows[3]
    assert thursday["booked_hours"] == 8.25


# ---------- cases real Apple Health data will produce ----------

DAY = date(2026, 10, 14)


@pytest.mark.django_db
def test_many_samples_per_day_are_totalled_or_averaged():
    for steps, hrv in [(4000, 40), (3500, 50), (500, 60)]:
        HealthSample.objects.create(source="apple_health", occurred_at=_at(DAY, 12), metric="step_count", value=steps)
        HealthSample.objects.create(source="apple_health", occurred_at=_at(DAY, 7), metric="heart_rate_variability", value=hrv)
    [row] = daily_summaries(DAY, DAY)
    assert row["steps"] == 8000
    assert row["hrv"] == 50
    assert row["workout_minutes"] == 0  # health data exists, no workout logged


@pytest.mark.django_db
def test_late_night_utc_sample_belongs_to_the_local_day():
    # 11pm in Chicago is already the next day in UTC.
    HealthSample.objects.create(source="apple_health", occurred_at=_at(DAY, 23), metric="step_count", value=900)
    [row] = daily_summaries(DAY, DAY)
    assert row["steps"] == 900


@pytest.mark.django_db
def test_late_and_overnight_events_count_as_late():
    for uid, start, end in [("a", _at(DAY, 9), _at(DAY, 10)), ("b", _at(DAY, 22), _at(DAY, 23, 30))]:
        CalendarEvent.objects.create(source="icloud", uid=uid, title="x", occurred_at=start, end_at=end)
    overnight = DAY + timedelta(days=1)
    CalendarEvent.objects.create(source="icloud", uid="c", title="x", category="class",
                                 occurred_at=_at(overnight, 20), end_at=_at(overnight, 23) + timedelta(hours=2))
    first, second = daily_summaries(DAY, overnight)
    assert first["booked_hours"] == 2.5 and first["late_event"] and not first["class_day"]
    assert second["booked_hours"] == 5 and second["late_event"] and second["class_day"]


@pytest.mark.django_db
def test_all_day_events_are_not_booked_time():
    CalendarEvent.objects.create(source="icloud", uid="holiday", title="Holiday", all_day=True,
                                 occurred_at=_at(DAY, 0), end_at=_at(DAY + timedelta(days=1), 0))
    [row] = daily_summaries(DAY, DAY)
    assert row["booked_hours"] == 0 and not row["late_event"]


@pytest.mark.django_db
def test_naps_add_to_the_nights_sleep():
    for start, minutes in [(_at(DAY - timedelta(days=1), 23), 360), (_at(DAY, 14), 30)]:
        SleepSession.objects.create(source="apple_health", occurred_at=start,
                                    end_at=start + timedelta(minutes=minutes), asleep_minutes=minutes)
    [row] = daily_summaries(DAY, DAY)
    assert row["sleep_hours"] == 6.5


@pytest.mark.django_db
def test_empty_day_has_a_row_of_unknowns():
    [row] = daily_summaries(DAY, DAY)
    assert row["date"] == DAY and row["steps"] is None and row["workout_minutes"] is None
    assert row["booked_hours"] == 0 and row["late_event"] is False


def test_end_before_start_is_rejected():
    with pytest.raises(ValueError):
        daily_summaries(DAY, DAY - timedelta(days=1))
