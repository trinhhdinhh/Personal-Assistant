"""Helpers for the UTC-storage / local-date convention."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.conf import settings


def user_tz() -> ZoneInfo:
    return ZoneInfo(settings.USER_TIME_ZONE)


def today() -> date:
    """The user's current date, or the pinned demo date when DEMO_TODAY is set."""
    if settings.DEMO_TODAY:
        return date.fromisoformat(settings.DEMO_TODAY)
    return datetime.now(user_tz()).date()


def to_local_date(moment: datetime) -> date:
    """Return the calendar date of `moment` in the user's timezone.

    Raises ValueError for naive datetimes, since we can't know what zone they mean.
    """
    if moment.tzinfo is None:
        raise ValueError("occurred_at must be timezone-aware")
    return moment.astimezone(user_tz()).date()
