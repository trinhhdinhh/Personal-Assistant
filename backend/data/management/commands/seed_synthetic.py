"""Load the synthetic dataset into the database, up to today.

    python manage.py seed_synthetic                     # Sep 1 to yesterday, plus the coming week's calendar
    python manage.py seed_synthetic --today 2026-11-16  # the fixed date the tests and the eval use
    python manage.py seed_synthetic --seed 7            # a different (still fake) dataset

"Today" defaults to the real date (or DEMO_TODAY if set). Run it again on a new
day and the history grows by that day; earlier days stay exactly the same.

Only rows with source="synthetic" are deleted, so real data is never touched.
"""
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from data import synthetic, timeutils
from data.models import CalendarEvent, HealthSample, SleepSession
from data.timeutils import to_local_date


class Command(BaseCommand):
    help = "Load synthetic data from Sep 1 to yesterday, plus the coming week's calendar."

    def add_arguments(self, parser):
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--today", type=date.fromisoformat, default=None,
                            help="The date to build the data around (YYYY-MM-DD). Default: today.")

    @transaction.atomic
    def handle(self, *args, seed: int, today: date | None = None, **options):
        if isinstance(today, str):  # call_command(..., today="2026-11-16") skips the argparse type
            today = date.fromisoformat(today)
        today = today or timeutils.today()
        history, next_week = synthetic.generate(seed, today)

        for model in (HealthSample, SleepSession, CalendarEvent):
            model.objects.filter(source=synthetic.SOURCE).delete()

        # bulk_create skips save(), so local_date is set here (see data/models.py).
        events = [
            CalendarEvent(
                source=synthetic.SOURCE,
                occurred_at=e.start,
                end_at=e.end,
                local_date=to_local_date(e.start),
                uid=f"synthetic-{e.start:%Y%m%dT%H%M}-{n}@life-agent",
                title=e.title,
                category=e.category,
                calendar_name="Synthetic",
            )
            for day in history + next_week
            for n, e in enumerate(day.events)
        ]
        sleeps = [
            SleepSession(
                source=synthetic.SOURCE,
                occurred_at=d.sleep.bedtime,
                end_at=d.sleep.wake,
                local_date=to_local_date(d.sleep.wake),
                asleep_minutes=d.sleep.asleep_minutes,
                in_bed_minutes=d.sleep.in_bed_minutes,
            )
            for d in history
        ]
        samples = [
            HealthSample(
                source=synthetic.SOURCE,
                occurred_at=s.start,
                end_at=s.end,
                local_date=to_local_date(s.start),
                metric=s.metric,
                value=s.value,
                unit=s.unit,
                raw=s.raw,
            )
            for d in history
            for s in d.samples
        ]

        CalendarEvent.objects.bulk_create(events)
        SleepSession.objects.bulk_create(sleeps)
        HealthSample.objects.bulk_create(samples)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(history)} days of history ({history[0].date} to {history[-1].date}) and the calendar "
            f"for {next_week[0].date} to {next_week[-1].date}: {len(events)} events, {len(sleeps)} nights, "
            f"{len(samples)} health samples."
        ))
