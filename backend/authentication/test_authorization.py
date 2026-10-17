"""Cross-app authorization matrix: unauthenticated access, farm/report
ownership (IDOR) and role checks, exercised through the real cookie session
(docs/AUTHENTICATION.md). Per-app suites cover each endpoint in more depth;
this file guards the security boundary as a whole."""

import uuid
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from farms.models import Farm
from history.tests import MOCK_WEATHER_REPORT, make_image_file
from module2.tests import VALID_SYMPTOMS
from notifications.models import Notification
from predictions.models import Prediction
from users.models import User

PASSWORD = "StrongPass123!"


def make_user(email, role=User.Role.FARMER):
    return User.objects.create_user(
        email=email, password=PASSWORD, first_name="Test", last_name="User", role=role
    )


def make_farm(user, name="Farm"):
    return Farm.objects.create(
        user=user, farm_name=name, address="Lahore", latitude="31.5204", longitude="74.3587"
    )


def make_prediction(user, farm):
    return Prediction.objects.create(
        user=user,
        farm=farm,
        uploaded_image=make_image_file(),
        prediction_report={"module1": None, "module2": None, "module3": None},
    )


def login(client, user):
    response = client.post(
        reverse("auth-login"), {"email": user.email, "password": PASSWORD}, format="json"
    )
    assert response.status_code == 200, response.data


