"""Add three example suggestions "taken" two weeks ago, for demoing follow-ups.

    python manage.py seed_demo_suggestions

Synthetic demo data only. The results are not made up: each suggestion is
checked against the synthetic dataset by evaluate_suggestion, like a real one.
Running it again replaces the same three suggestions, with dates moved to match today.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand

from agent import tools
from agent.models import Suggestion
from data.report import last_full_week

# (text, metric, direction, days after the Monday before the report's week)
# With today = Mon Nov 16 the report covers Nov 9-15 and these start on Nov 2, 3 and 6.
DEMO = [
    ("Lights out by 23:00 before busy days", "sleep_hours", "up", 0),
    ("Take a 30-minute walk in your free gap on class days", "steps", "up", 1),
    ("Keep your planned gym sessions", "mood", "up", 4),
]


class Command(BaseCommand):
    help = "Add three example suggestions from two weeks ago so the Report shows follow-ups."

    def handle(self, *args, **options):
        Suggestion.objects.filter(text__in=[text for text, *_ in DEMO]).delete()
        week_before_report = last_full_week() - timedelta(days=7)
        for text, metric, direction, offset in DEMO:
            start = (week_before_report + timedelta(days=offset)).isoformat()
            saved = tools.save_suggestion(text=text, metric=metric, direction=direction, start_date=start)
            self.stdout.write(f"#{saved['suggestion_id']} {text} (check on {saved['check_on']})")
        self.stdout.write(self.style.SUCCESS("Done. Open the Report page to see the follow-ups."))
