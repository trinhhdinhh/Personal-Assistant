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


def clock12(hhmm: str) -> str:
    """Show a 24-hour "14:30" as "2:30 PM".

    Tools and code keep 24-hour HH:MM (easy to sort and compare); only what
    the user sees is converted.
    """
    hour, minute = (int(part) for part in hhmm.split(":"))
    return f"{hour % 12 or 12}:{minute:02d} {'AM' if hour < 12 else 'PM'}"


def clock12_range(start: str, end: str) -> str:
    """"14:30", "15:00" -> "2:30 PM–3:00 PM"."""
    return f"{clock12(start)}–{clock12(end)}"


def to_local_date(moment: datetime) -> date:
    """Return the calendar date of `moment` in the user's timezone.

    Raises ValueError for naive datetimes, since we can't know what zone they mean.
    """
    if moment.tzinfo is None:
        raise ValueError("occurred_at must be timezone-aware")
    return moment.astimezone(user_tz()).date()
