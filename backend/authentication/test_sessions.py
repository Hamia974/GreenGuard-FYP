"""Cookie-based JWT sessions: login/logout/refresh, CSRF, expiry, password
reset/change revocation and email verification (docs/AUTHENTICATION.md)."""

import re
import time
from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.core import mail, signing
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from users.models import User

from .tokens import (
    VERIFY_EMAIL_TOKEN_SALT,
    generate_email_verification_token,
    generate_reset_token,
)

PASSWORD = "StrongPass123!"
NEW_PASSWORD = "NewStrongPass456!"
ACCESS = settings.JWT_ACCESS_COOKIE_NAME
REFRESH = settings.JWT_REFRESH_COOKIE_NAME


def make_user(email="farmer@example.com", **extra):
    return User.objects.create_user(
        email=email, password=PASSWORD, first_name="Hamia", last_name="Khalil", **extra
    )


class SessionTestCase(APITestCase):
    def setUp(self):
        self.user = make_user()

    def login(self, client=None, **extra):
        client = client or self.client
        payload = {"email": self.user.email, "password": PASSWORD, **extra}
        response = client.post(reverse("auth-login"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response

    def assert_cookie_cleared(self, response, name):
        self.assertIn(name, response.cookies)
        self.assertEqual(response.cookies[name].value, "")
        self.assertEqual(int(response.cookies[name]["max-age"]), 0)


class RegistrationTests(SessionTestCase):
    url = reverse("auth-register")

    def _payload(self, **overrides):
        payload = {
            "full_name": "Ali Khan",
            "email": "Ali@Example.com",
            "password": PASSWORD,
            "confirm_password": PASSWORD,
        }
        payload.update(overrides)
        return payload

    def test_valid_registration_hashes_password_and_sends_verification(self):
        response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="ali@example.com")
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))
        self.assertFalse(user.is_verified)
        self.assertEqual(user.role, User.Role.FARMER)
        self.assertNotIn("password", response.data["data"])
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/verify-email?token=", mail.outbox[0].body)

    def test_registration_does_not_start_a_session(self):
        response = self.client.post(self.url, self._payload(), format="json")
        self.assertNotIn(ACCESS, response.cookies)
        self.assertNotIn(REFRESH, response.cookies)

    def test_duplicate_email_rejected_case_insensitively(self):
        response = self.client.post(
            self.url, self._payload(email="FARMER@example.com"), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("email", response.data["errors"])

    def test_invalid_registrations_rejected(self):
        cases = [
            self._payload(email="not-an-email"),
            self._payload(password="short", confirm_password="short"),
            self._payload(password="password123", confirm_password="password123"),
            self._payload(confirm_password="Different123!"),
            self._payload(full_name=""),
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                response = self.client.post(self.url, payload, format="json")
                self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertFalse(User.objects.filter(email="ali@example.com").exists())

    def test_client_cannot_self_assign_admin_role(self):
        self.client.post(self.url, self._payload(role="admin", is_verified=True), format="json")
        user = User.objects.get(email="ali@example.com")
        self.assertEqual(user.role, User.Role.FARMER)
        self.assertFalse(user.is_verified)


class LoginTests(SessionTestCase):
    url = reverse("auth-login")

    def test_valid_login_sets_httponly_cookies_and_no_tokens_in_body(self):
        response = self.login()

        self.assertEqual(response.data["data"]["user"]["email"], self.user.email)
        self.assertNotIn("access_token", response.data["data"])
        self.assertNotIn("refresh_token", response.data["data"])

        access, refresh = response.cookies[ACCESS], response.cookies[REFRESH]
        for cookie in (access, refresh):
            self.assertTrue(cookie["httponly"])
            self.assertEqual(cookie["samesite"], settings.JWT_COOKIE_SAMESITE)
        self.assertEqual(access["path"], settings.JWT_ACCESS_COOKIE_PATH)
        self.assertEqual(refresh["path"], settings.JWT_REFRESH_COOKIE_PATH)
        self.assertTrue(refresh["max-age"])

    def test_access_cookie_and_token_share_the_configured_lifetime(self):
        response = self.login()
        lifetime = int(jwt_settings.ACCESS_TOKEN_LIFETIME.total_seconds())

        self.assertEqual(int(response.cookies[ACCESS]["max-age"]), lifetime)
        token = AccessToken(response.cookies[ACCESS].value)
        self.assertEqual(token["exp"] - token["iat"], lifetime)

    def test_remember_me_false_makes_refresh_cookie_session_only(self):
        response = self.login(remember_me=False)
        self.assertEqual(response.cookies[REFRESH]["max-age"], "")
        self.assertEqual(response.cookies[REFRESH]["expires"], "")

    def test_cookie_session_authenticates_private_endpoints(self):
        self.login()
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["email"], self.user.email)
        self.assertIn("is_verified", response.data["data"])

    def test_invalid_credentials_rejected_with_generic_message(self):
        for payload in (
            {"email": self.user.email, "password": "WrongPass123!"},
            {"email": "nobody@example.com", "password": PASSWORD},
        ):
            with self.subTest(payload=payload):
                response = self.client.post(self.url, payload, format="json")
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
                self.assertEqual(response.data["message"], "Invalid email or password.")
                self.assertNotIn(ACCESS, response.cookies)

    def test_inactive_user_cannot_log_in(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            self.url, {"email": self.user.email, "password": PASSWORD}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_works_with_a_stale_access_cookie(self):
        self.client.cookies[ACCESS] = "garbage"
        self.login()


class LogoutTests(SessionTestCase):
    def test_logout_clears_cookies_and_blacklists_refresh_token(self):
        self.login()
        old_refresh = self.client.cookies[REFRESH].value

        response = self.client.post(reverse("auth-logout"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assert_cookie_cleared(response, ACCESS)
        self.assert_cookie_cleared(response, REFRESH)
        self.assertEqual(self.client.get(reverse("profile")).status_code, 401)

        # Replaying the captured refresh token must not resurrect the session.
        self.client.cookies[REFRESH] = old_refresh
        response = self.client.post(reverse("auth-refresh"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_token_copied_before_logout_lasts_only_until_expiry(self):
        # Known limitation (docs/AUTHENTICATION.md section 5): logout does not
        # revoke an already-issued access token; it stays usable by whoever
        # copied it until it expires (JWT_ACCESS_TOKEN_LIFETIME_MINUTES).
        self.login()
        copied_access = self.client.cookies[ACCESS].value
        self.client.post(reverse("auth-logout"))

        other_client = APIClient()
        other_client.cookies[ACCESS] = copied_access
        self.assertEqual(other_client.get(reverse("profile")).status_code, 200)

    def test_logout_works_after_access_token_expired(self):
        self.login()
        self.client.cookies[ACCESS] = "expired-or-invalid"
        response = self.client.post(reverse("auth-logout"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class RefreshTests(SessionTestCase):
    url = reverse("auth-refresh")

    def test_refresh_rotates_and_rejects_replay(self):
        self.login()
        old_refresh = self.client.cookies[REFRESH].value

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("data", response.data)
        new_refresh = response.cookies[REFRESH].value
        self.assertNotEqual(new_refresh, old_refresh)
        self.assertTrue(response.cookies[ACCESS].value)

        self.client.cookies[REFRESH] = old_refresh
        replay = self.client.post(self.url)
        self.assertEqual(replay.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assert_cookie_cleared(replay, REFRESH)

    def test_refresh_keeps_session_only_cookie_when_remember_me_false(self):
        self.login(remember_me=False)
        response = self.client.post(self.url)
        self.assertEqual(response.cookies[REFRESH]["max-age"], "")

    def test_missing_refresh_cookie_rejected(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_expired_refresh_token_rejected(self):
        token = RefreshToken.for_user(self.user)
        token.set_exp(lifetime=-timedelta(seconds=1))
        self.client.cookies[REFRESH] = str(token)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_rejected_for_deactivated_user(self):
        self.login()
        self.user.is_active = False
        self.user.save()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_rejected_for_deleted_user(self):
        self.login()
        self.user.delete()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ExpiredAccessTokenTests(SessionTestCase):
    def test_expired_access_cookie_rejected(self):
        token = AccessToken.for_user(self.user)
        token.set_exp(lifetime=-timedelta(seconds=1))
        self.client.cookies[ACCESS] = str(token)
        self.assertEqual(self.client.get(reverse("profile")).status_code, 401)

    def test_tampered_access_cookie_rejected(self):
        token = str(AccessToken.for_user(self.user))
        self.client.cookies[ACCESS] = token[:-2] + ("AA" if token[-2:] != "AA" else "BB")
        self.assertEqual(self.client.get(reverse("profile")).status_code, 401)

    def test_access_token_for_deactivated_user_rejected(self):
        self.client.cookies[ACCESS] = str(AccessToken.for_user(self.user))
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.client.get(reverse("profile")).status_code, 401)

    def test_invalid_bearer_header_is_rejected_not_masked_by_cookie(self):
        expired = AccessToken.for_user(self.user)
        expired.set_exp(lifetime=-timedelta(seconds=1))
        self.client.cookies[ACCESS] = str(AccessToken.for_user(self.user))
        for header in (f"Bearer {expired}", "Bearer not-a-jwt", "Bearer"):
            with self.subTest(header=header):
                response = self.client.get(reverse("profile"), HTTP_AUTHORIZATION=header)
                self.assertEqual(response.status_code, 401)

    def test_non_bearer_authorization_header_falls_back_to_cookie(self):
        self.client.cookies[ACCESS] = str(AccessToken.for_user(self.user))
        response = self.client.get(
            reverse("profile"), HTTP_AUTHORIZATION="Basic c3RhZ2luZzpzZWNyZXQ="
        )
        self.assertEqual(response.status_code, 200)


class CsrfTests(SessionTestCase):
    """Uses a client that enforces CSRF like a real browser request would."""

    def setUp(self):
        super().setUp()
        self.csrf_client = APIClient(enforce_csrf_checks=True)

    def _csrf_token(self):
        response = self.csrf_client.get(reverse("auth-csrf"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("csrftoken", response.cookies)
        return response.data["data"]["csrf_token"]

    def _login(self):
        token = self._csrf_token()
        response = self.csrf_client.post(
            reverse("auth-login"),
            {"email": self.user.email, "password": PASSWORD},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return token

    def test_login_requires_csrf_token(self):
        response = self.csrf_client.post(
            reverse("auth-login"),
            {"email": self.user.email, "password": PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertNotIn(ACCESS, response.cookies)

    def test_cookie_authenticated_unsafe_request_requires_csrf_token(self):
        token = self._login()
        url = reverse("farm-list-create")
        farm = {
            "farm_name": "North Field",
            "address": "Lahore",
            "latitude": "31.5204",
            "longitude": "74.3587",
        }

        rejected = self.csrf_client.post(url, farm, format="json")
        self.assertEqual(rejected.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(rejected.data["detail"], "CSRF verification failed.")

        accepted = self.csrf_client.post(url, farm, format="json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(accepted.status_code, status.HTTP_201_CREATED)

    def test_safe_requests_do_not_need_csrf_token(self):
        self._login()
        self.assertEqual(self.csrf_client.get(reverse("profile")).status_code, 200)

    def test_refresh_and_logout_require_csrf_token(self):
        token = self._login()
        for name in ("auth-refresh", "auth-logout"):
            with self.subTest(endpoint=name):
                response = self.csrf_client.post(reverse(name))
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.csrf_client.post(reverse("auth-refresh"), HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_untrusted_origin_rejected_even_with_token(self):
        token = self._login()
        response = self.csrf_client.post(
            reverse("auth-logout"),
            HTTP_X_CSRFTOKEN=token,
            HTTP_ORIGIN="https://evil.example",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_trusted_frontend_origin_accepted(self):
        token = self._login()
        response = self.csrf_client.post(
            reverse("auth-logout"),
            HTTP_X_CSRFTOKEN=token,
            HTTP_ORIGIN=settings.CORS_ALLOWED_ORIGINS[0],
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_bearer_header_requests_are_not_subject_to_csrf(self):
        access = str(AccessToken.for_user(self.user))
        response = self.csrf_client.post(
            reverse("auth-resend-verification"), HTTP_AUTHORIZATION=f"Bearer {access}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class PasswordResetTests(SessionTestCase):
    def _reset(self, token, password=NEW_PASSWORD):
        return self.client.post(
            reverse("auth-reset-password"),
            {"token": token, "new_password": password, "confirm_password": password},
            format="json",
        )

    def test_forgot_password_response_identical_for_unknown_email(self):
        known = self.client.post(
            reverse("auth-forgot-password"), {"email": self.user.email}, format="json"
        )
        unknown = self.client.post(
            reverse("auth-forgot-password"), {"email": "nobody@example.com"}, format="json"
        )
        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known.data, unknown.data)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])

    def test_email_delivery_failure_is_logged_without_leaking_token(self):
        with patch(
            "authentication.views.send_mail", side_effect=ConnectionRefusedError("smtp down")
        ), self.assertLogs("greenguard", level="ERROR") as logs:
            response = self.client.post(
                reverse("auth-forgot-password"), {"email": self.user.email}, format="json"
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        output = "\n".join(logs.output)
        self.assertIn("Failed to send reset email", output)
        self.assertNotIn("token=", output)
        self.assertNotIn("smtp down", output)

    def test_emailed_reset_link_works(self):
        self.client.post(reverse("auth-forgot-password"), {"email": self.user.email}, format="json")
        token = re.search(r"reset-password\?token=(\S+)", mail.outbox[0].body).group(1)
        self.assertEqual(self._reset(token).status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))

    def test_reset_token_is_single_use(self):
        token = generate_reset_token(self.user)
        self.assertEqual(self._reset(token).status_code, status.HTTP_200_OK)
        reuse = self._reset(token, password="AnotherPass789!")
        self.assertEqual(reuse.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))

    def test_reset_token_expires_after_one_hour(self):
        token = generate_reset_token(self.user)
        with patch("django.core.signing.time.time", return_value=time.time() + 3601):
            response = self._reset(token)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_tampered_reset_token_rejected(self):
        self.assertEqual(self._reset("not-a-real-token").status_code, 400)

    def test_reset_signs_out_existing_sessions(self):
        self.login()
        self.assertEqual(self._reset(generate_reset_token(self.user)).status_code, 200)
        response = self.client.post(reverse("auth-refresh"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ChangePasswordSessionTests(SessionTestCase):
    def test_change_password_signs_out_other_devices_but_keeps_this_one(self):
        other_device = APIClient()
        self.login(client=other_device)
        self.login()

        response = self.client.post(
            reverse("auth-change-password"),
            {
                "current_password": PASSWORD,
                "new_password": NEW_PASSWORD,
                "confirm_password": NEW_PASSWORD,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(other_device.post(reverse("auth-refresh")).status_code, 401)
        self.assertEqual(self.client.post(reverse("auth-refresh")).status_code, 200)


class AccessTokenRevocationTests(SessionTestCase):
    """Access tokens are bound to the password (SIMPLE_JWT CHECK_REVOKE_TOKEN),
    so a password change or reset revokes them immediately rather than when
    they expire."""

    profile = reverse("profile")

    def _change_password(self, client):
        return client.post(
            reverse("auth-change-password"),
            {
                "current_password": PASSWORD,
                "new_password": NEW_PASSWORD,
                "confirm_password": NEW_PASSWORD,
            },
            format="json",
        )

    def test_change_password_revokes_other_devices_access_cookie_immediately(self):
        other_device = APIClient()
        self.login(client=other_device)
        self.login()
        self.assertEqual(other_device.get(self.profile).status_code, 200)

        self.assertEqual(self._change_password(self.client).status_code, 200)

        self.assertEqual(other_device.get(self.profile).status_code, 401)
        # The browser that changed the password got fresh cookies.
        self.assertEqual(self.client.get(self.profile).status_code, 200)

    def test_change_password_revokes_previous_access_cookie_of_same_browser(self):
        self.login()
        stale_access = self.client.cookies[ACCESS].value
        self.assertEqual(self._change_password(self.client).status_code, 200)

        replay = APIClient()
        replay.cookies[ACCESS] = stale_access
        self.assertEqual(replay.get(self.profile).status_code, 401)

    def test_reset_password_revokes_issued_access_cookie_immediately(self):
        self.login()
        self.assertEqual(self.client.get(self.profile).status_code, 200)

        response = self.client.post(
            reverse("auth-reset-password"),
            {
                "token": generate_reset_token(self.user),
                "new_password": NEW_PASSWORD,
                "confirm_password": NEW_PASSWORD,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(self.profile).status_code, 401)

    def test_password_change_revokes_bearer_access_token(self):
        access = str(RefreshToken.for_user(self.user).access_token)
        header = {"HTTP_AUTHORIZATION": f"Bearer {access}"}
        self.assertEqual(self.client.get(self.profile, **header).status_code, 200)

        self.user.set_password(NEW_PASSWORD)
        self.user.save()

        self.assertEqual(self.client.get(self.profile, **header).status_code, 401)

    def test_out_of_band_password_change_rejects_refresh_and_clears_cookies(self):
        # e.g. an admin or `manage.py changepassword`: no refresh tokens are
        # blacklisted, so the password binding alone must end the session.
        self.login()
        self.user.set_password(NEW_PASSWORD)
        self.user.save()

        self.assertEqual(self.client.get(self.profile).status_code, 401)
        response = self.client.post(reverse("auth-refresh"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assert_cookie_cleared(response, ACCESS)
        self.assert_cookie_cleared(response, REFRESH)

    def test_access_token_without_password_binding_rejected(self):
        # Tokens issued before CHECK_REVOKE_TOKEN was enabled lack the claim.
        access = AccessToken.for_user(self.user)
        del access[jwt_settings.REVOKE_TOKEN_CLAIM]
        response = self.client.get(self.profile, HTTP_AUTHORIZATION=f"Bearer {access}")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refreshed_access_token_still_works(self):
        self.login()
        self.assertEqual(self.client.post(reverse("auth-refresh")).status_code, 200)
        self.assertEqual(self.client.get(self.profile).status_code, 200)


class EmailVerificationTests(SessionTestCase):
    url = reverse("auth-verify-email")

    def _verify(self, token):
        return self.client.post(self.url, {"token": token}, format="json")

    def test_first_use_verifies_email(self):
        response = self._verify(generate_email_verification_token(self.user))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Email verified successfully.")
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_verified)

    def test_second_use_of_same_link_rejected(self):
        token = generate_email_verification_token(self.user)
        self.assertEqual(self._verify(token).status_code, status.HTTP_200_OK)

        reuse = self._verify(token)

        self.assertEqual(reuse.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            reuse.data,
            {"success": False, "message": "Verification link is invalid or has expired."},
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_verified)

    def test_other_outstanding_links_rejected_once_verified(self):
        first = generate_email_verification_token(self.user)
        resent = generate_email_verification_token(self.user)
        self.assertEqual(self._verify(resent).status_code, status.HTTP_200_OK)
        self.assertEqual(self._verify(first).status_code, status.HTTP_400_BAD_REQUEST)

    def test_link_for_already_verified_account_rejected(self):
        verified = make_user(email="verified@example.com", is_verified=True)
        response = self._verify(generate_email_verification_token(verified))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_expired_link_rejected_and_not_consumed(self):
        token = generate_email_verification_token(self.user)
        max_age = settings.EMAIL_VERIFICATION_MAX_AGE_HOURS * 3600
        with patch("django.core.signing.time.time", return_value=time.time() + max_age + 1):
            expired = self._verify(token)
        self.assertEqual(expired.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_verified)
        # Still unused, so it works once inside its lifetime.
        self.assertEqual(self._verify(token).status_code, status.HTTP_200_OK)

    def test_tampered_links_rejected(self):
        token = generate_email_verification_token(self.user)
        for tampered in (token + "x", token[:-1], "not-a-real-token"):
            with self.subTest(token=tampered):
                self.assertEqual(self._verify(tampered).status_code, 400)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_verified)

    def test_link_only_verifies_the_account_it_was_issued_for(self):
        other = make_user(email="other@example.com")
        # Signed in as `other`, opening self.user's link: the link decides
        # the account, never the session.
        self.client.force_authenticate(other)
        response = self._verify(generate_email_verification_token(self.user))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        other.refresh_from_db()
        self.user.refresh_from_db()
        self.assertFalse(other.is_verified)
        self.assertTrue(self.user.is_verified)

    def test_link_with_mismatched_account_and_email_rejected(self):
        other = make_user(email="other@example.com")
        forged = signing.dumps(
            {"user_id": str(other.id), "email": self.user.email},
            salt=VERIFY_EMAIL_TOKEN_SALT,
        )
        self.assertEqual(self._verify(forged).status_code, status.HTTP_400_BAD_REQUEST)
        other.refresh_from_db()
        self.user.refresh_from_db()
        self.assertFalse(other.is_verified)
        self.assertFalse(self.user.is_verified)

    def test_emailed_link_works_once(self):
        self.client.post(
            reverse("auth-register"),
            {
                "full_name": "Ali Khan",
                "email": "ali@example.com",
                "password": PASSWORD,
                "confirm_password": PASSWORD,
            },
            format="json",
        )
        token = re.search(r"verify-email\?token=(\S+)", mail.outbox[-1].body).group(1)
        self.assertEqual(self._verify(token).status_code, status.HTTP_200_OK)
        self.assertTrue(User.objects.get(email="ali@example.com").is_verified)
        self.assertEqual(self._verify(token).status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_invalid_after_email_change(self):
        token = generate_email_verification_token(self.user)
        self.user.email = "changed@example.com"
        self.user.save()
        response = self.client.post(self.url, {"token": token}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resend_requires_authentication_and_sends_to_own_address(self):
        url = reverse("auth-resend-verification")
        self.assertEqual(self.client.post(url).status_code, 401)

        self.login()
        response = self.client.post(url, {"email": "attacker@example.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(mail.outbox[-1].to, [self.user.email])
