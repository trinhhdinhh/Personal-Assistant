"""OAuth plumbing for the Claude connector: discovery metadata and a health check.

The sign-in itself is django-oauth-toolkit (/o/authorize, /o/token), with you
logging in on the Django admin login page. These views only describe it, so
Claude can find the endpoints on its own:

- /.well-known/oauth-authorization-server   (RFC 8414) where to authorize and get tokens
- /.well-known/oauth-protected-resource     (RFC 9728) which server protects /mcp
  The MCP server also serves this at /.well-known/oauth-protected-resource/mcp;
  the root copy is for clients that look there first.
"""
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET


def authorization_server_metadata() -> dict:
    base = settings.PUBLIC_URL
    return {
        "issuer": base,
        "authorization_endpoint": f"{base}/o/authorize/",
        "token_endpoint": f"{base}/o/token/",
        "revocation_endpoint": f"{base}/o/revoke_token/",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "authorization_response_iss_parameter_supported": True,
        "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
        "scopes_supported": [settings.MCP_SCOPE],
    }


def protected_resource_metadata() -> dict:
    return {
        "resource": f"{settings.PUBLIC_URL}/mcp",
        "authorization_servers": [settings.PUBLIC_URL],
        "scopes_supported": [settings.MCP_SCOPE],
        "bearer_methods_supported": ["header"],
        "resource_name": "Life Agent",
    }


@require_GET
def authorization_server(request):
    return JsonResponse(authorization_server_metadata())


@require_GET
def protected_resource(request):
    return JsonResponse(protected_resource_metadata())


@require_GET
def healthz(request):
    """For the host's health checks. No database access, so it answers even during a migration."""
    return JsonResponse({"ok": True})
