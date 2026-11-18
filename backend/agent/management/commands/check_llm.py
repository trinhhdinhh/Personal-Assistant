"""Check that the model key works and that tool use comes through.

    python manage.py check_llm

Sends one small request (a few cents at most) with one of the agent's real
tool definitions and reports what came back. Never prints the key.
"""
import anthropic
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError

from agent import llm
from agent.registry import TOOL_DEFINITIONS


class Command(BaseCommand):
    help = "Send one test request to the configured model and check tool use works."

    def handle(self, *args, **options):
        tool = next(t for t in TOOL_DEFINITIONS if t["name"] == "find_free_time")
        self.stdout.write(f"Provider: OpenRouter   Model: {settings.AGENT_MODEL}")

        try:
            client = llm.get_client()
        except ImproperlyConfigured as error:
            raise CommandError(str(error))

        try:
            response = client.messages.create(
                model=settings.AGENT_MODEL,
                max_tokens=2048,
                tools=[tool],
                messages=[{"role": "user", "content": "When am I free on 2026-11-19? Use the tool."}],
            )
        except anthropic.AuthenticationError:
            raise CommandError("The key was rejected. Check the value in .env (no quotes or spaces).")
        except anthropic.NotFoundError as error:
            raise CommandError(f"Model not found: {settings.AGENT_MODEL}. Set AGENT_MODEL in .env. ({error.message})")
        except anthropic.BadRequestError as error:
            raise CommandError(f"Request rejected: {error.message}")
        except anthropic.APIStatusError as error:
            raise CommandError(f"API error {error.status_code}: {error.message}")
        except anthropic.APIConnectionError:
            raise CommandError("Could not reach the API. Check your internet connection.")

        calls = [b for b in response.content if b.type == "tool_use"]
        self.stdout.write(f"Stop reason: {response.stop_reason}")
        self.stdout.write(f"Tokens: {response.usage.input_tokens} in, {response.usage.output_tokens} out")
        if calls:
            self.stdout.write(self.style.SUCCESS(f"OK: the model called {calls[0].name}({calls[0].input})"))
        else:
            self.stdout.write(self.style.WARNING("Connected, but the model did not call the tool."))
