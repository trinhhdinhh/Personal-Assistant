"""The one place the backend talks to the model, through OpenRouter.

The OpenRouter key comes from the repo-root .env file (git-ignored), loaded by
config/settings.py. It never appears in code, in responses to the frontend,
or in logs.

OpenRouter accepts the Anthropic Messages format, so the agent uses the
Anthropic SDK pointed at OpenRouter. The key is sent as a Bearer token.
The agent loop calls `get_client().messages.create(...)` with
`model=settings.AGENT_MODEL`.
"""
from functools import cache

import anthropic
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


@cache
def get_client() -> anthropic.Anthropic:
    """A shared client. Raises a clear error if the key is missing."""
    if not settings.OPENROUTER_API_KEY:
        raise ImproperlyConfigured(
            "OPENROUTER_API_KEY is not set. Add OPENROUTER_API_KEY=sk-or-... to the .env file "
            "in the repo root, then restart the server."
        )
    return anthropic.Anthropic(
        base_url=settings.OPENROUTER_BASE_URL,
        auth_token=settings.OPENROUTER_API_KEY,  # sent as "Authorization: Bearer ..."
    )
