"""Client setup points at OpenRouter. No network calls, no real keys."""
import pytest
from django.core.exceptions import ImproperlyConfigured

from agent import llm


@pytest.fixture(autouse=True)
def fresh_client():
    llm.get_client.cache_clear()
    yield
    llm.get_client.cache_clear()


def test_uses_openrouter_with_bearer_auth(settings):
    settings.OPENROUTER_API_KEY = "sk-or-test"
    client = llm.get_client()
    assert str(client.base_url).startswith("https://openrouter.ai/api")
    assert client.auth_headers == {"Authorization": "Bearer sk-or-test"}


def test_missing_key_gives_a_clear_error(settings):
    settings.OPENROUTER_API_KEY = ""
    with pytest.raises(ImproperlyConfigured, match="OPENROUTER_API_KEY"):
        llm.get_client()
