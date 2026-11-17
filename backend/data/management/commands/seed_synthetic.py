"""Load the synthetic dataset into the database.

    python manage.py seed_synthetic            # replace synthetic rows
    python manage.py seed_synthetic --seed 7   # a different (still fake) dataset

Only rows with source="synthetic" are deleted, so real data is never touched.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from data import synthetic
from data.models import CalendarEvent, HealthSample, SleepSession
from data.timeutils import to_local_date


class Command(BaseCommand):
    help = "Replace all synthetic rows with a freshly generated 60-day dataset."

    def add_arguments(self, parser):
        parser.add_argument("--seed", type=int, default=42)

    @transaction.atomic
    def handle(self, *args, seed: int, **options):
        history, next_week = synthetic.generate(seed)

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
            f"Seeded {len(history)} days of history ({synthetic.FIRST_DAY} to {history[-1].date}) "
            f"and next week's calendar: {len(events)} events, {len(sleeps)} nights, {len(samples)} health samples."
        ))
