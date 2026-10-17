"""
Django settings for the GreenGuard backend (config project).

See docs/GREEN_GUARD_SYSTEM_SPECIFICATION_V2.md (section 28) and
docs/DATABASE_SPECIFICATION.md for the architectural decisions behind
these settings.
"""

from datetime import timedelta
from pathlib import Path

import os
import sys

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

# True only under `manage.py test` -- disables DRF throttling for that run so
# the fast, back-to-back requests across hundreds of tests (often from the
# same test-client "IP") never trip a rate limit meant for real traffic.
# Rate limiting itself stays fully active outside the test runner.
TESTING = "test" in sys.argv


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def env_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Core / Security
# ---------------------------------------------------------------------------

# Known-insecure values: the code-level fallback used when SECRET_KEY is
# unset at all, plus the literal placeholder shipped in
# backend/.env.example -- both must be rejected, since a real deployment
# forgetting to edit a copied .env.example is the more likely real-world
# mistake than leaving the variable unset outright.
_INSECURE_DEFAULT_SECRET_KEY = "django-insecure-dev-only-do-not-use-in-production"
_KNOWN_PLACEHOLDER_SECRET_KEYS = {
    _INSECURE_DEFAULT_SECRET_KEY,
    "change-me-to-a-long-random-string",
}
_KNOWN_PLACEHOLDER_DATABASE_PASSWORDS = {"", "change-me"}

SECRET_KEY = os.getenv("SECRET_KEY", _INSECURE_DEFAULT_SECRET_KEY)

DEBUG = env_bool("DEBUG", True)

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")

# Fail fast rather than silently deploying with an insecure dev secret or an
# empty/placeholder database password -- both have safe, working defaults in
# backend/.env.example for local development (where DEBUG=True), but should
# never reach a real deployment (DEBUG=False) unchanged. Skipped under the
# test runner so `manage.py test` never needs a production-shaped .env.
if not DEBUG and not TESTING:
    if SECRET_KEY in _KNOWN_PLACEHOLDER_SECRET_KEYS:
        raise ImproperlyConfigured(
            "SECRET_KEY is unset or still a placeholder value. Set a real, "
            "unique SECRET_KEY in the environment before running with "
            "DEBUG=False."
        )
    if os.getenv("DATABASE_PASSWORD", "") in _KNOWN_PLACEHOLDER_DATABASE_PASSWORDS:
        raise ImproperlyConfigured(
            "DATABASE_PASSWORD is unset or still a placeholder value. Set "
            "the real production database password in the environment "
            "before running with DEBUG=False."
        )

# Production-only hardening, per GREEN_GUARD_SYSTEM_SPECIFICATION_V2.md
# section 30.7 ("HTTPS Communication... must use HTTPS in production") and
# section 30.20. Left off whenever DEBUG=True so local HTTP development is
# unaffected -- these settings actively break plain-HTTP access (redirects,
# cookies marked Secure) which is only correct once TLS is actually in front
# of the deployed app.
if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
]

# GreenGuard business apps (authentication, users, farms, predictions,
# dashboard, notifications, adminpanel, ai_services, weather, common) are
# registered here as they are created in their respective roadmap phases.
LOCAL_APPS: list[str] = [
    "authentication",
    "users",
    "farms",
    "dashboard",
    "weather",
    "predictions",
    "ai_services",
    "module1",
    "module2",
    "history",
    "notifications",
    "adminpanel",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

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


# ---------------------------------------------------------------------------
# Database (PostgreSQL only, per DATABASE_SPECIFICATION.md)
# ---------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DATABASE_NAME", "greenguard_db"),
        "USER": os.getenv("DATABASE_USER", "postgres"),
        "PASSWORD": os.getenv("DATABASE_PASSWORD", ""),
        "HOST": os.getenv("DATABASE_HOST", "localhost"),
        "PORT": os.getenv("DATABASE_PORT", "5432"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "users.User"


# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Static & Media files
# ---------------------------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB, per REST_API_SPEC.md upload limit
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024


# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    # Reads the JWT from the HttpOnly access cookie (with CSRF enforcement)
    # or, for non-browser clients, the Authorization: Bearer header -- see
    # authentication/backends.py and docs/AUTHENTICATION.md.
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "authentication.backends.CookieJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    "DEFAULT_THROTTLE_CLASSES": (
        ()
        if TESTING
        else (
            "rest_framework.throttling.AnonRateThrottle",
            "rest_framework.throttling.UserRateThrottle",
        )
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("THROTTLE_RATE_ANON", "30/min"),
        "user": os.getenv("THROTTLE_RATE_USER", "120/min"),
        # Stricter scope applied only to auth endpoints (register/login/
        # forgot-password/reset-password) -- see authentication/views.py.
        "auth": os.getenv("THROTTLE_RATE_AUTH", "10/min"),
        # Token refresh is called by every open tab roughly once per access-
        # token lifetime, so it gets its own, more generous scope.
        "auth_refresh": os.getenv("THROTTLE_RATE_AUTH_REFRESH", "30/min"),
        # Farm-form address lookup -- see farms/views.py FarmGeocodeView.
        "geocode": os.getenv("THROTTLE_RATE_GEOCODE", "20/min"),
    },
}

