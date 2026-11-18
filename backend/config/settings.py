"""Django settings for the Personal Life Agent backend.

All secrets and environment-specific values come from env vars (see .env.example).
"""
import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent

load_dotenv(REPO_ROOT / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).lower() in {"1", "true", "yes"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


# PRODUCTION=true on the hosted server (render.yaml). Locally it is off.
PRODUCTION = env_bool("PRODUCTION")
DEV_SECRET_KEY = "dev-only-insecure-key"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", DEV_SECRET_KEY)
DEBUG = env_bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

# Render sets RENDER_EXTERNAL_HOSTNAME (e.g. life-agent.onrender.com) on web services.
RENDER_HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "")
if RENDER_HOST:
    ALLOWED_HOSTS.append(RENDER_HOST)
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_HOST}")

# The server's public address, e.g. https://life-agent.onrender.com. OAuth and MCP metadata use it.
PUBLIC_URL = (os.environ.get("PUBLIC_URL")
              or (f"https://{RENDER_HOST}" if RENDER_HOST else "http://localhost:8000")).rstrip("/")

# The local JSON API (/api/...) used by the Next.js pages. Off in production: those endpoints have no
# login, so on a public server they would expose data and spend the model quota. Claude uses /mcp.
API_ENABLED = env_bool("API_ENABLED", default=not PRODUCTION)

if PRODUCTION:
    if SECRET_KEY == DEV_SECRET_KEY or DEBUG:
        raise ImproperlyConfigured("In production set DJANGO_SECRET_KEY and keep DJANGO_DEBUG off.")
    if not PUBLIC_URL.startswith("https://"):
        raise ImproperlyConfigured("In production PUBLIC_URL must be the https:// address of the server.")
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")  # Render terminates HTTPS
    SECURE_SSL_REDIRECT = True
    SECURE_REDIRECT_EXEMPT = [r"^healthz$"]
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "oauth2_provider",
    "data",
    "agent",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "config.middleware.api_gate",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if PRODUCTION:  # serve the login page's CSS/JS from the app itself (collectstatic runs at build time)
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.app"

# Postgres. Locally this is the docker-compose container; in production it is
# the hosted database's connection string.
DATABASES = {
    "default": dj_database_url.config(
        env="DATABASE_URL",
        default="postgres://postgres:postgres@localhost:5432/life_agent",
        conn_max_age=60,
    )
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Timestamps are stored in UTC. The user's own timezone is only used to derive
# each record's `local_date`.
TIME_ZONE = "UTC"
USE_TZ = True
USER_TIME_ZONE = os.environ.get("USER_TIME_ZONE", "America/Chicago")

# Pins "today" for demos on the synthetic dataset (e.g. 2026-11-16). Unset = the real date.
DEMO_TODAY = os.environ.get("DEMO_TODAY") or None

# The agent's OpenRouter key (school key). Put it in the repo-root .env (git-ignored), never in code:
#   OPENROUTER_API_KEY=sk-or-...
# Only the backend reads it; it is never sent to the frontend or written to logs.
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api"  # OpenRouter's Anthropic-compatible endpoint
AGENT_MODEL = os.environ.get("AGENT_MODEL") or "anthropic/claude-opus-5.5"

LANGUAGE_CODE = "en-us"
USE_I18N = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
                    if PRODUCTION else "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# ---------- Sign-in for the Claude connector (OAuth 2.1, django-oauth-toolkit) ----------
# You sign in on the Django admin login page; only staff accounts can. Claude gets a token
# with the single "mcp" scope, which /mcp checks on every request (agent/mcp_auth.py).
LOGIN_URL = "/admin/login/"
MCP_SCOPE = "mcp"
OAUTH2_PROVIDER = {
    "SCOPES": {MCP_SCOPE: "Read your Life Agent summaries and ask your agent questions"},
    "DEFAULT_SCOPES": [MCP_SCOPE],
    "PKCE_REQUIRED": True,
    "ACCESS_TOKEN_EXPIRE_SECONDS": 60 * 60,             # 1 hour; Claude refreshes it
    "REFRESH_TOKEN_EXPIRE_SECONDS": 60 * 60 * 24 * 30,  # 30 days, then sign in again
    "ROTATE_REFRESH_TOKEN": True,
    "REFRESH_TOKEN_REUSE_PROTECTION": True,  # a replayed refresh token revokes the whole family
    "ALLOWED_REDIRECT_URI_SCHEMES": ["https"] if PRODUCTION else ["http", "https"],
    "OIDC_ISS_ENDPOINT": PUBLIC_URL,  # the `iss` sent back after sign-in must match our metadata
    # OAuth 2.0 Security Best Current Practice (RFC 9700): no implicit or password grants, S256-only
    # PKCE, tokens only in the Authorization header, `iss` in the sign-in response, tokens stored hashed.
    "COMPLIANT_BCP_RFC9700_IMPLICIT_GRANT": True,
    "COMPLIANT_BCP_RFC9700_PASSWORD_GRANT": True,
    "COMPLIANT_BCP_RFC9700_PKCE_METHOD": True,
    "COMPLIANT_BCP_RFC9700_ACCESS_TOKEN_TRANSPORT": True,
    "COMPLIANT_BCP_RFC9700_AUTHZ_RESPONSE_ISS": True,
    "COMPLIANT_BCP_RFC9700_TOKEN_STORAGE": True,
    "COMPLIANT_BCP_RFC9700_REFRESH_TOKEN": True,
    "COMPLIANT_BCP_RFC9700_REDIRECT_URI_SCHEME": PRODUCTION,
    "COMPLIANT_BCP_RFC9700_REDIRECT_URI_MATCHING": True,
    "COMPLIANT_BCP_RFC9700_PKCE_REQUIRED": True,
}
CLAUDE_REDIRECT_URI = "https://claude.ai/api/mcp/auth_callback"

# Connector limits: keep agent runs short enough for Claude, and protect the school quota.
MCP_AGENT_MAX_STEPS = int(os.environ.get("MCP_AGENT_MAX_STEPS", "6"))
MCP_DAILY_ASK_LIMIT = int(os.environ.get("MCP_DAILY_ASK_LIMIT", "40"))
