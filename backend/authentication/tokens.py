"""
Stateless password-reset and single-use email-verification tokens, plus
refresh-token revocation.

DATABASE_SPECIFICATION.md has no table for password-reset tokens, so the
token itself carries everything needed to validate it (signed + time-limited),
instead of persisting a row. Binding a slice of the current password hash
means the token is automatically invalidated once the password changes --
which also makes it single-use, since using it changes the password.
"""

from django.conf import settings
from django.core import signing
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from users.models import User

RESET_TOKEN_SALT = "greenguard-password-reset"
RESET_TOKEN_MAX_AGE_SECONDS = 60 * 60  # 1 hour

VERIFY_EMAIL_TOKEN_SALT = "greenguard-verify-email"


def generate_reset_token(user: User) -> str:
    payload = {"user_id": str(user.id), "pw": user.password[-16:]}
    return signing.dumps(payload, salt=RESET_TOKEN_SALT)


def verify_reset_token(token: str) -> User | None:
    try:
        payload = signing.loads(
            token, salt=RESET_TOKEN_SALT, max_age=RESET_TOKEN_MAX_AGE_SECONDS
        )
    except signing.BadSignature:
        return None

    try:
        user = User.objects.get(id=payload["user_id"])
    except (User.DoesNotExist, ValueError, KeyError):
        return None

    if user.password[-16:] != payload.get("pw"):
        return None

    return user


def generate_email_verification_token(user: User) -> str:
    """Binds the address being verified, so a link stops working if the
    account's email is ever changed before it is used."""
    return signing.dumps(
        {"user_id": str(user.id), "email": user.email.lower()},
        salt=VERIFY_EMAIL_TOKEN_SALT,
    )


def consume_email_verification_token(token: str) -> User | None:
    """Marks the token's account verified and returns it, or None if the
    token is invalid, expired, bound to another address -- or already used.

    Single-use without a token table: the link is only accepted while the
    account is unverified, and the flip is a conditional UPDATE, so of two
    concurrent requests with the same link exactly one succeeds. Every later
    attempt -- with this link or any other issued for the account -- fails.
    """
    try:
        payload = signing.loads(
            token,
            salt=VERIFY_EMAIL_TOKEN_SALT,
            max_age=settings.EMAIL_VERIFICATION_MAX_AGE_HOURS * 60 * 60,
        )
    except signing.BadSignature:
        return None

    try:
        user = User.objects.get(id=payload["user_id"])
    except (User.DoesNotExist, ValueError, KeyError):
        return None

    if user.email.lower() != payload.get("email"):
        return None

    consumed = User.objects.filter(pk=user.pk, is_verified=False).update(
        is_verified=True, updated_at=timezone.now()
    )
    if not consumed:
        return None

    user.is_verified = True
    return user


def revoke_all_refresh_tokens(user: User) -> None:
    """Blacklists every outstanding refresh token for ``user`` -- signs the
    account out on all devices once their short-lived access token expires.
    Used after a password reset or change."""
    outstanding = OutstandingToken.objects.filter(user=user, blacklistedtoken__isnull=True)
    BlacklistedToken.objects.bulk_create(
        [BlacklistedToken(token=token) for token in outstanding],
        ignore_conflicts=True,
    )