SIMPLE_JWT = {
    # Kept short because logout cannot revoke an already-issued access token
    # (docs/AUTHENTICATION.md section 5); this caps how long a copied one works.
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=int(os.getenv("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", "10"))
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=int(os.getenv("JWT_REFRESH_TOKEN_LIFETIME_DAYS", "7"))
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    # Embeds a hash of the user's password hash in every token and rejects
    # access tokens whose hash no longer matches, so a password change or
    # reset revokes already-issued access tokens immediately (refresh tokens
    # are checked in authentication.serializers). Costs no extra query: the
    # user row is already loaded per request.
    "CHECK_REVOKE_TOKEN": True,
    "SIGNING_KEY": os.getenv("JWT_SECRET", SECRET_KEY),
    "AUTH_HEADER_TYPES": ("Bearer",),
}


# ---------------------------------------------------------------------------
# JWT cookies (browser sessions -- see docs/AUTHENTICATION.md)
# ---------------------------------------------------------------------------

# The browser never sees the JWTs: login/refresh set them as HttpOnly
# cookies, so they are unreachable from JavaScript (and so from XSS) and are
# never written to localStorage/sessionStorage. The refresh cookie is scoped
# to the auth endpoints only, so it is not sent with every API request.
JWT_ACCESS_COOKIE_NAME = "gg_access"
JWT_REFRESH_COOKIE_NAME = "gg_refresh"
JWT_ACCESS_COOKIE_PATH = "/api/"
JWT_REFRESH_COOKIE_PATH = "/api/v1/auth/"
# Lax works whenever the frontend and API share a registrable domain
# (localhost:3000 -> localhost:8000, or app.example.com -> api.example.com).
# "None" is only needed for a fully cross-site deployment and requires HTTPS.
JWT_COOKIE_SAMESITE = os.getenv("JWT_COOKIE_SAMESITE", "Lax")
JWT_COOKIE_SECURE = env_bool("JWT_COOKIE_SECURE", not DEBUG)
# Leave unset for host-only cookies; set to e.g. ".example.com" only if the
# frontend and API live on different subdomains and need to share the CSRF
# cookie.
JWT_COOKIE_DOMAIN = os.getenv("JWT_COOKIE_DOMAIN") or None

if JWT_COOKIE_SAMESITE not in ("Lax", "Strict", "None"):
    raise ImproperlyConfigured("JWT_COOKIE_SAMESITE must be one of Lax, Strict or None.")
if JWT_COOKIE_SAMESITE == "None" and not JWT_COOKIE_SECURE:
    raise ImproperlyConfigured("JWT_COOKIE_SAMESITE=None requires JWT_COOKIE_SECURE=True (HTTPS).")


# ---------------------------------------------------------------------------
# CORS (frontend origins only, per REST_API_SPEC.md section 30.13)
# ---------------------------------------------------------------------------

# Explicit origins only -- credentials (cookies) are allowed, so a wildcard
# origin must never be used here.
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
CORS_ALLOW_CREDENTIALS = True

if "*" in CORS_ALLOWED_ORIGINS:
    raise ImproperlyConfigured("CORS_ALLOWED_ORIGINS must list explicit origins, not '*'.")

# ---------------------------------------------------------------------------
# CSRF
# ---------------------------------------------------------------------------

# Cookie-authenticated API requests are CSRF-protected the same way Django
# protects its own forms: the frontend fetches a token from
# GET /api/v1/auth/csrf/ and echoes it in the X-CSRFToken header on every
# unsafe request (authentication/backends.py). Origin checking uses this
# list, which defaults to the trusted frontend origin(s) in
# CORS_ALLOWED_ORIGINS; the Django admin at /admin/ relies on it too.
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", ",".join(CORS_ALLOWED_ORIGINS))
CSRF_COOKIE_SAMESITE = JWT_COOKIE_SAMESITE
CSRF_COOKIE_SECURE = JWT_COOKIE_SECURE
CSRF_COOKIE_DOMAIN = JWT_COOKIE_DOMAIN

# Signed, stateless email-verification links (authentication/tokens.py).
EMAIL_VERIFICATION_MAX_AGE_HOURS = int(os.getenv("EMAIL_VERIFICATION_MAX_AGE_HOURS", "48"))


