"""The Claude connector: OAuth metadata, token checks, the API gate, and the MCP tools over HTTP.

No network: MCP calls go through the real ASGI app in-process, and ask_agent
uses the scripted fake model from test_loop.
"""
import json
from datetime import timedelta
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client
from django.utils import timezone
from oauth2_provider.models import get_access_token_model, get_application_model
from starlette.testclient import TestClient

from agent import llm, mcp_auth
from agent.registry import WRITE_TOOLS, run_tool, tool_definitions
from agent.tests.test_loop import FakeClient, reply, text, tool_use

ACCEPT = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


# ---------- helpers ----------

def make_token(*, staff=True, scope="mcp", expires_in=3600, value="good-token"):
    user = get_user_model().objects.create_user(f"u{value}", password="x", is_staff=staff)
    app = get_application_model().objects.create(
        name=f"app-{value}", client_type="confidential", authorization_grant_type="authorization-code",
        redirect_uris="https://claude.ai/api/mcp/auth_callback", user=user)
    get_access_token_model().objects.create(
        user=user, application=app, token=value, scope=scope,
        expires=timezone.now() + timedelta(seconds=expires_in))
    return value


def rpc(client, method, params=None, token="good-token", id=1):
    headers = {**ACCEPT, **({"Authorization": f"Bearer {token}"} if token else {})}
    return client.post("/mcp", headers=headers, content=json.dumps(
        {"jsonrpc": "2.0", "id": id, "method": method, "params": params or {}}))


def call_tool(client, name, arguments=None):
    response = rpc(client, "tools/call", {"name": name, "arguments": arguments or {}})
    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert not result.get("isError"), result
    return result["structuredContent"]


@pytest.fixture
def mcp_client(transactional_db, settings):
    """The real ASGI app (Django + MCP) with synthetic data and one valid token."""
    settings.DEMO_TODAY = "2026-11-16"
    call_command("seed_synthetic", stdout=StringIO())
    make_token()
    cache.clear()
    from config.asgi import build_app
    with TestClient(build_app(), base_url="http://localhost") as client:
        yield client


# ---------- OAuth discovery, health, API gate ----------

def test_oauth_metadata_points_at_this_server(db, settings):
    settings.PUBLIC_URL = "https://agent.example.com"
    server = Client().get("/.well-known/oauth-authorization-server").json()
    assert server["issuer"] == "https://agent.example.com"
    assert server["authorization_endpoint"] == "https://agent.example.com/o/authorize/"
    assert server["code_challenge_methods_supported"] == ["S256"]
    resource = Client().get("/.well-known/oauth-protected-resource").json()
    assert resource["resource"] == "https://agent.example.com/mcp"
    assert resource["authorization_servers"] == ["https://agent.example.com"]


def test_healthz():
    assert Client().get("/healthz").json() == {"ok": True}


def test_api_is_off_when_disabled(db, settings):
    settings.API_ENABLED = False
    assert Client().get("/api/report").status_code == 404
    assert Client().post("/api/chat", {}, content_type="application/json").status_code == 404
    assert Client().get("/healthz").status_code == 200


def test_authorize_page_requires_login(db):
    response = Client().get("/o/authorize/?response_type=code&client_id=x")
    assert response.status_code == 302 and response["Location"].startswith("/admin/login/")


def test_create_claude_client_prints_secret_once(db):
    out = StringIO()
    call_command("create_claude_client", stdout=out)
    app = get_application_model().objects.get(name="Claude connector")
    assert app.redirect_uris == "https://claude.ai/api/mcp/auth_callback"
    assert app.client_id in out.getvalue() and "Client secret:" in out.getvalue()
    call_command("create_claude_client", stdout=StringIO())  # rotating replaces it
    assert get_application_model().objects.filter(name="Claude connector").count() == 1


# ---------- token checks ----------

@pytest.mark.parametrize("kwargs, ok", [
    ({}, True),
    ({"expires_in": -60}, False),
    ({"scope": "read"}, False),
    ({"staff": False}, False),
])
def test_token_rules(db, kwargs, ok):
    token = make_token(**kwargs)
    assert (mcp_auth.lookup_token(token) is not None) is ok


def test_unknown_token_is_rejected(db):
    make_token()
    assert mcp_auth.lookup_token("guess") is None and mcp_auth.lookup_token("") is None


# ---------- MCP over HTTP ----------

def test_mcp_without_token_says_where_to_sign_in(mcp_client):
    response = rpc(mcp_client, "tools/list", token=None)
    assert response.status_code == 401
    assert 'resource_metadata="http://localhost:8000/.well-known/oauth-protected-resource/mcp"' \
        in response.headers["www-authenticate"]


def test_mcp_lists_read_only_tools(mcp_client):
    tools = {t["name"]: t for t in rpc(mcp_client, "tools/list").json()["result"]["tools"]}
    assert set(tools) == {"get_today_brief", "get_week_forecast", "get_weekly_report", "get_recent_trends", "ask_agent"}
    assert all(t["annotations"]["readOnlyHint"] for t in tools.values())


