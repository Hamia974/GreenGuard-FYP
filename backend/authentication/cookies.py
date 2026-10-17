"""Setting and clearing the HttpOnly JWT cookies (see docs/AUTHENTICATION.md)."""

from django.conf import settings
from rest_framework_simplejwt.settings import api_settings as jwt_settings


def _cookie_options(path):
    return {
        "path": path,
        "domain": settings.JWT_COOKIE_DOMAIN,
        "secure": settings.JWT_COOKIE_SECURE,
        "httponly": True,
        "samesite": settings.JWT_COOKIE_SAMESITE,
    }


def set_auth_cookies(response, access_token, refresh_token, persistent=True):
    """Attach the access and refresh tokens as HttpOnly cookies.

    ``persistent=False`` ("Remember me" unticked) makes the refresh cookie a
    browser-session cookie, so closing the browser ends the session. The
    token itself still expires server-side after REFRESH_TOKEN_LIFETIME.
    """
    response.set_cookie(
        settings.JWT_ACCESS_COOKIE_NAME,
        str(access_token),
        max_age=int(jwt_settings.ACCESS_TOKEN_LIFETIME.total_seconds()),
        **_cookie_options(settings.JWT_ACCESS_COOKIE_PATH),
    )
    response.set_cookie(
        settings.JWT_REFRESH_COOKIE_NAME,
        str(refresh_token),
        max_age=(
            int(jwt_settings.REFRESH_TOKEN_LIFETIME.total_seconds()) if persistent else None
        ),
        **_cookie_options(settings.JWT_REFRESH_COOKIE_PATH),
    )


def clear_auth_cookies(response):
    for name, path in (
        (settings.JWT_ACCESS_COOKIE_NAME, settings.JWT_ACCESS_COOKIE_PATH),
        (settings.JWT_REFRESH_COOKIE_NAME, settings.JWT_REFRESH_COOKIE_PATH),
    ):
        response.delete_cookie(
            name,
            path=path,
            domain=settings.JWT_COOKIE_DOMAIN,
            samesite=settings.JWT_COOKIE_SAMESITE,
        )
