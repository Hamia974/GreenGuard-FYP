import io

from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User


def make_image_file(name="avatar.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), color="green").save(buffer, format="PNG")
    buffer.seek(0)
    buffer.name = name
    return buffer


class ProfileGetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="farmer@example.com",
            password="StrongPass123!",
            first_name="Hamia",
            last_name="Khalil",
        )
        self.url = reverse("profile")

    def test_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_authenticated_users_profile(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertTrue(response.data["success"])
        self.assertEqual(data["user_id"], str(self.user.id))
        self.assertEqual(data["full_name"], "Hamia Khalil")
        self.assertEqual(data["email"], "farmer@example.com")
        self.assertEqual(data["role"], "Farmer")
        self.assertIsNone(data["profile_image"])
        self.assertIn("created_at", data)

    def test_admin_role_is_capitalized(self):
        admin = User.objects.create_superuser(
            email="admin@example.com", password="StrongPass123!"
        )
        self.client.force_authenticate(user=admin)
        response = self.client.get(self.url)

        self.assertEqual(response.data["data"]["role"], "Admin")


class ProfileUpdateTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="farmer@example.com",
            password="StrongPass123!",
            first_name="Hamia",
            last_name="Khalil",
        )
        self.url = reverse("profile")
        self.client.force_authenticate(user=self.user)

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.put(self.url, {"full_name": "New Name"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_updates_full_name(self):
        response = self.client.put(self.url, {"full_name": "Minahil Kamran"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Minahil")
        self.assertEqual(self.user.last_name, "Kamran")

    def test_single_word_name_leaves_last_name_blank(self):
        response = self.client.put(self.url, {"full_name": "Cher"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Cher")
        self.assertEqual(self.user.last_name, "")

    def test_missing_full_name_is_rejected(self):
        response = self.client.put(self.url, {})

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertFalse(response.data["success"])
        self.assertIn("full_name", response.data["errors"])

    def test_uploads_profile_image(self):
        response = self.client.put(
            self.url,
            {"full_name": "Hamia Khalil", "profile_image": make_image_file()},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(bool(self.user.profile_image))

        get_response = self.client.get(self.url)
        self.assertIsNotNone(get_response.data["data"]["profile_image"])

    def test_rejects_non_image_file_as_profile_image(self):
        bad_file = io.BytesIO(b"not an image")
        bad_file.name = "avatar.txt"

        response = self.client.put(
            self.url,
            {"full_name": "Hamia Khalil", "profile_image": bad_file},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("profile_image", response.data["errors"])
        self.user.refresh_from_db()
        self.assertFalse(bool(self.user.profile_image))

    def test_rejects_oversized_profile_image(self):
        oversized = io.BytesIO(b"0" * (11 * 1024 * 1024))
        oversized.name = "big.png"

        response = self.client.put(
            self.url,
            {"full_name": "Hamia Khalil", "profile_image": oversized},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("profile_image", response.data["errors"])

    def test_does_not_affect_other_users(self):
        other = User.objects.create_user(
            email="other@example.com",
            password="StrongPass123!",
            first_name="Other",
            last_name="Farmer",
        )
        self.client.put(self.url, {"full_name": "Changed Name"})

        other.refresh_from_db()
        self.assertEqual(other.first_name, "Other")
        self.assertEqual(other.last_name, "Farmer")


class AccountDeletionTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="farmer@example.com",
            password="StrongPass123!",
            first_name="Hamia",
            last_name="Khalil",
        )
        self.url = reverse("profile")
        self.client.force_authenticate(user=self.user)

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.delete(
            self.url, {"current_password": "StrongPass123!"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_correct_password_deletes_account(self):
        user_id = self.user.id
        response = self.client.delete(
            self.url, {"current_password": "StrongPass123!"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertFalse(User.objects.filter(id=user_id).exists())

    def test_incorrect_password_is_rejected_and_account_survives(self):
        response = self.client.delete(
            self.url, {"current_password": "WrongPassword123!"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertFalse(response.data["success"])
        self.assertIn("current_password", response.data["errors"])
        self.assertTrue(User.objects.filter(id=self.user.id).exists())

    def test_missing_password_is_rejected_and_account_survives(self):
        response = self.client.delete(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertFalse(response.data["success"])
        self.assertIn("current_password", response.data["errors"])
        self.assertTrue(User.objects.filter(id=self.user.id).exists())

    def test_does_not_delete_other_users_account(self):
        other = User.objects.create_user(
            email="other@example.com",
            password="OthersPass123!",
            first_name="Other",
            last_name="Farmer",
        )
        response = self.client.delete(
            self.url, {"current_password": "StrongPass123!"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(User.objects.filter(id=other.id).exists())
