"""Create (or replace) the OAuth client Claude uses to connect.

    python manage.py create_claude_client

Prints the client ID and secret ONCE. Paste them into Claude:
Settings > Connectors > Add custom connector > OAuth > "Use your own OAuth client".
Never commit them or paste them anywhere else. Running it again replaces the
client, so the old secret stops working (use this to rotate it).
"""
import secrets

from django.conf import settings
from django.core.management.base import BaseCommand
from oauth2_provider.models import get_application_model

NAME = "Claude connector"


class Command(BaseCommand):
    help = "Create or replace the OAuth client for the Claude connector and print its ID and secret once."

    def handle(self, *args, **options):
        Application = get_application_model()
        Application.objects.filter(name=NAME).delete()  # also revokes its tokens

        secret = secrets.token_urlsafe(48)
        app = Application.objects.create(
            name=NAME,
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
            redirect_uris=settings.CLAUDE_REDIRECT_URI,
            client_secret=secret,  # stored hashed; this is the only time it is shown
            skip_authorization=False,
        )

        self.stdout.write(self.style.SUCCESS("Claude connector client created. Copy these now; the secret is not shown again.\n"))
        self.stdout.write(f"  Server URL:     {settings.PUBLIC_URL}/mcp")
        self.stdout.write(f"  Client ID:      {app.client_id}")
        self.stdout.write(f"  Client secret:  {secret}")
        self.stdout.write(f"  Redirect URI:   {settings.CLAUDE_REDIRECT_URI}\n")
