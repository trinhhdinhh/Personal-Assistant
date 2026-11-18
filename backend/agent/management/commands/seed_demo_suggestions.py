"""Add three example suggestions "taken" in early November, for demoing follow-ups.

    python manage.py seed_demo_suggestions

Synthetic demo data only. The results are not made up: each suggestion is
checked against the synthetic dataset by evaluate_suggestion, like a real one.
Running it again replaces the same three suggestions.
"""
from django.core.management.base import BaseCommand

from agent import tools
from agent.models import Suggestion

DEMO = [
    ("Lights out by 23:00 before busy days", "sleep_hours", "up", "2026-11-02"),
    ("Take a 30-minute walk in your free gap on class days", "steps", "up", "2026-11-03"),
    ("Keep your planned gym sessions", "mood", "up", "2026-11-06"),
]


class Command(BaseCommand):
    help = "Add three example suggestions from early November so the Report shows follow-ups."

    def handle(self, *args, **options):
        Suggestion.objects.filter(text__in=[text for text, *_ in DEMO]).delete()
        for text, metric, direction, start in DEMO:
            saved = tools.save_suggestion(text=text, metric=metric, direction=direction, start_date=start)
            self.stdout.write(f"#{saved['suggestion_id']} {text} (check on {saved['check_on']})")
        self.stdout.write(self.style.SUCCESS("Done. Open the Report page (DEMO_TODAY=2026-11-16) to see the follow-ups."))
