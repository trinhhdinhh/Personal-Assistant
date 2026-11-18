"""Ask the agent a question from the terminal and see every step it took.

    python manage.py ask "Do busy days affect my mood?"
    python manage.py ask "How's my week looking?" --json

Each question makes a few real model calls through OpenRouter.
"""
import json

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError

from agent.loop import run_agent


class Command(BaseCommand):
    help = "Ask the agent a question and print its steps and answer."

    def add_arguments(self, parser):
        parser.add_argument("question")
        parser.add_argument("--json", action="store_true", help="Print the full run as JSON.")

    def handle(self, *args, question: str, **options):
        try:
            run = run_agent(question)
        except ImproperlyConfigured as error:
            raise CommandError(str(error))

        if options["json"]:
            self.stdout.write(json.dumps(run.to_dict(), indent=2, default=str))
            return

        for i, step in enumerate(run.steps, 1):
            mark = self.style.SUCCESS("ok ") if step.ok else self.style.ERROR("err")
            self.stdout.write(f"{i:>2}. {mark} {step.tool}({_short(step.input)})")
            self.stdout.write(f"       {step.summary}")
        self.stdout.write("")
        self.stdout.write(run.answer)
        self.stdout.write("")
        self.stdout.write(self.style.NOTICE(
            f"[{run.stop}] {run.model_calls} model calls, {len(run.steps)} tool calls, "
            f"{run.input_tokens:,} in / {run.output_tokens:,} out tokens, {run.model}"))


def _short(tool_input: dict) -> str:
    return ", ".join(f"{k}={v!r}" for k, v in tool_input.items())