def test_mcp_views_return_summaries(mcp_client):
    brief = call_tool(mcp_client, "get_today_brief")
    assert brief["source"].startswith("Life Agent") and brief["date"] == "2026-11-16"
    week = call_tool(mcp_client, "get_week_forecast")
    assert {d["label"]: d["risk"] for d in week["days"]}["Thu"] == "High"
    report = call_tool(mcp_client, "get_weekly_report")
    assert report["label"] == "NOV 9 – 15 vs NOV 2 – 8"
    trends = call_tool(mcp_client, "get_recent_trends", {"days": 7})
    assert trends["recent"]["end"] == "2026-11-15" and trends["recent"]["days_with_data"]["sleep_hours"] == 7


def test_ask_agent_runs_the_custom_agent_read_only(mcp_client, monkeypatch):
    fake = FakeClient([
        reply(tool_use("find_free_time", {"date": "2026-11-19"}), stop="tool_use"),
        reply(text("You're free from 12:15 to 16:00 on Thursday.")),
    ])
    monkeypatch.setattr(llm, "get_client", lambda: fake)

    result = call_tool(mcp_client, "ask_agent", {"question": "When am I free Thursday?"})
    assert result["stop"] == "answered" and "12:15" in result["answer"]
    assert [s["tool"] for s in result["steps"]] == ["find_free_time"]
    assert all(c["passed"] for c in result["checks"])
    sent_tools = {t["name"] for t in fake.requests[0]["tools"]}
    assert "save_suggestion" not in sent_tools  # no writes through the connector
    assert "read-only" in fake.requests[0]["system"][1]["text"]


def test_ask_agent_daily_limit(mcp_client, monkeypatch, settings):
    settings.MCP_DAILY_ASK_LIMIT = 1
    monkeypatch.setattr(llm, "get_client", lambda: FakeClient([reply(text("Hi.")), reply(text("Hi."))]))
    call_tool(mcp_client, "ask_agent", {"question": "Hello"})
    second = rpc(mcp_client, "tools/call", {"name": "ask_agent", "arguments": {"question": "Hello again"}}).json()
    assert second["result"]["isError"] and "daily limit" in json.dumps(second["result"])


# ---------- read-only agent ----------

def test_read_only_tool_list_and_refusal():
    assert not WRITE_TOOLS & {t["name"] for t in tool_definitions(allow_writes=False)}
    assert {t["name"] for t in tool_definitions()} >= WRITE_TOOLS
    allowed = {t["name"] for t in tool_definitions(allow_writes=False)}
    content, is_error = run_tool("save_suggestion", {"text": "x"}, allowed)
    assert is_error and "Unknown tool" in content


# ---------- the whole sign-in, as Claude does it ----------

def test_full_oauth_flow_then_mcp_call(transactional_db, settings):
    """Login → authorize with PKCE → token → /mcp. Uses the client from create_claude_client."""
    import base64
    import hashlib
    import re
    import secrets
    from urllib.parse import parse_qs, urlparse

    settings.DEMO_TODAY = "2026-11-16"
    call_command("seed_synthetic", stdout=StringIO())
    get_user_model().objects.create_user("me", password="pw", is_staff=True)
    out = StringIO()
    call_command("create_claude_client", stdout=out)
    client_id = re.search(r"Client ID:\s+(\S+)", out.getvalue()).group(1)
    client_secret = re.search(r"Client secret:\s+(\S+)", out.getvalue()).group(1)

    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    params = {
        "response_type": "code", "client_id": client_id, "redirect_uri": settings.CLAUDE_REDIRECT_URI,
        "scope": "mcp", "state": "abc", "code_challenge": challenge, "code_challenge_method": "S256",
        "resource": f"{settings.PUBLIC_URL}/mcp",
    }

    browser = Client()
    assert browser.login(username="me", password="pw")
    page = browser.get("/o/authorize/", params)
    assert page.status_code == 200  # the "allow Claude?" page
    approved = browser.post("/o/authorize/", {**params, "allow": "Authorize"})
    assert approved.status_code == 302
    redirect = urlparse(approved["Location"])
    assert f"{redirect.scheme}://{redirect.netloc}{redirect.path}" == settings.CLAUDE_REDIRECT_URI
    query = parse_qs(redirect.query)
    assert query["state"] == ["abc"]
    assert query["iss"] == [settings.PUBLIC_URL]  # RFC 9207: matches the metadata's issuer

    token = Client().post("/o/token/", {
        "grant_type": "authorization_code", "code": query["code"][0], "redirect_uri": settings.CLAUDE_REDIRECT_URI,
        "client_id": client_id, "client_secret": client_secret, "code_verifier": verifier,
        "resource": f"{settings.PUBLIC_URL}/mcp",
    }).json()
    assert token["scope"] == "mcp" and token["refresh_token"]

    # Without the PKCE verifier the code is useless.
    assert Client().post("/o/token/", {
        "grant_type": "authorization_code", "code": query["code"][0], "redirect_uri": settings.CLAUDE_REDIRECT_URI,
        "client_id": client_id, "client_secret": client_secret,
    }).status_code == 400

    from config.asgi import build_app
    with TestClient(build_app(), base_url="http://localhost") as client:
        brief = call_tool_with(client, "get_today_brief", token["access_token"])
        assert brief["dateLabel"] == "MON · NOV 16"


def call_tool_with(client, name, token, arguments=None):
    response = rpc(client, "tools/call", {"name": name, "arguments": arguments or {}}, token=token)
    assert response.status_code == 200, response.text
    return response.json()["result"]["structuredContent"]
