"""The one web process: Django plus the MCP server for the Claude connector.

    uvicorn config.asgi:app

- /mcp and /.well-known/oauth-protected-resource/mcp  -> MCP server (agent/mcp_server.py)
- everything else (OAuth sign-in, admin, metadata, health) -> Django
"""
import os

import django
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings  # noqa: E402
from mcp.server.transport_security import TransportSecuritySettings  # noqa: E402

from agent.mcp_server import build_server  # noqa: E402

MCP_PATHS = ("/mcp", "/mcp/", "/.well-known/oauth-protected-resource/mcp")


def build_app():
    """A fresh Django + MCP app. (The MCP session manager can only start once per app.)"""
    django_app = get_asgi_application()
    mcp_app = build_server().streamable_http_app(
        streamable_http_path="/mcp",
        stateless_http=True,   # each request stands alone; nothing to keep between calls
        json_response=True,    # plain JSON replies, no event stream needed
        # /mcp requests don't pass through Django, so check the Host header here too (same list as
        # ALLOWED_HOSTS). A browser Origin, if one is sent, must be Claude's or this server's own.
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[h for host in settings.ALLOWED_HOSTS for h in (host, f"{host}:*")],
            allowed_origins=["https://claude.ai", "https://claude.com", settings.PUBLIC_URL],
        ),
    )

    async def app(scope, receive, send):
        if scope["type"] == "lifespan":  # starts the MCP session manager; Django has no lifespan of its own
            await mcp_app(scope, receive, send)
        elif scope["type"] == "http" and scope["path"] in MCP_PATHS:
            if scope["path"] == "/mcp/":
                scope = {**scope, "path": "/mcp", "raw_path": b"/mcp"}
            await mcp_app(scope, receive, send)
        else:
            await django_app(scope, receive, send)

    return app


app = build_app()
