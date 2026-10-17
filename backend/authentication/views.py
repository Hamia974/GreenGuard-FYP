import logging

from django.conf import settings
from django.core.mail import send_mail
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User

from .backends import enforce_csrf
from .cookies import clear_auth_cookies, set_auth_cookies
from .serializers import (
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    PasswordBoundTokenRefreshSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    VerifyEmailSerializer,
)
from .tokens import (
    consume_email_verification_token,
    generate_email_verification_token,
    generate_reset_token,
    revoke_all_refresh_tokens,
    verify_reset_token,
)

logger = logging.getLogger("greenguard")

# Applied to the AllowAny endpoints most exposed to brute-forcing
# (register/login/forgot-password/reset-password/verify-email). Empty under
# the test runner -- see settings.TESTING -- so the hundreds of same-"IP"
# requests across the test suite never trip the limit meant for real traffic.
_AUTH_THROTTLE_CLASSES = [] if settings.TESTING else [ScopedRateThrottle]

# Claim stored in the refresh token recording the "Remember me" choice, so a
# rotated refresh cookie keeps the same lifetime as the original one.
REMEMBER_ME_CLAIM = "remember_me"


def _validation_error(serializer):
    return Response(
        {
            "success": False,
            "message": "Validation failed.",
            "errors": serializer.errors,
        },
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


def _user_payload(user):
    return {
        "user_id": str(user.id),
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role.capitalize(),
        "is_verified": user.is_verified,
    }


def _issue_tokens(response, user, remember_me):
    refresh = RefreshToken.for_user(user)
    refresh[REMEMBER_ME_CLAIM] = remember_me
    set_auth_cookies(response, refresh.access_token, refresh, persistent=remember_me)


def _remember_me_from_cookie(request):
    raw_refresh = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
    if not raw_refresh:
        return True
    try:
        return bool(RefreshToken(raw_refresh).payload.get(REMEMBER_ME_CLAIM, True))
    except TokenError:
        return True


def _send_link_email(user, subject, intro, link, expiry_note, log_label):
    try:
        send_mail(
            subject=subject,
            message=(
                f"{intro}\n\n{link}\n\n{expiry_note} "
                "If you didn't request this, you can ignore this email."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )
    except Exception as exc:  # noqa: BLE001 - any SMTP/backend failure
        # Logged so delivery problems are visible to operators, but without
        # the link (it carries a live token) or the exception message (SMTP
        # errors can echo the message body). The API response is unchanged,
        # so forgot-password still never reveals whether an account exists.
        logger.error(
            "Failed to send %s email to %s (%s).",
            log_label,
            user.email,
            type(exc).__name__,
        )

    # The console email backend quoted-printable-encodes long body lines
    # (wrapping them and escaping "=" as "=3D"), which mangles the link when
    # copied from the terminal. Print the raw, unwrapped link separately so
    # it stays copy-pasteable in dev.
    if settings.EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend":
        logger.info(
            "DEV MODE %s link for %s (copy/paste into browser): %s",
            log_label,
            user.email,
            link,
        )


def _send_verification_email(user):
    token = generate_email_verification_token(user)
    _send_link_email(
        user,
        subject="Verify your GreenGuard email address",
        intro="Confirm your email address for your GreenGuard account:",
        link=f"{settings.FRONTEND_BASE_URL}/verify-email?token={token}",
        expiry_note=f"This link expires in {settings.EMAIL_VERIFICATION_MAX_AGE_HOURS} hours.",
        log_label="email verification",
    )


class CsrfTokenView(APIView):
    """GET /api/v1/auth/csrf/ -- issues the CSRF cookie and returns the
    matching token, which the frontend sends back in the X-CSRFToken header
    on every unsafe request. Returned in the body because the frontend and
    API may be on different origins, where the cookie isn't readable."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "success": True,
                "message": "CSRF token issued.",
                "data": {"csrf_token": get_token(request)},
            }
        )


class RegisterView(APIView):
    """POST /api/v1/auth/register/"""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = _AUTH_THROTTLE_CLASSES
    throttle_scope = "auth"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer)

        user = serializer.save()
        logger.info("New user registered: %s", user.email)
        _send_verification_email(user)

        return Response(
            {
                "success": True,
                "message": "User registered successfully.",
                "data": {
                    "user_id": str(user.id),
                    "full_name": user.full_name,
                    "email": user.email,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """POST /api/v1/auth/login/ -- sets the HttpOnly JWT cookies; the tokens
    are never returned in the body."""

    # Ignore any stale access cookie: logging in must work even when the
    # previous session's token has expired.
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = _AUTH_THROTTLE_CLASSES
    throttle_scope = "auth"

    def post(self, request):
        # Login CSRF: stops a third-party page from silently signing the
        # browser into an attacker-controlled account.
        enforce_csrf(request)

        serializer = LoginSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(
                {"success": False, "message": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user = serializer.validated_data["user"]
        logger.info("User logged in: %s", user.email)

        response = Response(
            {
                "success": True,
                "message": "Login successful.",
                "data": {"user": _user_payload(user)},
            }
        )
        _issue_tokens(response, user, serializer.validated_data["remember_me"])
        return response


class LogoutView(APIView):
    """POST /api/v1/auth/logout/ -- blacklists the refresh token and clears
    both cookies. Works with an expired access token, so a stale session can
    always be ended; CSRF-protected so other sites cannot log the user out."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        enforce_csrf(request)

        raw_refresh = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
        if raw_refresh:
            try:
                RefreshToken(raw_refresh).blacklist()
            except TokenError:
                pass

        response = Response({"success": True, "message": "Logout successful."})
        clear_auth_cookies(response)
        return response


class RefreshView(APIView):
    """POST /api/v1/auth/refresh/ -- rotates the refresh token (the old one
    is blacklisted, so a replayed token is rejected) and re-sets both
    cookies."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [] if settings.TESTING else [ScopedRateThrottle]
    throttle_scope = "auth_refresh"

    def post(self, request):
        enforce_csrf(request)

        raw_refresh = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
        try:
            if not raw_refresh:
                raise TokenError("No refresh token.")
            remember_me = bool(RefreshToken(raw_refresh).payload.get(REMEMBER_ME_CLAIM, True))
            serializer = PasswordBoundTokenRefreshSerializer(data={"refresh": raw_refresh})
            serializer.is_valid(raise_exception=True)
        except (TokenError, AuthenticationFailed, User.DoesNotExist):
            response = Response(
                {"success": False, "message": "Invalid or expired refresh token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            clear_auth_cookies(response)
            return response

        response = Response({"success": True, "message": "Token refreshed successfully."})
        set_auth_cookies(
            response,
            serializer.validated_data["access"],
            serializer.validated_data["refresh"],
            persistent=remember_me,
        )
        return response


class ForgotPasswordView(APIView):
    """POST /api/v1/auth/forgot-password/"""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = _AUTH_THROTTLE_CLASSES
    throttle_scope = "auth"

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer)

        email = serializer.validated_data["email"]
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user is not None:
            token = generate_reset_token(user)
            _send_link_email(
                user,
                subject="Reset your GreenGuard password",
                intro="We received a request to reset your GreenGuard password. Reset it here:",
                link=f"{settings.FRONTEND_BASE_URL}/reset-password?token={token}",
                expiry_note="This link expires in 1 hour and can only be used once.",
                log_label="reset",
            )
            logger.info("Password reset requested for %s", user.email)

        # Always return success to avoid leaking which emails are registered.
        return Response(
            {
                "success": True,
                "message": "Password reset instructions sent to your email.",
            }
        )


class ResetPasswordView(APIView):
    """POST /api/v1/auth/reset-password/"""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = _AUTH_THROTTLE_CLASSES
    throttle_scope = "auth"

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer)

        user = verify_reset_token(serializer.validated_data["token"])
        if user is None or not user.is_active:
            return Response(
                {
                    "success": False,
                    "message": "Reset link is invalid or has expired.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        # Whoever triggered the reset may not hold the account's other
        # sessions -- sign every device out.
        revoke_all_refresh_tokens(user)
        logger.info("Password reset completed for %s", user.email)

        return Response({"success": True, "message": "Password reset successful."})


class ChangePasswordView(APIView):
    """POST /api/v1/auth/change-password/ -- signs out every other device
    and re-issues this browser's cookies so the current session continues."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return _validation_error(serializer)

        user = request.user
        remember_me = _remember_me_from_cookie(request)
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        revoke_all_refresh_tokens(user)
        logger.info("Password changed for %s", user.email)

        response = Response({"success": True, "message": "Password changed successfully."})
        _issue_tokens(response, user, remember_me)
        return response


class VerifyEmailView(APIView):
    """POST /api/v1/auth/verify-email/ -- consumes the signed link sent at
    registration. Single-use: once the account is verified, this and every
    other link issued for it is rejected like an invalid one."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = _AUTH_THROTTLE_CLASSES
    throttle_scope = "auth"

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer)

        user = consume_email_verification_token(serializer.validated_data["token"])
        if user is None:
            return Response(
                {
                    "success": False,
                    "message": "Verification link is invalid or has expired.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info("Email verified for %s", user.email)
        return Response({"success": True, "message": "Email verified successfully."})


class ResendVerificationView(APIView):
    """POST /api/v1/auth/resend-verification/ -- re-sends the verification
    link to the signed-in user's own address."""

    permission_classes = [IsAuthenticated]
    throttle_classes = _AUTH_THROTTLE_CLASSES
    throttle_scope = "auth"

    def post(self, request):
        user = request.user
        if user.is_verified:
            return Response({"success": True, "message": "Email is already verified."})

        _send_verification_email(user)
        return Response({"success": True, "message": "Verification email sent."})
