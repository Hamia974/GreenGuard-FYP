from unittest.mock import Mock, patch

import requests
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from farms.geocoding import GeocodingError, geocode_address
from users.models import User


def _open_meteo_item(name, admin2, latitude, longitude, feature_code="PPL"):
    return {
        "name": name,
        "latitude": latitude,
        "longitude": longitude,
        "feature_code": feature_code,
        "country": "Pakistan",
        "admin1": "Punjab",
        "admin2": admin2,
    }


def _response(payload, status_code=200):
    return Mock(status_code=status_code, json=Mock(return_value=payload))


@override_settings(GEOCODING_PROVIDER="open_meteo", GEOCODING_COUNTRY_CODE="PK")
class OpenMeteoGeocodingTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    @patch("farms.geocoding.requests.get")
    def test_village_ranked_by_district_from_rest_of_address(self, mock_get):
        mock_get.return_value = _response(
            {
                "results": [
                    _open_meteo_item("Baghbanpura", "Kasur District", 31.22437, 74.09952),
                    _open_meteo_item("Baghbanpura", "Lahore District", 31.58648, 74.37743),
                ]
            }
        )

        results = geocode_address("Village Baghbanpura, Lahore, Punjab, Pakistan")

        self.assertEqual(
            results[0],
            {
                "label": "Baghbanpura, Lahore District, Punjab, Pakistan",
                "latitude": 31.58648,
                "longitude": 74.37743,
            },
        )
        self.assertEqual(len(results), 2)
        params = mock_get.call_args.kwargs["params"]
        self.assertEqual(params["name"], "Baghbanpura")
        self.assertEqual(params["countryCode"], "PK")

    @patch("farms.geocoding.requests.get")
    def test_falls_through_to_next_part_and_drops_fuzzy_matches(self, mock_get):
        mock_get.side_effect = [
            _response({"results": [_open_meteo_item("Chak Number Two", "Sanghar", 26.1, 68.9)]}),
            _response({"results": [_open_meteo_item("Jaranwala", "Faisalabad District", 31.33, 73.41)]}),
        ]

        results = geocode_address("Near Govt School, Tehsil Jaranwala, Faisalabad")

        self.assertEqual(results[0]["label"], "Jaranwala, Faisalabad District, Punjab, Pakistan")

    @patch("farms.geocoding.requests.get")
    def test_province_only_address_is_too_vague(self, mock_get):
        self.assertEqual(geocode_address("Punjab, Pakistan"), [])
        mock_get.assert_not_called()

    @patch("farms.geocoding.requests.get")
    def test_no_results(self, mock_get):
        mock_get.return_value = _response({"generationtime_ms": 0.2})
        self.assertEqual(geocode_address("Qwertyzxv"), [])

    @patch("farms.geocoding.requests.get", side_effect=requests.Timeout("slow"))
    def test_network_failure_raises(self, _mock_get):
        with self.assertRaises(GeocodingError):
            geocode_address("Multan")

    @patch("farms.geocoding.requests.get")
    def test_results_are_cached(self, mock_get):
        mock_get.return_value = _response(
            {"results": [_open_meteo_item("Multan", "Multan District", 30.19679, 71.47824)]}
        )
        geocode_address("Multan")
        geocode_address("  multan ")
        self.assertEqual(mock_get.call_count, 1)


@override_settings(GEOCODING_PROVIDER="google", GEOCODING_COUNTRY_CODE="PK")
class GoogleGeocodingTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    @override_settings(GOOGLE_MAPS_GEOCODING_API_KEY="")
    def test_missing_key_raises(self):
        with self.assertRaises(GeocodingError):
            geocode_address("Lahore")

    @override_settings(GOOGLE_MAPS_GEOCODING_API_KEY="test-key")
    @patch("farms.geocoding.requests.get")
    def test_maps_results_and_drops_country_level_matches(self, mock_get):
        mock_get.return_value = _response(
            {
                "status": "OK",
                "results": [
                    {
                        "formatted_address": "Baghbanpura, Lahore, Punjab, Pakistan",
                        "types": ["sublocality"],
                        "geometry": {"location": {"lat": 31.5865, "lng": 74.3774}},
                    },
                    {
                        "formatted_address": "Pakistan",
                        "types": ["country", "political"],
                        "geometry": {"location": {"lat": 30.3, "lng": 69.3}},
                    },
                ],
            }
        )

        results = geocode_address("Baghbanpura, Lahore", "ur")

        self.assertEqual(
            results,
            [{"label": "Baghbanpura, Lahore, Punjab, Pakistan", "latitude": 31.5865, "longitude": 74.3774}],
        )
        params = mock_get.call_args.kwargs["params"]
        self.assertEqual(params["components"], "country:PK")
        self.assertEqual(params["language"], "ur")

    @override_settings(GOOGLE_MAPS_GEOCODING_API_KEY="test-key")
    @patch("farms.geocoding.requests.get")
    def test_zero_results_and_denied(self, mock_get):
        mock_get.return_value = _response({"status": "ZERO_RESULTS", "results": []})
        self.assertEqual(geocode_address("Nowhere"), [])

        mock_get.return_value = _response({"status": "REQUEST_DENIED"})
        with self.assertRaises(GeocodingError):
            geocode_address("Somewhere else")


class FarmGeocodeViewTests(APITestCase):
    """POST /api/v1/farms/geocode/"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="farmer@example.com",
            password="StrongPass123!",
            first_name="Test",
            last_name="Farmer",
        )
        self.url = reverse("farm-geocode")

    def test_requires_authentication(self):
        response = self.client.post(self.url, {"address": "Lahore"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_empty_address_is_validation_error(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {"address": "   "}, format="json")
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("address", response.data["errors"])

    @patch("farms.views.geocode_address")
    def test_returns_candidates(self, mock_geocode):
        candidate = {"label": "Multan, Punjab, Pakistan", "latitude": 30.19679, "longitude": 71.47824}
        mock_geocode.return_value = [candidate]
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.url, {"address": "Multan", "language": "ur"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"], {"results": [candidate]})
        mock_geocode.assert_called_once_with("Multan", "ur")

    @patch("farms.views.geocode_address", return_value=[])
    def test_no_results_is_empty_list(self, _mock_geocode):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {"address": "Qwertyzxv"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"], {"results": []})

    @patch("farms.views.geocode_address", side_effect=GeocodingError("down"))
    def test_provider_failure_is_503_without_details(self, _mock_geocode):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {"address": "Lahore"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["message"], "Location service is temporarily unavailable.")

    def test_geocode_route_resolves_before_farm_detail(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("farm-detail", args=["geocode"]))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
