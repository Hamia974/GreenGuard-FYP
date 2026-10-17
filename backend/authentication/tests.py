from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User


class ChangePasswordTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="farmer@example.com",
            password="StrongPass123!",
            first_name="Hamia",
            last_name="Khalil",
        )
        self.url = reverse("auth-change-password")
        self.client.force_authenticate(user=self.user)

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(
            self.url,
            {
                "current_password": "StrongPass123!",
                "new_password": "NewStrongPass456!",
                "confirm_password": "NewStrongPass456!",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_changes_password_with_correct_current_password(self):
        response = self.client.post(
            self.url,
            {
                "current_password": "StrongPass123!",
                "new_password": "NewStrongPass456!",
                "confirm_password": "NewStrongPass456!",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewStrongPass456!"))
        self.assertFalse(self.user.check_password("StrongPass123!"))

    def test_rejects_incorrect_current_password(self):
        response = self.client.post(
            self.url,
            {
                "current_password": "WrongPassword123!",
                "new_password": "NewStrongPass456!",
                "confirm_password": "NewStrongPass456!",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertFalse(response.data["success"])
        self.assertIn("current_password", response.data["errors"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("StrongPass123!"))

    def test_rejects_mismatched_confirmation(self):
        response = self.client.post(
            self.url,
            {
                "current_password": "StrongPass123!",
                "new_password": "NewStrongPass456!",
                "confirm_password": "SomethingElse789!",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertFalse(response.data["success"])
        self.assertIn("confirm_password", response.data["errors"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("StrongPass123!"))

    def test_rejects_weak_new_password(self):
        response = self.client.post(
            self.url,
            {
                "current_password": "StrongPass123!",
                "new_password": "12345678",
                "confirm_password": "12345678",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertFalse(response.data["success"])
        self.assertIn("new_password", response.data["errors"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("StrongPass123!"))

    def test_rejects_missing_fields(self):
        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertFalse(response.data["success"])
        for field in ("current_password", "new_password", "confirm_password"):
            self.assertIn(field, response.data["errors"])

    def test_does_not_affect_other_users_password(self):
        other = User.objects.create_user(
            email="other@example.com",
            password="OthersPass123!",
            first_name="Other",
            last_name="Farmer",
        )
        self.client.post(
            self.url,
            {
                "current_password": "StrongPass123!",
                "new_password": "NewStrongPass456!",
                "confirm_password": "NewStrongPass456!",
            },
        )

        other.refresh_from_db()
        self.assertTrue(other.check_password("OthersPass123!"))
