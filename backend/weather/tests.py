import copy
from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from farms.models import Farm
from users.models import User
from weather.services import (
    WeatherServiceError,
    _MOCK_RESPONSE,
    check_weather_module_health,
    fetch_weather_for_coordinates,
    to_dashboard_summary,
)

# Mirrors ai/Weather_Module/Weather_Module/samples/sample_response.json
# exactly -- the real module's own documented "real, live-captured
# response" example -- so these tests exercise the actual delivered
# contract shape, not an invented one.
SAMPLE_RESPONSE = {
    "farm_id": "farm_001",
    "timestamp": "2026-09-01T22:39:35Z",
    "weather": {
        "temperature": 28.0,
        "humidity": 78.0,
        "rainfall_last_7_days_mm": 1.8,
        "wind_speed": 2.2,
    },
    "units": {
        "temperature": "celsius",
        "humidity": "percent",
        "rainfall_last_7_days_mm": "mm",
        "wind_speed": "m/s",
    },
    "risk_assessment": {
        "fungal_disease_risk": "Moderate",
        "fungal_disease_reason": "Humidity is 78%, above the 65% threshold that raises fungal risk.",
        "heat_stress_risk": "Low",
        "heat_stress_reason": "Current temperature (28.0°C) is at or below 35°C.",
        "drought_risk": "High",
        "drought_reason": "Only 1.8mm of rain fell in the last 7 days, below the 10mm high-drought threshold.",
    },
    "forecast": {
        "temperature": 31.5,
        "humidity": 63.5,
        "rainfall_mm": 2.0,
    },
    "predicted_risk_assessment": {
        "fungal_disease_risk": "Low",
        "fungal_disease_reason": "Humidity (63.5%) is below the 65% risk threshold.",
        "heat_stress_risk": "Low",
        "heat_stress_reason": "Current temperature (31.5°C) is at or below 35°C.",
        "drought_risk": "High",
        "drought_reason": "Only 3.8mm of rain fell in the last 7 days, below the 10mm high-drought threshold.",
    },
}


def _mock_post_response(status_code=200, json_body=None, text=""):
    response = Mock()
    response.status_code = status_code
    response.text = text
    if json_body is not None:
        response.json.return_value = json_body
    else:
        response.json.side_effect = ValueError("No JSON")
    return response