class UnauthenticatedAccessTests(APITestCase):
    def test_private_endpoints_reject_anonymous_requests(self):
        some_id = uuid.uuid4()
        requests = [
            ("get", reverse("profile")),
            ("put", reverse("profile")),
            ("delete", reverse("profile")),
            ("post", reverse("auth-change-password")),
            ("post", reverse("auth-resend-verification")),
            ("get", reverse("farm-list-create")),
            ("post", reverse("farm-list-create")),
            ("post", reverse("farm-geocode")),
            ("get", reverse("farm-detail", args=[some_id])),
            ("put", reverse("farm-detail", args=[some_id])),
            ("delete", reverse("farm-detail", args=[some_id])),
            ("post", reverse("predictions-analyze")),
            ("get", reverse("predictions-list")),
            ("get", reverse("predictions-detail", args=[some_id])),
            ("delete", reverse("predictions-detail", args=[some_id])),
            ("get", reverse("history-list")),
            ("get", reverse("history-detail", args=[some_id])),
            ("delete", reverse("history-detail", args=[some_id])),
            ("post", reverse("module1-analyze")),
            ("post", reverse("module2-analyze")),
            ("get", reverse("weather-current")),
            ("get", reverse("dashboard-overview")),
            ("get", reverse("dashboard-weather")),
            ("get", reverse("dashboard-recent-predictions")),
            ("get", reverse("dashboard-recommendations")),
            ("get", reverse("notification-list")),
            ("put", reverse("notification-mark-read", args=[some_id])),
            ("delete", reverse("notification-detail", args=[some_id])),
            ("get", reverse("admin-dashboard")),
            ("get", reverse("admin-user-list")),
            ("get", reverse("admin-prediction-list")),
        ]
        for method, url in requests:
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url)
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_public_endpoints_stay_public(self):
        self.assertIn(self.client.get(reverse("health-check")).status_code, (200, 503))
        self.assertEqual(self.client.get(reverse("auth-csrf")).status_code, 200)
        response = self.client.post(
            reverse("auth-forgot-password"), {"email": "x@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, 200)


class FarmIsolationTests(APITestCase):
    """User A (self.client, cookie session) against User B's records."""

    def setUp(self):
        self.user_a = make_user("a@example.com")
        self.user_b = make_user("b@example.com")
        self.farm_a = make_farm(self.user_a, "A's farm")
        self.farm_b = make_farm(self.user_b, "B's farm")
        self.prediction_a = make_prediction(self.user_a, self.farm_a)
        self.prediction_b = make_prediction(self.user_b, self.farm_b)
        self.notification_b = Notification.objects.create(
            user=self.user_b, title="B", message="private"
        )
        login(self.client, self.user_a)

    def test_owner_can_access_own_farm_and_reports(self):
        for url in (
            reverse("farm-detail", args=[self.farm_a.id]),
            reverse("predictions-detail", args=[self.prediction_a.id]),
            reverse("history-detail", args=[self.prediction_a.id]),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)

    def test_cannot_read_modify_or_delete_another_users_farm(self):
        url = reverse("farm-detail", args=[self.farm_b.id])
        update = {"farm_name": "Hijacked", "address": "x", "latitude": "1", "longitude": "1"}

        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.put(url, update, format="json").status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 404)

        self.farm_b.refresh_from_db()
        self.assertEqual(self.farm_b.farm_name, "B's farm")

    def test_cannot_read_or_delete_another_users_reports(self):
        for name in ("predictions-detail", "history-detail"):
            url = reverse(name, args=[self.prediction_b.id])
            with self.subTest(endpoint=name):
                self.assertEqual(self.client.get(url).status_code, 404)
                self.assertEqual(self.client.delete(url).status_code, 404)
        self.assertTrue(Prediction.objects.filter(id=self.prediction_b.id).exists())

    def test_cannot_touch_another_users_notifications(self):
        read_url = reverse("notification-mark-read", args=[self.notification_b.id])
        delete_url = reverse("notification-detail", args=[self.notification_b.id])
        self.assertEqual(self.client.put(read_url).status_code, 404)
        self.assertEqual(self.client.delete(delete_url).status_code, 404)
        self.notification_b.refresh_from_db()
        self.assertFalse(self.notification_b.is_read)

    def test_list_endpoints_only_return_own_records(self):
        farms = self.client.get(reverse("farm-list-create")).data["data"]
        self.assertEqual({f["farm_id"] for f in farms}, {str(self.farm_a.id)})

        for name in ("predictions-list", "history-list", "dashboard-recent-predictions"):
            with self.subTest(endpoint=name):
                body = str(self.client.get(reverse(name)).data)
                self.assertIn(str(self.prediction_a.id), body)
                self.assertNotIn(str(self.prediction_b.id), body)

        notifications = str(self.client.get(reverse("notification-list")).data)
        self.assertNotIn(str(self.notification_b.id), notifications)

    def test_farm_ownership_comes_from_session_not_request_body(self):
        response = self.client.post(
            reverse("farm-list-create"),
            {
                "farm_name": "New",
                "address": "Lahore",
                "latitude": "31.5",
                "longitude": "74.3",
                "user": str(self.user_b.id),
                "user_id": str(self.user_b.id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Farm.objects.get(id=response.data["data"]["farm_id"]).user, self.user_a)

    def test_weather_for_another_users_farm_rejected(self):
        with patch("weather.views.fetch_weather_for_coordinates") as weather, patch(
            "dashboard.views.fetch_weather_for_coordinates"
        ) as dashboard_weather:
            for name in ("weather-current", "dashboard-weather"):
                with self.subTest(endpoint=name):
                    response = self.client.get(reverse(name), {"farm_id": str(self.farm_b.id)})
                    self.assertEqual(response.status_code, 404)
        weather.assert_not_called()
        dashboard_weather.assert_not_called()

    def test_quick_scan_on_another_users_farm_rejected_before_ai_calls(self):
        with patch("predictions.views.call_disease_module_predict") as module1, patch(
            "predictions.views.fetch_weather_for_coordinates"
        ) as weather:
            response = self.client.post(
                reverse("predictions-analyze"),
                {"image": make_image_file(), "farm_id": str(self.farm_b.id)},
                format="multipart",
            )
        self.assertEqual(response.status_code, 404)
        module1.assert_not_called()
        weather.assert_not_called()
        self.assertEqual(Prediction.objects.filter(farm=self.farm_b).count(), 1)

    def test_disease_check_on_another_users_farm_rejected_before_ai_call(self):
        with patch("module1.views.call_disease_module_predict") as module1:
            response = self.client.post(
                reverse("module1-analyze"),
                {"image": make_image_file(), "farm_id": str(self.farm_b.id)},
                format="multipart",
            )
        self.assertEqual(response.status_code, 404)
        module1.assert_not_called()

    def test_soil_check_on_another_users_farm_rejected_before_ai_call(self):
        payload = {
            "farm_id": str(self.farm_b.id),
            "crop": "wheat",
            "growth_stage": "vegetative",
            "soil_type": "sandy",
            "last_fertilizer_type": "No_Fertilizer",
            "days_since_fertilizer": "not_applicable",
            "irrigation_source": "tube_well",
            "irrigation_adequacy": "excessive",
            "ph_value": 6.5,
            "soil_moisture_pct": 55,
            "light_intensity_lux": 25000,
            "symptoms": VALID_SYMPTOMS,
        }
        with patch("module2.views.call_module2_orchestrator") as module2, patch(
            "module2.views.fetch_weather_for_coordinates", return_value=MOCK_WEATHER_REPORT
        ):
            response = self.client.post(reverse("module2-analyze"), payload, format="json")
        self.assertEqual(response.status_code, 404)
        module2.assert_not_called()

    def test_malformed_ids_do_not_error(self):
        for value in ("not-a-uuid", "1 OR 1=1", "' OR ''='"):
            with self.subTest(value=value):
                response = self.client.get(reverse("farm-detail", args=[value]))
                self.assertEqual(response.status_code, 404)


class RoleTests(APITestCase):
    def setUp(self):
        self.farmer = make_user("farmer@example.com")
        self.admin = make_user("admin@example.com", role=User.Role.ADMIN)

    def test_farmers_cannot_reach_admin_endpoints(self):
        login(self.client, self.farmer)
        for name in ("admin-dashboard", "admin-user-list", "admin-prediction-list"):
            with self.subTest(endpoint=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)
        url = reverse("admin-user-detail", args=[self.admin.id])
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_admins_can_reach_admin_endpoints(self):
        login(self.client, self.admin)
        self.assertEqual(self.client.get(reverse("admin-user-list")).status_code, 200)

    def test_farmers_cannot_log_into_django_admin(self):
        client = APIClient()
        client.force_login(self.farmer)
        response = client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])
