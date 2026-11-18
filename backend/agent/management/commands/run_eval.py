"""Run the agent on the synthetic test questions and score every answer.

    python manage.py run_eval                    # all 10 questions
    python manage.py run_eval --only 1 7         # just some
    python manage.py run_eval --model anthropic/claude-sonnet-5.5
    python manage.py run_eval --save             # also write eval_results/<time>.json

Makes real model calls through OpenRouter (roughly 2-6 per question).
Runs on the synthetic dataset only, with "today" pinned to 2026-11-16.
Each question runs inside a rolled-back transaction, so suggestions the
agent saves during the eval don't stay in the database.
"""
import json
import time
from datetime import datetime
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from agent.evaluation import grade, load_questions
from agent.loop import run_agent
from data import synthetic
from data.models import CalendarEvent, HealthSample, SleepSession

RESULTS_DIR = Path(settings.BASE_DIR) / "eval_results"


class Command(BaseCommand):
    help = "Run the agent on the synthetic test questions and score the answers."

    def add_arguments(self, parser):
        parser.add_argument("--only", nargs="+", type=int, help="Question ids to run.")
        parser.add_argument("--model", help="Override AGENT_MODEL for this run.")
        parser.add_argument("--save", action="store_true", help="Write the full results to eval_results/.")

    def handle(self, *args, only=None, model=None, save=False, **options):
        for table in (HealthSample, SleepSession, CalendarEvent):
            if table.objects.exclude(source=synthetic.SOURCE).exists():
                raise CommandError("The database has real (non-synthetic) data. Run the eval on a synthetic-only database.")
        call_command("seed_synthetic", stdout=StringIO())
        settings.DEMO_TODAY = synthetic.TODAY.isoformat()
        if model:
            settings.AGENT_MODEL = model

        questions = [q for q in load_questions() if not only or q["id"] in only]
        self.stdout.write(f"Running {len(questions)} questions on {settings.AGENT_MODEL} (today = {settings.DEMO_TODAY})\n")

        results = []
        for q in questions:
            self.stdout.write(f"Q{q['id']:>2} {q['question']}")
            started = time.monotonic()
            try:
                with transaction.atomic():
                    run = run_agent(q["question"])
                    transaction.set_rollback(True)
            except ImproperlyConfigured as error:
                raise CommandError(str(error))
            result = {**grade(q, run), "seconds": round(time.monotonic() - started, 1)}
            results.append(result)
            self._print(result)

        self._summary(results)
        if save:
            RESULTS_DIR.mkdir(exist_ok=True)
            path = RESULTS_DIR / f"{datetime.now():%Y%m%d-%H%M%S}-{settings.AGENT_MODEL.replace('/', '_')}.json"
            path.write_text(json.dumps({"model": settings.AGENT_MODEL, "today": settings.DEMO_TODAY,
                                        "results": results}, indent=2, default=str))
            self.stdout.write(f"\nSaved {path.relative_to(settings.BASE_DIR)}")

    def _print(self, r: dict) -> None:
        mark = self.style.SUCCESS("PASS") if r["passed"] else self.style.ERROR("FAIL")
        self.stdout.write(f"    {mark}  tools: {' → '.join(r['tools_used']) or '(none)'}")
        for name, c in r["criteria"].items():
            if not c["passed"]:
                self.stdout.write(self.style.WARNING(f"          ✗ {name}: {c['detail']}"))
        if r["retries"]:
            self.stdout.write(f"          answer rewritten {r['retries']}x after a failed check")
        self.stdout.write(f"          {r['model_calls']} model calls · {r['tokens']:,} tokens · {r['seconds']}s\n")

    def _summary(self, results: list[dict]) -> None:
        passed = sum(r["passed"] for r in results)
        def rate(name):
            graded = [r for r in results if name in r["criteria"]]
            ok = sum(r["criteria"][name]["passed"] for r in graded)
            return f"{ok}/{len(graded)}"

        self.stdout.write(self.style.MIGRATE_HEADING(f"Passed {passed}/{len(results)} questions"))
        self.stdout.write(f"  answered and passed checks: {rate('answered')}")
        self.stdout.write(f"  used the right tools:       {rate('must_use')}")
        self.stdout.write(f"  found the planted pattern:  {rate('evidence')}")
        self.stdout.write(f"  said what it should:        {rate('must_say')}")
        self.stdout.write(f"  avoided banned claims:      {rate('must_not')}")
        self.stdout.write(f"  answers rewritten by checks: {sum(r['retries'] for r in results)}")
        self.stdout.write(f"  total: {sum(r['tokens'] for r in results):,} tokens, "
                          f"{sum(r['seconds'] for r in results):.0f}s")
