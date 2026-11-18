"""Checks the OAuth token on every request to /mcp.

The MCP SDK calls `verify_token` with the Bearer token from the request. A
token is accepted only if this server issued it (django-oauth-toolkit), it has
not expired, it carries the "mcp" scope, and it belongs to an active staff
account (you). Anything else gets a 401 from the SDK, which also tells Claude
where to sign in.

This server only issues tokens for its own /mcp, so a valid token here was
issued for this resource (the audience check the MCP auth spec asks for).
"""
import hashlib

from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import close_old_connections, connections
from mcp.server.auth.provider import AccessToken
from oauth2_provider.models import get_access_token_model


class DjangoTokenVerifier:
    async def verify_token(self, token: str) -> AccessToken | None:
        return await sync_to_async(_checked_lookup)(token)


def _checked_lookup(token: str) -> AccessToken | None:
    """lookup_token with this thread's database connection closed afterwards."""
    close_old_connections()
    try:
        return lookup_token(token)
    finally:
        connections.close_all()  # this worker thread's connections only


def lookup_token(token: str) -> AccessToken | None:
    if not token:
        return None
    # Tokens are stored hashed (RFC 9700) and looked up by their SHA-256 checksum, the same way
    # django-oauth-toolkit does. Only the real token has that checksum.
    checksum = hashlib.sha256(token.encode("utf-8")).hexdigest()
    found = (get_access_token_model().objects.select_related("user", "application")
             .filter(token_checksum=checksum).first())
    if found is None:
        return None
    if not found.is_valid([settings.MCP_SCOPE]):
        return None
    if found.user is None or not (found.user.is_active and found.user.is_staff):
        return None
    return AccessToken(
        token=token,
        client_id=found.application.client_id if found.application else "",
        scopes=found.scope.split(),
        expires_at=int(found.expires.timestamp()),
        resource=f"{settings.PUBLIC_URL}/mcp",
        subject=str(found.user.pk),
    )
