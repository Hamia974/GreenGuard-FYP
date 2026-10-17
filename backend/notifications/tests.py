import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Notification

User = get_user_model()


class NotificationModelTests(TestCase):
    """Model-level behavior per DATABASE_SPECIFICATION.md section 6."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="farmer@example.com",
            password="StrongPass123!",
            first_name="Hamia",
            last_name="Khalil",
        )

    def test_is_read_defaults_to_false(self):
        notification = Notification.objects.create(
            user=self.user, title="Title", message="Message"
        )
        self.assertFalse(notification.is_read)

    def test_notification_type_defaults_to_system(self):
        notification = Notification.objects.create(
            user=self.user, title="Title", message="Message"
        )
        self.assertEqual(notification.notification_type, Notification.NotificationType.SYSTEM)

    def test_accepts_system_notification_type(self):
        notification = Notification.objects.create(
            user=self.user, title="System", message="Message", notification_type="system"
        )
        notification.full_clean()
        self.assertEqual(notification.notification_type, "system")

    def test_accepts_prediction_notification_type(self):
        notification = Notification.objects.create(
            user=self.user, title="Prediction", message="Message", notification_type="prediction"
        )
        notification.full_clean()
        self.assertEqual(notification.notification_type, "prediction")

    def test_accepts_weather_notification_type(self):
        notification = Notification.objects.create(
            user=self.user, title="Weather", message="Message", notification_type="weather"
        )
        notification.full_clean()
        self.assertEqual(notification.notification_type, "weather")

    def test_rejects_invalid_notification_type(self):
        notification = Notification(
            user=self.user,
            title="Invalid",
            message="Message",
            notification_type="disease_risk",
        )
        with self.assertRaises(DjangoValidationError):
            notification.full_clean()

    def test_deleting_user_cascades_to_notifications(self):
        Notification.objects.create(user=self.user, title="Title", message="Message")
        self.user.delete()
        self.assertEqual(Notification.objects.count(), 0)

    def test_unread_count_reflects_only_unread_notifications(self):
        Notification.objects.create(user=self.user, title="Unread 1", message="m")
        Notification.objects.create(user=self.user, title="Unread 2", message="m")
        Notification.objects.create(
            user=self.user, title="Read", message="m", is_read=True
        )

        unread_count = Notification.objects.filter(user=self.user, is_read=False).count()

        self.assertEqual(unread_count, 2)


class NotificationListViewTests(APITestCase):
    """GET /api/v1/notifications/ per REST_API_SPEC.md section 7."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="farmer@example.com",
            password="StrongPass123!",
            first_name="Hamia",
            last_name="Khalil",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="StrongPass123!",
            first_name="Other",
            last_name="Farmer",
        )
        self.url = reverse("notification-list")

    def test_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_response_envelope_matches_standard_contract(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.data.keys()), {"success", "message", "data"})
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Notifications retrieved successfully.")

    def test_returns_empty_list_when_no_notifications(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.data["data"], [])

    def test_response_fields_match_section_7_contract(self):
        notification = Notification.objects.create(
            user=self.user, title="Prediction Completed", message="Your analysis is ready."
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        item = response.data["data"][0]
        self.assertEqual(
            set(item.keys()), {"notification_id", "title", "message", "is_read", "created_at"}
        )
        self.assertEqual(item["notification_id"], str(notification.id))
        self.assertEqual(item["title"], "Prediction Completed")
        self.assertEqual(item["message"], "Your analysis is ready.")
        self.assertFalse(item["is_read"])

    def test_returns_only_own_notifications(self):
        own = Notification.objects.create(user=self.user, title="Mine", message="m")
        Notification.objects.create(user=self.other_user, title="Not mine", message="m")
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        ids = [item["notification_id"] for item in response.data["data"]]
        self.assertEqual(ids, [str(own.id)])

    def test_returns_newest_first(self):
        first = Notification.objects.create(user=self.user, title="First", message="m")
        second = Notification.objects.create(user=self.user, title="Second", message="m")
        third = Notification.objects.create(user=self.user, title="Third", message="m")
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        ids = [item["notification_id"] for item in response.data["data"]]
        self.assertEqual(ids, [str(third.id), str(second.id), str(first.id)])


class NotificationMarkReadViewTests(APITestCase):
    """PUT /api/v1/notifications/{id}/read/ per REST_API_SPEC.md section 7."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="farmer@example.com",
            password="StrongPass123!",
            first_name="Hamia",
            last_name="Khalil",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="StrongPass123!",
            first_name="Other",
            last_name="Farmer",
        )
        self.notification = Notification.objects.create(
            user=self.user, title="Title", message="Message"
        )
        self.url = reverse("notification-mark-read", args=[self.notification.id])

    def test_requires_authentication(self):
        response = self.client.put(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_owner_can_mark_own_notification_as_read(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.put(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Notification marked as read.")

    def test_mark_read_changes_is_read_to_true_in_database(self):
        self.client.force_authenticate(user=self.user)

        self.client.put(self.url)

        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)

    def test_non_owner_cannot_mark_another_users_notification_as_read(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.put(self.url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.notification.refresh_from_db()
        self.assertFalse(self.notification.is_read)

    def test_mark_read_nonexistent_notification_returns_404(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.put(
            reverse("notification-mark-read", args=[uuid.uuid4()])
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class NotificationDeleteViewTests(APITestCase):
    """DELETE /api/v1/notifications/{id}/ per REST_API_SPEC.md section 7."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="farmer@example.com",
            password="StrongPass123!",
            first_name="Hamia",
            last_name="Khalil",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="StrongPass123!",
            first_name="Other",
            last_name="Farmer",
        )
        self.notification = Notification.objects.create(
            user=self.user, title="Title", message="Message"
        )
        self.url = reverse("notification-detail", args=[self.notification.id])

    def test_requires_authentication(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_owner_can_delete_own_notification(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Notification deleted successfully.")

    def test_delete_removes_the_record(self):
        self.client.force_authenticate(user=self.user)

        self.client.delete(self.url)

        self.assertFalse(Notification.objects.filter(id=self.notification.id).exists())

    def test_non_owner_cannot_delete_another_users_notification(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Notification.objects.filter(id=self.notification.id).exists())

    def test_delete_nonexistent_notification_returns_404(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(
            reverse("notification-detail", args=[uuid.uuid4()])
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
