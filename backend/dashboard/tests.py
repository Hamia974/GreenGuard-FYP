from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from farms.models import Farm
from history.tests import make_report
from notifications.models import Notification
from predictions.models import Prediction
from predictions.tests import make_image_file
from users.models import User
from weather.services import WeatherServiceError


class DashboardOverviewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="farmer@example.com",
            password="StrongPass123!",
            first_name="Hamia",
            last_name="Khalil",
        )
        self.url = reverse("dashboard-overview")

    def test_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_welcome_message_and_empty_states(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.data
        self.assertTrue(body["success"])
        data = body["data"]
        self.assertEqual(data["welcome_message"], "Welcome back, Hamia Khalil")
        self.assertEqual(data["total_predictions"], 0)
        self.assertEqual(data["recent_predictions"], 0)
        self.assertEqual(data["notification_count"], 0)
        self.assertIsNone(data["weather_summary"])
        self.assertEqual(data["farm_summary"], {"total_farms": 0})
        self.assertEqual(
            data["prediction_statistics"],
            {"healthy_count": 0, "diseased_count": 0, "accuracy": None},
        )

    def test_farm_summary_reflects_only_the_authenticated_users_farms(self):
        other_user = User.objects.create_user(
            email="other@example.com",
            password="StrongPass123!",
            first_name="Other",
            last_name="Farmer",
        )
        Farm.objects.create(
            user=self.user,
            farm_name="North Field",
            address="123 Farm Rd",
            latitude="31.5204",
            longitude="74.3587",
        )
        Farm.objects.create(
            user=self.user,
            farm_name="South Field",
            address="456 Farm Rd",
            latitude="31.4",
            longitude="74.2",
        )
        Farm.objects.create(
            user=other_user,
            farm_name="Someone Else's Field",
            address="789 Farm Rd",
            latitude="31.1",
            longitude="74.1",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.data["data"]["farm_summary"], {"total_farms": 2})

    def test_notification_count_reflects_real_unread_count(self):
        other_user = User.objects.create_user(
            email="other@example.com",
            password="StrongPass123!",
            first_name="Other",
            last_name="Farmer",
        )
        Notification.objects.create(user=self.user, title="Unread 1", message="m")
        Notification.objects.create(user=self.user, title="Unread 2", message="m")
        Notification.objects.create(
            user=self.user, title="Already read", message="m", is_read=True
        )
        Notification.objects.create(user=other_user, title="Not mine", message="m")

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.data["data"]["notification_count"], 2)


class DashboardWeatherTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="farmer@example.com",
            password="StrongPass123!",
            first_name="Hamia",
            last_name="Khalil",
        )
        self.url = reverse("dashboard-weather")

    def test_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_empty_weather_fields_when_user_has_no_farm(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        for field in (
            "temperature",
            "humidity",
            "rainfall",
            "wind_speed",
            "fungal_disease_risk",
            "heat_stress_risk",
            "drought_risk",
        ):
            self.assertIsNone(data[field])

    @patch("dashboard.views.fetch_weather_for_coordinates")
    def test_returns_real_weather_for_users_only_farm_when_no_farm_id_given(self, mock_fetch):
        farm = Farm.objects.create(
            user=self.user,
            farm_name="North Field",
            address="123 Farm Rd",
            latitude="31.5204",
            longitude="74.3587",
        )
        mock_fetch.return_value = {
            "farm_id": "farm_001",
            "timestamp": "2026-09-01T22:39:35Z",
            "weather": {
                "temperature": 33.4,
                "humidity": 84,
                "rainfall_last_7_days_mm": 2.3,
                "wind_speed": 9.1,
            },
            "units": {
                "temperature": "celsius",
                "humidity": "percent",
                "rainfall_last_7_days_mm": "mm",
                "wind_speed": "m/s",
            },
            "risk_assessment": {
                "fungal_disease_risk": "High",
                "fungal_disease_reason": "test reason",
                "heat_stress_risk": "Moderate",
                "heat_stress_reason": "test reason",
                "drought_risk": "Low",
                "drought_reason": "test reason",
            },
            "forecast": None,
            "predicted_risk_assessment": None,
        }

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["temperature"], 33.4)
        self.assertEqual(response.data["data"]["rainfall"], 2.3)
        self.assertEqual(response.data["data"]["fungal_disease_risk"], "High")
        mock_fetch.assert_called_once()
        called_args, called_kwargs = mock_fetch.call_args
        self.assertEqual(float(called_args[0]), float(farm.latitude))
        self.assertEqual(float(called_args[1]), float(farm.longitude))

    @patch("dashboard.views.fetch_weather_for_coordinates")
    def test_returns_weather_for_requested_farm_id(self, mock_fetch):
        Farm.objects.create(
            user=self.user,
            farm_name="North Field",
            address="123 Farm Rd",
            latitude="31.5204",
            longitude="74.3587",
        )
        south_field = Farm.objects.create(
            user=self.user,
            farm_name="South Field",
            address="456 Farm Rd",
            latitude="31.4",
            longitude="74.2",
        )
        mock_fetch.return_value = {
            "farm_id": "farm_002",
            "timestamp": "2026-09-01T22:39:35Z",
            "weather": {
                "temperature": 30.0,
                "humidity": 60,
                "rainfall_last_7_days_mm": 0.0,
                "wind_speed": 5.0,
            },
            "units": {
                "temperature": "celsius",
                "humidity": "percent",
                "rainfall_last_7_days_mm": "mm",
                "wind_speed": "m/s",
            },
            "risk_assessment": {
                "fungal_disease_risk": "Low",
                "fungal_disease_reason": "test reason",
                "heat_stress_risk": "Low",
                "heat_stress_reason": "test reason",
                "drought_risk": "High",
                "drought_reason": "test reason",
            },
            "forecast": None,
            "predicted_risk_assessment": None,
        }

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {"farm_id": str(south_field.id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        called_args, _ = mock_fetch.call_args
        self.assertEqual(float(called_args[0]), float(south_field.latitude))

    def test_returns_404_when_requested_farm_id_does_not_belong_to_user(self):
        other_user = User.objects.create_user(
            email="other@example.com",
            password="StrongPass123!",
            first_name="Other",
            last_name="Farmer",
        )
        other_farm = Farm.objects.create(
            user=other_user,
            farm_name="Someone Else's Field",
            address="789 Farm Rd",
            latitude="31.1",
            longitude="74.1",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {"farm_id": str(other_farm.id)})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data["success"])

    @patch("dashboard.views.fetch_weather_for_coordinates")
    def test_returns_503_when_weather_service_unavailable(self, mock_fetch):
        Farm.objects.create(
            user=self.user,
            farm_name="North Field",
            address="123 Farm Rd",
            latitude="31.5204",
            longitude="74.3587",
        )
        mock_fetch.side_effect = WeatherServiceError("Weather service is temporarily unavailable.")

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["message"], "Weather service is temporarily unavailable.")


class DashboardRecentPredictionsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="farmer@example.com",
            password="StrongPass123!",
            first_name="Hamia",
            last_name="Khalil",
        )
        self.url = reverse("dashboard-recent-predictions")

    def test_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_empty_list(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {"limit": 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"], [])


class DashboardRecommendationsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="farmer@example.com",
            password="StrongPass123!",
            first_name="Hamia",
            last_name="Khalil",
        )
        self.url = reverse("dashboard-recommendations")

    def test_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_empty_list(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"], [])


class DashboardModuleResultTests(APITestCase):
    """Dashboard figures come only from each analysis's own Module 1 result."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="farmer@example.com",
            password="StrongPass123!",
            first_name="Hamia",
            last_name="Khalil",
        )
        self.farm = Farm.objects.create(
            user=self.user,
            farm_name="North Field",
            address="123 Farm Rd",
            latitude="31.5204",
            longitude="74.3587",
        )
        for report in (
            make_report("Yellow Rust", 0.88),
            make_report("Healthy", 0.97, is_healthy=True),
            make_report("Septoria", 0.4, uncertain=True),
        ):
            Prediction.objects.create(
                user=self.user,
                farm=self.farm,
                uploaded_image=make_image_file(),
                prediction_report=report,
            )
        self.client.force_authenticate(user=self.user)

    def test_overview_counts_module1_health_flags(self):
        data = self.client.get(reverse("dashboard-overview")).data["data"]

        self.assertEqual(data["total_predictions"], 3)
        self.assertEqual(data["recent_predictions"], 3)
        self.assertEqual(
            data["prediction_statistics"],
            {"healthy_count": 1, "diseased_count": 1, "accuracy": None},
        )

    def test_recent_predictions_use_module1_result_newest_first(self):
        response = self.client.get(reverse("dashboard-recent-predictions"), {"limit": 5})

        items = response.data["data"]
        self.assertEqual(len(items), 3)
        self.assertEqual(
            set(items[0].keys()), {"prediction_id", "diagnosis", "confidence", "created_at"}
        )
        self.assertIsNone(items[0]["diagnosis"])
        self.assertIsNone(items[0]["confidence"])
        self.assertEqual(items[2]["diagnosis"], "Yellow Rust")
        self.assertEqual(items[2]["confidence"], 0.88)

    def test_recent_predictions_respects_limit(self):
        response = self.client.get(reverse("dashboard-recent-predictions"), {"limit": 1})

        self.assertEqual(len(response.data["data"]), 1)

    def test_recent_predictions_exclude_other_users(self):
        other = User.objects.create_user(
            email="other@example.com",
            password="StrongPass123!",
            first_name="Other",
            last_name="Farmer",
        )
        self.client.force_authenticate(user=other)

        response = self.client.get(reverse("dashboard-recent-predictions"))

        self.assertEqual(response.data["data"], [])
