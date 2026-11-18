from django.contrib import admin
from django.urls import include, path
from oauth2_provider import views as oauth_views

from agent import oauth
from agent import views as agent_views
from data import views

# Only the OAuth endpoints Claude needs. django-oauth-toolkit's app-registration pages are left out.
oauth_patterns = ([
    path("authorize/", oauth_views.AuthorizationView.as_view(), name="authorize"),
    path("token/", oauth_views.TokenView.as_view(), name="token"),
    path("revoke_token/", oauth_views.RevokeTokenView.as_view(), name="revoke-token"),
], "oauth2_provider")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz", oauth.healthz),

    # Sign-in for the Claude connector (the MCP server itself is mounted at /mcp in config/asgi.py)
    path("o/", include(oauth_patterns)),
    path(".well-known/oauth-authorization-server", oauth.authorization_server),
    path(".well-known/oauth-protected-resource", oauth.protected_resource),

    # Local JSON API for the Next.js pages (turned off in production, see config/middleware.py)
    path("api/report", views.report),
    path("api/forecast", agent_views.forecast),
    path("api/brief", agent_views.brief),
    path("api/chat", agent_views.chat),  # POST, runs the agent
    path("api/suggestions", agent_views.save_suggestion),  # POST, the user added a suggestion
]
