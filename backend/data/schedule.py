"""Adding, editing and removing events from the Week page.

These are the user's own changes, made by hand. The agent never calls this:
it can only read the calendar and suggest (see CLAUDE.md).

Changes stay in the local database; nothing is written back to iCloud.
Only today and later can be changed, because past days are the history the
agent learns from.

Edited or added events get source="manual", so the daily `seed_synthetic`
(which only replaces source="synthetic" rows) leaves them alone. A deleted
synthetic event is remembered in RemovedEvent so the seeder doesn't bring it back.
"""
import uuid
from datetime import date, datetime, time

from django.db import transaction

from data.models import CalendarEvent, EventCategory, RemovedEvent
from data.synthetic import SOURCE as SYNTHETIC
from data.timeutils import today, user_tz

MANUAL = "manual"
MAX_TITLE = 200


class ScheduleError(ValueError):
    """A change that can't be made; the message is shown to the user."""


def _clean(body: dict) -> dict:
    """Check a {title, date, start, end, category} body and turn it into model fields."""
    title = str(body.get("title") or "").strip()
    if not title:
        raise ScheduleError("Give the event a title.")
    if len(title) > MAX_TITLE:
        raise ScheduleError(f"Keep the title under {MAX_TITLE} characters.")

    try:
        day = date.fromisoformat(body.get("date"))
        start = time.fromisoformat(body.get("start"))
        end = time.fromisoformat(body.get("end"))
    except (TypeError, ValueError):
        raise ScheduleError("date must be YYYY-MM-DD and start/end must be HH:MM.") from None
    if end <= start:
        raise ScheduleError("The event has to end after it starts.")
    if day < today():
        raise ScheduleError("Past days can't be changed; they're the history the agent learns from.")

    category = body.get("category") or EventCategory.OTHER
    if category not in EventCategory.values:
        raise ScheduleError(f"category must be one of: {', '.join(EventCategory.values)}.")

    tz = user_tz()
    return {"title": title, "category": category,
            "occurred_at": datetime.combine(day, start, tzinfo=tz),
            "end_at": datetime.combine(day, end, tzinfo=tz)}


def _editable(event_id: int) -> CalendarEvent:
    event = CalendarEvent.objects.filter(pk=event_id).first()
    if event is None:
        raise ScheduleError("That event doesn't exist any more.")
    if event.local_date < today():
        raise ScheduleError("Past days can't be changed; they're the history the agent learns from.")
    return event


def add_event(body: dict) -> CalendarEvent:
    fields = _clean(body)
    event = CalendarEvent(source=MANUAL, uid=f"manual-{uuid.uuid4()}@life-agent", calendar_name="Life Agent", **fields)
    event.save()  # save() sets local_date
    return event


def edit_event(event_id: int, body: dict) -> CalendarEvent:
    event = _editable(event_id)
    for name, value in _clean(body).items():
        setattr(event, name, value)
    event.source = MANUAL  # it's the user's version now, so the reseed keeps it (same uid, so no duplicate)
    event.save()
    return event


@transaction.atomic
def remove_event(event_id: int) -> None:
    event = _editable(event_id)
    if event.uid.startswith("synthetic-"):
        RemovedEvent.objects.get_or_create(uid=event.uid)
    event.delete()


def user_changed_uids() -> set[str]:
    """Synthetic event uids the seeder must skip: ones the user edited (now theirs) or deleted."""
    edited = CalendarEvent.objects.exclude(source=SYNTHETIC).filter(uid__startswith="synthetic-")
    return set(edited.values_list("uid", flat=True)) | set(RemovedEvent.objects.values_list("uid", flat=True))
