from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from adminpanel.permissions import IsAdminRole
from adminpanel.services import (
    INTEGRATION_LAYER_STATUS,
    check_ai_services,
    compute_overall_system_status,
    get_ai_module_status,
    get_system_health,
)
from farms.models import Farm
from history.tests import make_report
from predictions.models import Prediction
from predictions.tests import make_image_file

User = get_user_model()


def make_prediction(user, farm, diagnosis="Powdery Mildew", confidence=0.9, status_=None):
    kwargs = dict(
        user=user,
        farm=farm,
        uploaded_image=make_image_file(),
        prediction_report=make_report(diagnosis, confidence, is_healthy=diagnosis == "Healthy"),
    )
    if status_:
        kwargs["prediction_status"] = status_
    return Prediction.objects.create(**kwargs)


class AdminApiAuthorizationTests(APITestCase):
    """Every admin endpoint must require authentication (401) and Admin
    role (403 for an authenticated non-admin), per REST_API_SPEC.md section
    8's "Admin Rules".
    """

    def setUp(self):
        self.farmer = User.objects.create_user(
            email="farmer@example.com", password="StrongPassword123",
            first_name="Farm", last_name="Er",
        )
        self.admin = User.objects.create_user(
            email="admin@example.com", password="StrongPassword123",
            first_name="Admin", last_name="User", role=User.Role.ADMIN,
        )
        self.urls = [
            ("get", reverse("admin-dashboard")),
            ("get", reverse("admin-user-list")),
            ("get", reverse("admin-user-detail", args=[self.farmer.id])),
            ("put", reverse("admin-user-status", args=[self.farmer.id])),
            ("delete", reverse("admin-user-detail", args=[self.farmer.id])),
            ("get", reverse("admin-prediction-list")),
            ("get", reverse("admin-ai-monitoring")),
            ("get", reverse("admin-system-health")),
            ("get", reverse("admin-statistics")),
        ]

    def _call(self, method, url):
        return getattr(self.client, method)(url)

    def test_all_admin_endpoints_require_authentication(self):
        for method, url in self.urls:
            with self.subTest(method=method, url=url):
                response = self._call(method, url)
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_all_admin_endpoints_reject_non_admin_users(self):
        self.client.force_authenticate(user=self.farmer)
        for method, url in self.urls:
            with self.subTest(method=method, url=url):
                response = self._call(method, url)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_access_dashboard(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse("admin-dashboard"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])


class IsAdminRolePermissionTests(TestCase):
    def test_rejects_none_user(self):
        class FakeRequest:
            user = None

        self.assertFalse(IsAdminRole().has_permission(FakeRequest(), None))


class AdminDashboardViewTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com", password="StrongPassword123",
            first_name="Admin", last_name="User", role=User.Role.ADMIN,
        )
        self.client.force_authenticate(user=self.admin)
        self.url = reverse("admin-dashboard")

    def test_empty_database_returns_honest_zero_counts(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        # Exactly one admin user exists at this point (self.admin).
        self.assertEqual(data["total_users"], 1)
        self.assertEqual(data["active_users"], 1)
        self.assertEqual(data["total_predictions"], 0)
        self.assertEqual(data["system_status"], "Healthy")

    def test_counts_reflect_real_data(self):
        farmer = User.objects.create_user(
            email="farmer@example.com", password="StrongPassword123",
            first_name="Farm", last_name="Er",
        )
        User.objects.create_user(
            email="inactive@example.com", password="StrongPassword123",
            first_name="In", last_name="Active", is_active=False,
        )
        farm = Farm.objects.create(
            user=farmer, farm_name="Green Valley", address="Lahore",
            latitude=31.5204, longitude=74.3587,
        )
        make_prediction(farmer, farm)

        response = self.client.get(self.url)
        data = response.data["data"]
        self.assertEqual(data["total_users"], 3)
        self.assertEqual(data["active_users"], 2)
        self.assertEqual(data["total_predictions"], 1)

    def test_response_never_exposes_password_or_secrets(self):
        response = self.client.get(self.url)
        body = str(response.data)
        for forbidden in ("password", "SECRET_KEY", "jwt", "token"):
            self.assertNotIn(forbidden, body.lower().replace("total_predictions", ""))


class AdminUserListViewTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com", password="StrongPassword123",
            first_name="Admin", last_name="User", role=User.Role.ADMIN,
        )
        self.client.force_authenticate(user=self.admin)
        self.url = reverse("admin-user-list")

    def test_lists_all_users(self):
        User.objects.create_user(
            email="alice@example.com", password="StrongPassword123",
            first_name="Alice", last_name="Anderson",
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emails = [row["email"] for row in response.data["data"]]
        self.assertIn("alice@example.com", emails)
        self.assertIn("admin@example.com", emails)

    def test_list_item_shape_matches_documented_fields(self):
        response = self.client.get(self.url)
        row = response.data["data"][0]
        self.assertEqual(
            set(row.keys()), {"user_id", "full_name", "email", "status", "role"}
        )
        self.assertEqual(row["role"], "Admin")
        self.assertEqual(row["status"], "Active")

    def test_search_filters_by_name_or_email(self):
        User.objects.create_user(
            email="bob@example.com", password="StrongPassword123",
            first_name="Bob", last_name="Builder",
        )
        response = self.client.get(self.url, {"search": "bob"})
        emails = [row["email"] for row in response.data["data"]]
        self.assertEqual(emails, ["bob@example.com"])

    def test_status_filter(self):
        User.objects.create_user(
            email="inactive@example.com", password="StrongPassword123",
            first_name="In", last_name="Active", is_active=False,
        )
        response = self.client.get(self.url, {"status": "Inactive"})
        emails = [row["email"] for row in response.data["data"]]
        self.assertEqual(emails, ["inactive@example.com"])

    def test_pagination_limits_results(self):
        for i in range(5):
            User.objects.create_user(
                email=f"user{i}@example.com", password="StrongPassword123",
                first_name=f"User{i}", last_name="Test",
            )
        response = self.client.get(self.url, {"limit": 2, "page": 1})
        self.assertEqual(len(response.data["data"]), 2)

    def test_invalid_query_params_return_422(self):
        response = self.client.get(self.url, {"status": "not-a-status"})
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)


class AdminUserDetailViewTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com", password="StrongPassword123",
            first_name="Admin", last_name="User", role=User.Role.ADMIN,
        )
        self.farmer = User.objects.create_user(
            email="farmer@example.com", password="StrongPassword123",
            first_name="Farm", last_name="Er",
        )
        self.client.force_authenticate(user=self.admin)

    def test_get_returns_profile_and_prediction_count(self):
        farm = Farm.objects.create(
            user=self.farmer, farm_name="Green Valley", address="Lahore",
            latitude=31.5204, longitude=74.3587,
        )
        make_prediction(self.farmer, farm)

        response = self.client.get(reverse("admin-user-detail", args=[self.farmer.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(data["email"], "farmer@example.com")
        self.assertEqual(data["prediction_count"], 1)
        self.assertEqual(data["status"], "Active")
        self.assertNotIn("password", data)

    def test_get_unknown_user_returns_404(self):
        response = self.client.get(reverse("admin-user-detail", args=["00000000-0000-0000-0000-000000000000"]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_malformed_id_returns_404_not_500(self):
        response = self.client.get(reverse("admin-user-detail", args=["not-a-uuid"]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_removes_user(self):
        response = self.client.delete(reverse("admin-user-detail", args=[self.farmer.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(User.objects.filter(id=self.farmer.id).exists())

    def test_delete_cascades_owned_data(self):
        farm = Farm.objects.create(
            user=self.farmer, farm_name="Green Valley", address="Lahore",
            latitude=31.5204, longitude=74.3587,
        )
        prediction = make_prediction(self.farmer, farm)

        self.client.delete(reverse("admin-user-detail", args=[self.farmer.id]))
        self.assertFalse(Farm.objects.filter(id=farm.id).exists())
        self.assertFalse(Prediction.objects.filter(id=prediction.id).exists())

    def test_admin_cannot_delete_own_account(self):
        response = self.client.delete(reverse("admin-user-detail", args=[self.admin.id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(User.objects.filter(id=self.admin.id).exists())

    def test_delete_unknown_user_returns_404(self):
        response = self.client.delete(reverse("admin-user-detail", args=["00000000-0000-0000-0000-000000000000"]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class AdminUserStatusViewTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com", password="StrongPassword123",
            first_name="Admin", last_name="User", role=User.Role.ADMIN,
        )
        self.farmer = User.objects.create_user(
            email="farmer@example.com", password="StrongPassword123",
            first_name="Farm", last_name="Er",
        )
        self.client.force_authenticate(user=self.admin)
        self.url = reverse("admin-user-status", args=[self.farmer.id])

    def test_deactivates_user(self):
        response = self.client.put(self.url, {"status": "Inactive"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.farmer.refresh_from_db()
        self.assertFalse(self.farmer.is_active)

    def test_reactivates_user(self):
        self.farmer.is_active = False
        self.farmer.save(update_fields=["is_active"])
        response = self.client.put(self.url, {"status": "Active"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.farmer.refresh_from_db()
        self.assertTrue(self.farmer.is_active)

    def test_invalid_status_value_returns_422(self):
        response = self.client.put(self.url, {"status": "Banned"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_missing_status_returns_422(self):
        response = self.client.put(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_unknown_user_returns_404(self):
        url = reverse("admin-user-status", args=["00000000-0000-0000-0000-000000000000"])
        response = self.client.put(url, {"status": "Active"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_cannot_deactivate_own_account(self):
        url = reverse("admin-user-status", args=[self.admin.id])
        response = self.client.put(url, {"status": "Inactive"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)


class AdminPredictionListViewTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com", password="StrongPassword123",
            first_name="Admin", last_name="User", role=User.Role.ADMIN,
        )
        self.farmer = User.objects.create_user(
            email="farmer@example.com", password="StrongPassword123",
            first_name="Farm", last_name="Er",
        )
        self.farm = Farm.objects.create(
            user=self.farmer, farm_name="Green Valley", address="Lahore",
            latitude=31.5204, longitude=74.3587,
        )
        self.client.force_authenticate(user=self.admin)
        self.url = reverse("admin-prediction-list")

    def test_returns_empty_list_when_no_predictions(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"], [])

    def test_lists_predictions_across_all_users(self):
        make_prediction(self.farmer, self.farm, diagnosis="Powdery Mildew")
        response = self.client.get(self.url)
        row = response.data["data"][0]
        self.assertEqual(
            set(row.keys()),
            {"prediction_id", "user", "diagnosis", "confidence", "created_at"},
        )
        self.assertEqual(row["user"], "Farm Er")
        self.assertEqual(row["diagnosis"], "Powdery Mildew")

    def test_search_matches_diagnosis(self):
        make_prediction(self.farmer, self.farm, diagnosis="Powdery Mildew")
        make_prediction(self.farmer, self.farm, diagnosis="Healthy")
        response = self.client.get(self.url, {"search": "Mildew"})
        self.assertEqual(len(response.data["data"]), 1)

    def test_search_matches_user_email(self):
        make_prediction(self.farmer, self.farm)
        response = self.client.get(self.url, {"search": "farmer@example.com"})
        self.assertEqual(len(response.data["data"]), 1)

    def test_status_filter(self):
        make_prediction(self.farmer, self.farm, status_=Prediction.Status.FAILED)
        make_prediction(self.farmer, self.farm, status_=Prediction.Status.COMPLETED)
        response = self.client.get(self.url, {"status": "failed"})
        self.assertEqual(len(response.data["data"]), 1)

    def test_pagination(self):
        for _ in range(3):
            make_prediction(self.farmer, self.farm)
        response = self.client.get(self.url, {"limit": 2})
        self.assertEqual(len(response.data["data"]), 2)


class AdminPredictionDetailViewTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com", password="StrongPassword123",
            first_name="Admin", last_name="User", role=User.Role.ADMIN,
        )
        self.farmer = User.objects.create_user(
            email="farmer@example.com", password="StrongPassword123",
            first_name="Farm", last_name="Er",
        )
        self.farm = Farm.objects.create(
            user=self.farmer, farm_name="Green Valley", address="Lahore",
            latitude=31.5204, longitude=74.3587,
        )
        self.client.force_authenticate(user=self.admin)

    def test_deletes_any_users_prediction(self):
        prediction = make_prediction(self.farmer, self.farm)
        response = self.client.delete(reverse("admin-prediction-detail", args=[prediction.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Prediction.objects.filter(id=prediction.id).exists())

    def test_unknown_prediction_returns_404(self):
        response = self.client.delete(
            reverse("admin-prediction-detail", args=["00000000-0000-0000-0000-000000000000"])
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_malformed_id_returns_404_not_500(self):
        response = self.client.delete(reverse("admin-prediction-detail", args=["not-a-uuid"]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(ENABLE_MOCK_AI=True)
class AdminAIMonitoringViewTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com", password="StrongPassword123",
            first_name="Admin", last_name="User", role=User.Role.ADMIN,
        )
        self.client.force_authenticate(user=self.admin)

    @override_settings(ENABLE_MOCK_AI=True)
    def test_reports_mock_mode_honestly_when_enabled(self):
        response = self.client.get(reverse("admin-ai-monitoring"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(data["image_module"], "Mock Mode")
        self.assertEqual(data["soil_module"], "Mock Mode")
        self.assertEqual(data["fusion_module"], INTEGRATION_LAYER_STATUS)
        self.assertEqual(set(data.keys()), {
            "image_module", "soil_module", "weather_module", "fusion_module",
        })

    @override_settings(ENABLE_MOCK_AI=False)
    @patch("adminpanel.services.check_weather_module_health", return_value=True)
    @patch("adminpanel.services.check_stress_module_health", return_value=True)
    @patch("adminpanel.services.check_disease_module_health", return_value=False)
    def test_reports_unreachable_when_module1_health_check_fails(self, *_mocks):
        response = self.client.get(reverse("admin-ai-monitoring"))
        data = response.data["data"]
        self.assertEqual(data["image_module"], "Unreachable")
        self.assertEqual(data["soil_module"], "Connected")
        self.assertEqual(data["weather_module"], "Connected")

    @override_settings(ENABLE_MOCK_AI=False)
    @patch("adminpanel.services.check_weather_module_health", return_value=False)
    @patch("adminpanel.services.check_stress_module_health", return_value=False)
    @patch("adminpanel.services.check_disease_module_health", return_value=True)
    def test_reports_module1_connected_and_fusion_as_integration_layer(self, *_mocks):
        response = self.client.get(reverse("admin-ai-monitoring"))
        data = response.data["data"]
        self.assertEqual(data["image_module"], "Connected")
        self.assertEqual(data["fusion_module"], INTEGRATION_LAYER_STATUS)

    def test_never_fabricates_confidence_or_accuracy_metrics(self):
        response = self.client.get(reverse("admin-ai-monitoring"))
        body = str(response.data)
        for forbidden in ("confidence", "accuracy", "uptime", "latency"):
            self.assertNotIn(forbidden, body.lower())


@override_settings(ENABLE_MOCK_AI=True)
class AdminSystemHealthViewTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com", password="StrongPassword123",
            first_name="Admin", last_name="User", role=User.Role.ADMIN,
        )
        self.client.force_authenticate(user=self.admin)

    def test_shape_matches_documented_fields(self):
        response = self.client.get(reverse("admin-system-health"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(response.data["data"].keys()),
            {"backend", "database", "ai_services", "weather_api"},
        )

    def test_database_reports_healthy_against_real_test_db(self):
        response = self.client.get(reverse("admin-system-health"))
        self.assertEqual(response.data["data"]["database"], "Healthy")
        self.assertEqual(response.data["data"]["backend"], "Healthy")

    def test_never_exposes_connection_strings_or_secrets(self):
        response = self.client.get(reverse("admin-system-health"))
        body = str(response.data)
        for forbidden in ("postgres://", "password", "secret_key", "django-insecure"):
            self.assertNotIn(forbidden, body.lower())


class AdminStatisticsViewTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com", password="StrongPassword123",
            first_name="Admin", last_name="User", role=User.Role.ADMIN,
        )
        self.farmer = User.objects.create_user(
            email="farmer@example.com", password="StrongPassword123",
            first_name="Farm", last_name="Er",
        )
        self.client.force_authenticate(user=self.admin)
        self.url = reverse("admin-statistics")

    def test_empty_database_returns_null_most_detected_disease(self):
        response = self.client.get(self.url)
        data = response.data["data"]
        self.assertIsNone(data["most_detected_disease"])
        self.assertIsNone(data["most_recommended_crop"])

    def test_most_detected_disease_is_computed_from_real_data(self):
        farm = Farm.objects.create(
            user=self.farmer, farm_name="Green Valley", address="Lahore",
            latitude=31.5204, longitude=74.3587,
        )
        make_prediction(self.farmer, farm, diagnosis="Powdery Mildew")
        make_prediction(self.farmer, farm, diagnosis="Powdery Mildew")
        make_prediction(self.farmer, farm, diagnosis="Healthy")

        response = self.client.get(self.url)
        data = response.data["data"]
        self.assertEqual(data["most_detected_disease"], "Powdery Mildew")
        self.assertEqual(data["total_predictions"], 3)

    def test_uncertain_and_healthy_results_are_not_counted_as_detected_disease(self):
        farm = Farm.objects.create(
            user=self.farmer, farm_name="Green Valley", address="Lahore",
            latitude=31.5204, longitude=74.3587,
        )
        make_prediction(self.farmer, farm, diagnosis="Healthy")
        Prediction.objects.create(
            user=self.farmer,
            farm=farm,
            uploaded_image=make_image_file(),
            prediction_report=make_report("Late Blight", uncertain=True),
        )

        response = self.client.get(self.url)
        self.assertIsNone(response.data["data"]["most_detected_disease"])

    def test_most_recommended_crop_is_never_fabricated(self):
        response = self.client.get(self.url)
        self.assertIsNone(response.data["data"]["most_recommended_crop"])


class AdminServicesTests(TestCase):
    """Unit tests for adminpanel.services -- the honest mock/real/unreachable
    reporting rules independent of any view.
    """

    @override_settings(ENABLE_MOCK_AI=True)
    def test_check_ai_services_reports_mock_mode(self):
        self.assertEqual(check_ai_services(), "Mock Mode")

    @override_settings(ENABLE_MOCK_AI=False)
    @patch("adminpanel.services.check_stress_module_health", return_value=False)
    @patch("adminpanel.services.check_disease_module_health", return_value=False)
    def test_check_ai_services_reports_unreachable_when_both_down(self, *_mocks):
        self.assertEqual(check_ai_services(), "Unreachable")

    @override_settings(ENABLE_MOCK_AI=False)
    @patch("adminpanel.services.check_stress_module_health", return_value=False)
    @patch("adminpanel.services.check_disease_module_health", return_value=True)
    def test_check_ai_services_reports_degraded_when_one_down(self, *_mocks):
        self.assertEqual(check_ai_services(), "Degraded")

    @override_settings(ENABLE_MOCK_AI=False)
    @patch("adminpanel.services.check_stress_module_health", return_value=True)
    @patch("adminpanel.services.check_disease_module_health", return_value=True)
    def test_check_ai_services_reports_healthy_when_both_up(self, *_mocks):
        self.assertEqual(check_ai_services(), "Healthy")

    def test_compute_overall_system_status_healthy_against_real_db(self):
        self.assertEqual(compute_overall_system_status(), "Healthy")

    def test_get_system_health_returns_all_four_keys(self):
        health = get_system_health()
        self.assertEqual(
            set(health.keys()), {"backend", "database", "ai_services", "weather_api"}
        )

    def test_get_ai_module_status_returns_all_four_keys(self):
        status_map = get_ai_module_status()
        self.assertEqual(
            set(status_map.keys()),
            {"image_module", "soil_module", "weather_module", "fusion_module"},
        )