@override_settings(ENABLE_MOCK_AI=False, WEATHER_MODULE_URL="http://weather-module.test")
class FetchWeatherForCoordinatesTests(SimpleTestCase):
    """Exercises the real (non-mock) HTTP path against a deterministic
    fixture based on the Weather Module's own sample_response.json --
    never against the real Open-Meteo network."""

    @patch("weather.services.requests.post")
    def test_successful_request_forwards_response_unmodified(self, mock_post):
        mock_post.return_value = _mock_post_response(200, copy.deepcopy(SAMPLE_RESPONSE))

        result = fetch_weather_for_coordinates(31.5204, 74.3587, farm_id="farm_001")

        self.assertEqual(result, SAMPLE_RESPONSE)

    @patch("weather.services.requests.post")
    def test_farm_id_is_sent_to_the_module(self, mock_post):
        mock_post.return_value = _mock_post_response(200, copy.deepcopy(SAMPLE_RESPONSE))

        fetch_weather_for_coordinates(31.5204, 74.3587, farm_id="farm_001")

        sent_payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(sent_payload, {"latitude": 31.5204, "longitude": 74.3587, "farm_id": "farm_001"})

    @patch("weather.services.requests.post")
    def test_missing_farm_id_defaults_to_unknown(self, mock_post):
        mock_post.return_value = _mock_post_response(200, copy.deepcopy(SAMPLE_RESPONSE))

        fetch_weather_for_coordinates(31.5204, 74.3587)

        sent_payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(sent_payload["farm_id"], "unknown")

    @patch("weather.services.requests.post")
    def test_farm_id_is_returned_unchanged(self, mock_post):
        body = copy.deepcopy(SAMPLE_RESPONSE)
        body["farm_id"] = "farm_042"
        mock_post.return_value = _mock_post_response(200, body)

        result = fetch_weather_for_coordinates(31.5204, 74.3587, farm_id="farm_042")

        self.assertEqual(result["farm_id"], "farm_042")

    @patch("weather.services.requests.post")
    def test_units_are_passed_through_unchanged(self, mock_post):
        mock_post.return_value = _mock_post_response(200, copy.deepcopy(SAMPLE_RESPONSE))

        result = fetch_weather_for_coordinates(31.5204, 74.3587)

        self.assertEqual(result["units"], SAMPLE_RESPONSE["units"])

    @patch("weather.services.requests.post")
    def test_reason_fields_are_passed_through_unchanged(self, mock_post):
        mock_post.return_value = _mock_post_response(200, copy.deepcopy(SAMPLE_RESPONSE))

        result = fetch_weather_for_coordinates(31.5204, 74.3587)

        self.assertEqual(
            result["risk_assessment"]["fungal_disease_reason"],
            SAMPLE_RESPONSE["risk_assessment"]["fungal_disease_reason"],
        )

    def test_low_moderate_high_risk_labels_pass_through_unchanged(self):
        for level in ("Low", "Moderate", "High"):
            body = copy.deepcopy(SAMPLE_RESPONSE)
            body["risk_assessment"]["drought_risk"] = level
            with patch("weather.services.requests.post", return_value=_mock_post_response(200, body)):
                result = fetch_weather_for_coordinates(31.5204, 74.3587)
            self.assertEqual(result["risk_assessment"]["drought_risk"], level)

    @patch("weather.services.requests.post")
    def test_forecast_present_is_forwarded(self, mock_post):
        mock_post.return_value = _mock_post_response(200, copy.deepcopy(SAMPLE_RESPONSE))

        result = fetch_weather_for_coordinates(31.5204, 74.3587)

        self.assertEqual(result["forecast"], SAMPLE_RESPONSE["forecast"])
        self.assertEqual(result["predicted_risk_assessment"], SAMPLE_RESPONSE["predicted_risk_assessment"])

    @patch("weather.services.requests.post")
    def test_forecast_null_is_preserved_as_null_not_fabricated(self, mock_post):
        body = copy.deepcopy(SAMPLE_RESPONSE)
        body["forecast"] = None
        body["predicted_risk_assessment"] = None
        mock_post.return_value = _mock_post_response(200, body)

        result = fetch_weather_for_coordinates(31.5204, 74.3587)

        self.assertIsNone(result["forecast"])
        self.assertIsNone(result["predicted_risk_assessment"])

    @patch("weather.services.requests.post")
    def test_missing_forecast_key_entirely_is_not_an_error(self, mock_post):
        body = copy.deepcopy(SAMPLE_RESPONSE)
        del body["forecast"]
        del body["predicted_risk_assessment"]
        mock_post.return_value = _mock_post_response(200, body)

        result = fetch_weather_for_coordinates(31.5204, 74.3587)

        self.assertEqual(result["risk_assessment"], SAMPLE_RESPONSE["risk_assessment"])

    @patch("weather.services.requests.post")
    def test_http_500_raises_weather_service_error(self, mock_post):
        # Per the module's documented 500 contract: {"message": "..."}.
        mock_post.return_value = _mock_post_response(
            500, {"message": "Prediction Failed: weather service unavailable."}
        )

        with self.assertRaises(WeatherServiceError):
            fetch_weather_for_coordinates(31.5204, 74.3587)

    @patch("weather.services.requests.post")
    def test_http_422_raises_weather_service_error(self, mock_post):
        # FastAPI's default validation-error shape: {"detail": [...]}.
        mock_post.return_value = _mock_post_response(422, {"detail": [{"msg": "invalid latitude"}]})

        with self.assertRaises(WeatherServiceError):
            fetch_weather_for_coordinates(999, 74.3587)

    @patch("weather.services.requests.post")
    def test_malformed_json_raises_weather_service_error(self, mock_post):
        mock_post.return_value = _mock_post_response(200, json_body=None)

        with self.assertRaises(WeatherServiceError):
            fetch_weather_for_coordinates(31.5204, 74.3587)

    @patch("weather.services.requests.post")
    def test_missing_required_top_level_field_raises_weather_service_error(self, mock_post):
        body = copy.deepcopy(SAMPLE_RESPONSE)
        del body["risk_assessment"]
        mock_post.return_value = _mock_post_response(200, body)

        with self.assertRaises(WeatherServiceError):
            fetch_weather_for_coordinates(31.5204, 74.3587)

    @patch("weather.services.requests.post")
    def test_missing_required_weather_field_raises_weather_service_error(self, mock_post):
        body = copy.deepcopy(SAMPLE_RESPONSE)
        del body["weather"]["wind_speed"]
        mock_post.return_value = _mock_post_response(200, body)

        with self.assertRaises(WeatherServiceError):
            fetch_weather_for_coordinates(31.5204, 74.3587)

    @patch("weather.services.requests.post")
    def test_connection_error_raises_weather_service_error(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError("connection refused")

        with self.assertRaises(WeatherServiceError):
            fetch_weather_for_coordinates(31.5204, 74.3587)

    @patch("weather.services.requests.post")
    def test_timeout_raises_weather_service_error(self, mock_post):
        mock_post.side_effect = requests.exceptions.Timeout("timed out")

        with self.assertRaises(WeatherServiceError):
            fetch_weather_for_coordinates(31.5204, 74.3587)

    @patch("weather.services.requests.get")
    def test_health_check_true_on_200(self, mock_get):
        mock_get.return_value = Mock(status_code=200)
        self.assertTrue(check_weather_module_health())

    @patch("weather.services.requests.get")
    def test_health_check_false_on_non_200(self, mock_get):
        mock_get.return_value = Mock(status_code=503)
        self.assertFalse(check_weather_module_health())

    @patch("weather.services.requests.get")
    def test_health_check_false_on_connection_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("refused")
        self.assertFalse(check_weather_module_health())


class MockModeTests(SimpleTestCase):
    @override_settings(ENABLE_MOCK_AI=True)
    def test_mock_mode_returns_fixed_response_matching_module_contract(self):
        result = fetch_weather_for_coordinates(31.5204, 74.3587, farm_id="farm_001")

        self.assertEqual(result["farm_id"], "farm_001")
        self.assertIn("weather", result)
        self.assertIn("risk_assessment", result)
        self.assertEqual(result["units"], _MOCK_RESPONSE["units"])

    @override_settings(ENABLE_MOCK_AI=True)
    def test_mock_mode_never_calls_the_real_module(self):
        with patch("weather.services.requests.post") as mock_post:
            fetch_weather_for_coordinates(31.5204, 74.3587)
        mock_post.assert_not_called()

    @override_settings(ENABLE_MOCK_AI=True)
    def test_mock_mode_health_check_reports_not_connected(self):
        # Mock Mode must never claim a live connection to the real module.
        self.assertFalse(check_weather_module_health())


class ToDashboardSummaryTests(SimpleTestCase):
    """The dashboard's flat legacy contract (REST_API_SPEC.md section 5) is
    unchanged by this integration -- only its data source is. These tests
    confirm the flattening is pure field access, with no risk recalculation:
    module3.py's `if humidity > ...`-style logic must never reappear here."""

    def test_flattens_nested_contract_without_recalculating_anything(self):
        result = to_dashboard_summary(SAMPLE_RESPONSE)

        self.assertEqual(
            result,
            {
                "temperature": 28.0,
                "humidity": 78.0,
                "rainfall": 1.8,
                "wind_speed": 2.2,
                "fungal_disease_risk": "Moderate",
                "heat_stress_risk": "Low",
                "drought_risk": "High",
            },
        )

    def test_no_duplicate_risk_calculation_logic_exists_in_this_module(self):
        import weather.services as services_module

        self.assertFalse(hasattr(services_module, "assess_weather_risk"))
        self.assertFalse(hasattr(services_module, "assess_risk"))


class WeatherCurrentViewTests(APITestCase):
    """GET /api/v1/weather/current/ -- the full Module 3 report for the
    Weather page (see frontend/app/(app)/weather/)."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="farmer@example.com",
            password="StrongPass123!",
            first_name="Hamia",
            last_name="Khalil",
        )
        self.url = reverse("weather-current")

    def test_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_farm_returns_empty_state(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIsNone(response.data["data"])

    @patch("weather.views.fetch_weather_for_coordinates")
    def test_returns_full_nested_contract_for_users_farm(self, mock_fetch):
        farm = Farm.objects.create(
            user=self.user,
            farm_name="North Field",
            address="123 Farm Rd",
            latitude="31.5204",
            longitude="74.3587",
        )
        mock_fetch.return_value = copy.deepcopy(SAMPLE_RESPONSE)

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"], SAMPLE_RESPONSE)
        self.assertIn("units", response.data["data"])
        self.assertIn("forecast", response.data["data"])
        self.assertIn("predicted_risk_assessment", response.data["data"])
        called_args, _ = mock_fetch.call_args
        self.assertEqual(float(called_args[0]), float(farm.latitude))
        self.assertEqual(float(called_args[1]), float(farm.longitude))

    @patch("weather.views.fetch_weather_for_coordinates")
    def test_null_forecast_is_preserved_not_hidden(self, mock_fetch):
        Farm.objects.create(
            user=self.user,
            farm_name="North Field",
            address="123 Farm Rd",
            latitude="31.5204",
            longitude="74.3587",
        )
        body = copy.deepcopy(SAMPLE_RESPONSE)
        body["forecast"] = None
        body["predicted_risk_assessment"] = None
        mock_fetch.return_value = body

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertIsNone(response.data["data"]["forecast"])
        self.assertIsNone(response.data["data"]["predicted_risk_assessment"])

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

    @patch("weather.views.fetch_weather_for_coordinates")
    def test_returns_503_when_weather_module_unavailable(self, mock_fetch):
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
