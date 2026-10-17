from django.conf import settings
from rest_framework import exceptions
from rest_framework.authentication import CSRFCheck
from rest_framework_simplejwt.authentication import JWTAuthentication

# Matched verbatim by the frontend API client (lib/api-client.ts), which
# re-fetches its CSRF token once and retries when it sees this message.
CSRF_FAILED_MESSAGE = "CSRF verification failed."


def enforce_csrf(request):
    """Runs Django's own CSRF validation (Origin/Referer + token checks)
    against a DRF request -- the same approach DRF's SessionAuthentication
    uses. Honours the test client's ``enforce_csrf_checks`` switch."""

    def dummy_get_response(_request):  # pragma: no cover - never called
        return None

    check = CSRFCheck(dummy_get_response)
    check.process_request(request)
    reason = check.process_view(request, None, (), {})
    if reason:
        raise exceptions.PermissionDenied(CSRF_FAILED_MESSAGE)


class CookieJWTAuthentication(JWTAuthentication):
    """Simple JWT authentication that also accepts the HttpOnly access cookie.

    - ``Authorization: Bearer <token>`` is checked first (non-browser
      clients). A header cannot be attached by a cross-site page, so no CSRF
      check is needed for it. An invalid or expired Bearer token is rejected
      outright (401) rather than silently falling back to the cookie.
    - Otherwise the ``gg_access`` cookie set by login/refresh is used, and
      because browsers attach cookies automatically, every cookie-
      authenticated request is CSRF-validated. A non-Bearer Authorization
      header (e.g. ``Basic`` from a password-protected staging proxy) does
      not stop the cookie from being used.

    Token validation, expiry, the inactive-user check and blacklist-aware
    user lookup are all inherited unchanged from JWTAuthentication.
    """

    def authenticate(self, request):
        header = self.get_header(request)
        if header is not None and self.get_raw_token(header) is not None:
            return super().authenticate(request)

        raw_token = request.COOKIES.get(settings.JWT_ACCESS_COOKIE_NAME)
        if not raw_token:
            return None

        validated_token = self.get_validated_token(raw_token.encode())
        user = self.get_user(validated_token)
        enforce_csrf(request)
        return user, validated_token