# ---------------------------------------------------------------------------
# Email (used by the forgot-password flow)
# ---------------------------------------------------------------------------

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@greenguard.local")

# Base URL of the Next.js frontend, used to build links (e.g. password reset).
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")


# ---------------------------------------------------------------------------
# AI Integration & External Services
# ---------------------------------------------------------------------------

# When True, ai_services returns fixture responses instead of calling the
# real AI endpoints. Response shape must still match REST_API_SPEC.md exactly.
ENABLE_MOCK_AI = env_bool("ENABLE_MOCK_AI", True)

# Module 3 (Weather Risk Engine) -- the real ai/Weather_Module FastAPI
# microservice (Open-Meteo + rule engine + optional LSTM forecast), not
# called directly by the frontend. Defaults match that module's own
# README/.env.example (PORT=8001). Timeout is generous because the module's
# own documented worst case, with its internal retries against Open-Meteo,
# is ~30-45 seconds (see its docs/MODEL_DOCUMENTATION.md "Remaining known
# limitations").
WEATHER_MODULE_URL = os.getenv("WEATHER_MODULE_URL", "http://localhost:8001")
WEATHER_MODULE_REQUEST_TIMEOUT_SECONDS = int(os.getenv("WEATHER_MODULE_REQUEST_TIMEOUT_SECONDS", "45"))
WEATHER_MODULE_HEALTH_TIMEOUT_SECONDS = int(os.getenv("WEATHER_MODULE_HEALTH_TIMEOUT_SECONDS", "3"))

# Module 2 (Soil & Nutrient / "Stress Module") -- the real ai/Stress_Module
# FastAPI microservice (Module 2A nutrient-risk ML + Module 2B pH/moisture/
# light rules, combined by its own orchestrator). Not called directly by the
# frontend. Defaults match that module's own README/.env.example (PORT=8002).
STRESS_MODULE_URL = os.getenv("STRESS_MODULE_URL", "http://localhost:8002")
STRESS_MODULE_REQUEST_TIMEOUT_SECONDS = int(os.getenv("STRESS_MODULE_REQUEST_TIMEOUT_SECONDS", "30"))
STRESS_MODULE_HEALTH_TIMEOUT_SECONDS = int(os.getenv("STRESS_MODULE_HEALTH_TIMEOUT_SECONDS", "3"))

# Module 1 (Disease Detection) -- the AI team's real, live "Disease Module"
# service (see ai/API_CONTRACT.md), currently deployed on Render. Not called
# directly by the frontend. Used by both the standalone Disease Check
# (POST /api/v1/module1/analyze/) and Quick Scan
# (POST /api/v1/predictions/analyze/). Timeout defaults to 60s per
# the contract's own "Cold start" guidance (free-tier Render instance can
# take 30s+ to wake up); the client itself retries once on timeout or 503.
DISEASE_MODULE_URL = os.getenv("DISEASE_MODULE_URL", "http://localhost:8003")
DISEASE_MODULE_REQUEST_TIMEOUT_SECONDS = int(os.getenv("DISEASE_MODULE_REQUEST_TIMEOUT_SECONDS", "60"))
DISEASE_MODULE_HEALTH_TIMEOUT_SECONDS = int(os.getenv("DISEASE_MODULE_HEALTH_TIMEOUT_SECONDS", "5"))

# Shared secret required by every Module 1 `/v1/*` request as the `X-API-Key`
# header (ai/API_CONTRACT.md). Never logged, never sent to the frontend, and
# never given a real value here or in .env.example -- only in the untracked
# local .env / the production host's own secret store.
GREENGUARD_API_KEY = os.getenv("GREENGUARD_API_KEY", "")

# Farm-form forward geocoding (address -> coordinates), see farms/geocoding.py.
# Not an AI module and unrelated to ENABLE_MOCK_AI. "open_meteo" needs no key
# (free for non-commercial use); "google" needs a server-side Geocoding API
# key that is never sent to the frontend.
GEOCODING_PROVIDER = os.getenv("GEOCODING_PROVIDER", "open_meteo").strip().lower()
GEOCODING_COUNTRY_CODE = os.getenv("GEOCODING_COUNTRY_CODE", "PK").strip().upper()
GEOCODING_REQUEST_TIMEOUT_SECONDS = int(os.getenv("GEOCODING_REQUEST_TIMEOUT_SECONDS", "10"))
GOOGLE_MAPS_GEOCODING_API_KEY = os.getenv("GOOGLE_MAPS_GEOCODING_API_KEY", "")


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} [{levelname}] {name}: {message}",
            "style": "{",
        },
        "simple": {
            "format": "[{levelname}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "greenguard.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "greenguard": {
            "handlers": ["console", "file"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}
