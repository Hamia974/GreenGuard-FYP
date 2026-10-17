from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ai_services.module2_client import Module2ServiceError
from farms.models import Farm
from module2.models import Module2Analysis
from users.models import User
from weather.services import WeatherServiceError

VALID_SYMPTOMS = {
    "yellowing_older_leaves": True,
    "purple_reddish_tint": False,
    "brown_scorched_leaf_edges": False,
    "stunted_growth": True,
    "poor_flowering_or_fruiting": False,
    "weak_stems": False,
    "interveinal_chlorosis_older_leaves": False,
    "interveinal_chlorosis_young_leaves": False,
    "leaf_curling_brittle": False,
    "short_internodes_small_leaves": False,
    "none_visible": False,
}

MOCK_WEATHER = {
    "farm_id": "farm_001",
    "timestamp": "2026-09-01T22:39:35Z",
    "weather": {
        "temperature": 30.0,
        "humidity": 55,
        "rainfall_last_7_days_mm": 45.0,
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
        "drought_risk": "Low",
        "drought_reason": "test reason",
    },
    "forecast": None,
    "predicted_risk_assessment": None,
}

# Minimal realistic supported-crop Stress Module response, per
# ai/Stress_Module/samples/sample_response.json's shape -- used wherever a
# test patches call_module2_orchestrator directly rather than exercising the
# real client (ai_services/tests.py covers the client itself).
_MOCK_ORCHESTRATOR_RESPONSE = {
    "crop_supported": True,
    "module2a": {
        "nitrogen_risk": {"level": "high", "confidence": 0.82},
        "phosphorus_risk": {"level": "medium", "confidence": 0.46},
        "potassium_risk": {"level": "low", "confidence": 0.71},
        "magnesium_risk": {"level": "medium", "confidence": 0.48},
        "zinc_risk": {"level": "low", "confidence": 0.66},
        "boron_risk": {"level": "medium", "confidence": 0.44},
        "overall_nutrient_health": "moderate",
        "input_typicality": {"anomaly_score": 0.07, "flag": "typical"},
        "model_version": "module2a-v5",
    },
    "module2b": {
        "ph": {
            "current": 5.1,
            "ideal_range": [6.5, 7.0],
            "gap": 1.4,
            "status": "critical",
            "nutrient_lockout_note": "Soil is strongly acidic.",
        },
        "soil_moisture": {"current": 62, "ideal_range": [50, 75], "gap": 0, "status": "ok"},
        "light": {"current": 28000, "ideal_range": [25000, None], "gap": 0, "status": "ok"},
        "crop_supported": True,
    },
    "overall_soil_health_score": 52.5,
    "overall_soil_health_label": "moderate",
    "recommendation_notes": {
        "headline": "Nitrogen needs attention first.",
        "needs_attention": [
            {
                "nutrient": "Nitrogen",
                "level": "high",
                "confidence_pct": 82,
                "confidence_text": "82% confident — strong match",
                "why": "sandy soil (nutrients wash out faster)",
            }
        ],
        "looking_fine": [
            {
                "nutrient": "Zinc",
                "level": "low",
                "confidence_pct": 66,
                "confidence_text": "66% confident — likely",
            }
        ],
        "caveat": "This advice is based on your answers and soil-meter readings.",
        "soil_condition_note": "Soil is strongly acidic.",
    },
    "model_version": "module2-orchestrator-v1",
    "module2a_model_version": "module2a-v5",
}


@override_settings(ENABLE_MOCK_AI=True)
class Module2AnalyzeTests(APITestCase):
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
        self.url = reverse("module2-analyze")

    def _payload(self, **overrides):
        payload = {
            "farm_id": str(self.farm.id),
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
        payload.update(overrides)
        return payload

    # --- Authentication ---

    def test_requires_authentication(self):
        response = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- Farm resolution / ownership ---

    def test_missing_farm_id_returns_422(self):
        self.client.force_authenticate(user=self.user)
        payload = self._payload()
        del payload["farm_id"]

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("farm_id", response.data["errors"])

    def test_invalid_farm_id_format_returns_422(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.url, self._payload(farm_id="not-a-uuid"), format="json")

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("farm_id", response.data["errors"])

    def test_nonexistent_farm_id_returns_404(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url,
            self._payload(farm_id="8f14e45f-ceea-4c9a-b3f4-000000000099"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data["success"])

    def test_farm_belonging_to_another_user_returns_404(self):
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

        response = self.client.post(
            self.url, self._payload(farm_id=str(other_farm.id)), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data["success"])

    # --- Categorical whitelist validation ---

    def test_invalid_crop_returns_422_with_documented_message(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.url, self._payload(crop="banana"), format="json")

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("crop", response.data["errors"])
        self.assertIn('"banana" is not a valid crop value.', response.data["errors"]["crop"])

    def test_invalid_soil_type_returns_422(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.url, self._payload(soil_type="rocky"), format="json")

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("soil_type", response.data["errors"])

    def test_invalid_irrigation_adequacy_returns_422(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url, self._payload(irrigation_adequacy="flooded"), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("irrigation_adequacy", response.data["errors"])

    # --- Fertilizer conditional logic ---

    def test_days_since_fertilizer_must_be_not_applicable_when_no_fertilizer(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url,
            self._payload(
                last_fertilizer_type="No_Fertilizer", days_since_fertilizer="lt_15_days"
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("days_since_fertilizer", response.data["errors"])

    def test_days_since_fertilizer_must_not_be_not_applicable_when_fertilizer_used(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url,
            self._payload(last_fertilizer_type="Urea", days_since_fertilizer="not_applicable"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("days_since_fertilizer", response.data["errors"])

    def test_valid_fertilizer_and_days_since_combination_passes_validation(self):
        self.client.force_authenticate(user=self.user)

        with patch("module2.views.fetch_weather_for_coordinates", return_value=MOCK_WEATHER):
            response = self.client.post(
                self.url,
                self._payload(
                    last_fertilizer_type="Urea", days_since_fertilizer="lt_15_days"
                ),
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # --- Symptom validation ---

    def test_symptoms_missing_keys_returns_422(self):
        self.client.force_authenticate(user=self.user)
        incomplete_symptoms = dict(VALID_SYMPTOMS)
        del incomplete_symptoms["stunted_growth"]

        response = self.client.post(
            self.url, self._payload(symptoms=incomplete_symptoms), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("symptoms", response.data["errors"])

    def test_symptoms_unexpected_key_returns_422(self):
        self.client.force_authenticate(user=self.user)
        bad_symptoms = dict(VALID_SYMPTOMS)
        bad_symptoms["wilting"] = True

        response = self.client.post(self.url, self._payload(symptoms=bad_symptoms), format="json")

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("symptoms", response.data["errors"])

    def test_none_visible_true_with_other_symptom_true_returns_422(self):
        self.client.force_authenticate(user=self.user)
        bad_symptoms = dict(VALID_SYMPTOMS)
        bad_symptoms["none_visible"] = True
        bad_symptoms["stunted_growth"] = True

        response = self.client.post(self.url, self._payload(symptoms=bad_symptoms), format="json")

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("symptoms", response.data["errors"])

    def test_none_visible_alone_is_valid(self):
        self.client.force_authenticate(user=self.user)
        symptoms = {key: False for key in VALID_SYMPTOMS}
        symptoms["none_visible"] = True

        with patch("module2.views.fetch_weather_for_coordinates", return_value=MOCK_WEATHER):
            response = self.client.post(self.url, self._payload(symptoms=symptoms), format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # --- Required numeric meter readings ---
    # As of the Stress Module's v1.1.0 delivery (2026-09-10), a soil meter
    # ships with the deployment, so ph_value/soil_moisture_pct/
    # light_intensity_lux are required -- missing, null, or out-of-range must
    # be rejected with 422, never defaulted or silently accepted.

    def test_missing_ph_value_returns_422(self):
        self.client.force_authenticate(user=self.user)
        payload = self._payload()
        del payload["ph_value"]

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("ph_value", response.data["errors"])

    def test_null_ph_value_returns_422(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.url, self._payload(ph_value=None), format="json")

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("ph_value", response.data["errors"])

    def test_missing_soil_moisture_pct_returns_422(self):
        self.client.force_authenticate(user=self.user)
        payload = self._payload()
        del payload["soil_moisture_pct"]

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("soil_moisture_pct", response.data["errors"])

    def test_missing_light_intensity_lux_returns_422(self):
        self.client.force_authenticate(user=self.user)
        payload = self._payload()
        del payload["light_intensity_lux"]

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("light_intensity_lux", response.data["errors"])

    def test_ph_value_out_of_range_returns_422(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.url, self._payload(ph_value=14.5), format="json")

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("ph_value", response.data["errors"])

    def test_soil_moisture_pct_out_of_range_returns_422(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url, self._payload(soil_moisture_pct=101), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("soil_moisture_pct", response.data["errors"])

    def test_light_intensity_lux_negative_returns_422(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url, self._payload(light_intensity_lux=-1), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("light_intensity_lux", response.data["errors"])

    def test_meter_readings_accept_valid_values(self):
        self.client.force_authenticate(user=self.user)

        with patch("module2.views.fetch_weather_for_coordinates", return_value=MOCK_WEATHER):
            response = self.client.post(
                self.url,
                self._payload(ph_value=5.1, soil_moisture_pct=62, light_intensity_lux=28000),
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # --- Unsupported crop behavior ---
    # All 15 catalog crops are trained-and-supported as of module2a-v5
    # (2026-09-10) -- module2_field_options.json's crop_model_support no
    # longer has a "pending retrain" subset, so no valid `crop` choice can
    # reach the unsupported-crop branch through the public API today. The
    # branch itself is still defensive code (a future crop could be added to
    # the categorical list before a retrain), so it is exercised directly by
    # patching crop_model_support() rather than via a real unsupported crop.

    def test_unsupported_crop_short_circuits_without_calling_weather_or_ai(self):
        self.client.force_authenticate(user=self.user)

        with (
            patch(
                "module2.views.crop_model_support",
                return_value={"trained_and_supported": []},
            ),
            patch("module2.views.fetch_weather_for_coordinates") as mock_weather,
            patch("module2.views.call_module2_orchestrator") as mock_ai,
        ):
            response = self.client.post(self.url, self._payload(crop="wheat"), format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        data = response.data["data"]
        self.assertFalse(data["crop_supported"])
        self.assertIsNone(data["module2a"])
        self.assertIsNone(data["module2b"])
        self.assertIsNone(data["overall_soil_health_score"])
        self.assertIsNone(data["overall_soil_health_label"])
        self.assertIsNone(data["recommendation_notes"])
        mock_weather.assert_not_called()
        mock_ai.assert_not_called()

    def test_all_fifteen_crops_are_supported(self):
        self.client.force_authenticate(user=self.user)
        all_crops = [
            "wheat", "rice", "cotton", "sugarcane", "maize", "potato", "tomato", "chickpea",
            "eggplant", "cucumber", "bitter_gourd", "snake_gourd", "ridge_gourd", "ash_gourd",
            "bottle_gourd",
        ]
        for crop in all_crops:
            with (
                self.subTest(crop=crop),
                patch("module2.views.fetch_weather_for_coordinates", return_value=MOCK_WEATHER),
                patch("module2.views.call_module2_orchestrator") as mock_ai,
            ):
                mock_ai.return_value = dict(_MOCK_ORCHESTRATOR_RESPONSE)
                response = self.client.post(self.url, self._payload(crop=crop), format="json")
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertTrue(response.data["data"]["crop_supported"])
                mock_ai.assert_called_once()

    # --- Weather / AI failures ---

    def test_weather_service_failure_returns_503(self):
        self.client.force_authenticate(user=self.user)

        with patch(
            "module2.views.fetch_weather_for_coordinates",
            side_effect=WeatherServiceError("Weather service is temporarily unavailable."),
        ):
            response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["message"], "Weather service is temporarily unavailable.")

    def test_weather_failure_does_not_call_module2(self):
        self.client.force_authenticate(user=self.user)

        with (
            patch(
                "module2.views.fetch_weather_for_coordinates",
                side_effect=WeatherServiceError("Weather service is temporarily unavailable."),
            ),
            patch("module2.views.call_module2_orchestrator") as mock_ai,
        ):
            response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        mock_ai.assert_not_called()

    def test_ai_service_failure_returns_500(self):
        self.client.force_authenticate(user=self.user)

        with (
            patch("module2.views.fetch_weather_for_coordinates", return_value=MOCK_WEATHER),
            patch(
                "module2.views.call_module2_orchestrator",
                side_effect=Module2ServiceError("boom"),
            ),
        ):
            response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["message"], "AI module is currently unavailable.")

    # --- Successful orchestration / response shape ---

    @override_settings(ENABLE_MOCK_AI=True)
    def test_successful_supported_crop_check_in_mock_mode(self):
        self.client.force_authenticate(user=self.user)

        with patch("module2.views.fetch_weather_for_coordinates", return_value=MOCK_WEATHER):
            response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(
            response.data["message"], "Soil & nutrient health check completed successfully."
        )
        data = response.data["data"]
        self.assertTrue(data["crop_supported"])
        self.assertEqual(data["model_version"], "module2-orchestrator-mock")
        self.assertEqual(data["module2a_model_version"], "module2a-v5-mock")
        for risk_field in (
            "nitrogen_risk",
            "phosphorus_risk",
            "potassium_risk",
            "magnesium_risk",
            "zinc_risk",
            "boron_risk",
        ):
            self.assertIn(risk_field, data["module2a"])
            self.assertIn(data["module2a"][risk_field]["level"], ("high", "medium", "low"))
        self.assertIn("input_typicality", data["module2a"])
        self.assertIn(data["module2a"]["input_typicality"]["flag"], ("typical", "unusual"))
        self.assertIn(data["overall_soil_health_label"], ("good", "moderate", "poor"))
        self.assertIsNotNone(data["recommendation_notes"])
        self.assertIn("headline", data["recommendation_notes"])
        self.assertIn("caveat", data["recommendation_notes"])

    def test_orchestrator_payload_maps_weather_to_module2_field_names(self):
        self.client.force_authenticate(user=self.user)

        with (
            patch("module2.views.fetch_weather_for_coordinates", return_value=MOCK_WEATHER),
            patch("module2.views.call_module2_orchestrator") as mock_ai,
        ):
            mock_ai.return_value = dict(_MOCK_ORCHESTRATOR_RESPONSE)
            self.client.post(
                self.url,
                self._payload(ph_value=5.1, soil_moisture_pct=62, light_intensity_lux=28000),
                format="json",
            )

        called_payload = mock_ai.call_args[0][0]
        self.assertEqual(called_payload["temperature_c"], MOCK_WEATHER["weather"]["temperature"])
        self.assertEqual(called_payload["humidity_pct"], MOCK_WEATHER["weather"]["humidity"])
        self.assertEqual(
            called_payload["rainfall_mm_last_7_days"],
            MOCK_WEATHER["weather"]["rainfall_last_7_days_mm"],
        )
        self.assertEqual(called_payload["ph_value"], 5.1)
        self.assertEqual(called_payload["soil_moisture_pct"], 62)
        self.assertEqual(called_payload["light_intensity_lux"], 28000)
        self.assertNotIn("temperature", called_payload)
        self.assertNotIn("humidity", called_payload)
        self.assertNotIn("rainfall", called_payload)

    def test_weather_resolved_from_farm_coordinates_not_request_body(self):
        self.client.force_authenticate(user=self.user)

        with patch(
            "module2.views.fetch_weather_for_coordinates", return_value=MOCK_WEATHER
        ) as mock_weather:
            self.client.post(self.url, self._payload(), format="json")

        called_args, called_kwargs = mock_weather.call_args
        self.assertEqual(float(called_args[0]), float(self.farm.latitude))
        self.assertEqual(float(called_args[1]), float(self.farm.longitude))


@override_settings(ENABLE_MOCK_AI=True)
class Module2AnalysisPersistenceTests(APITestCase):
    """Module2Analysis persistence, per DATABASE_SPECIFICATION.md section 6A.

    Verifies persistence is a side effect only -- the response assertions
    mirror Module2AnalyzeTests exactly, so any accidental contract change
    here would fail the same way it would there.
    """

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
        self.url = reverse("module2-analyze")

    def _payload(self, **overrides):
        payload = {
            "farm_id": str(self.farm.id),
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
        payload.update(overrides)
        return payload

    def test_supported_crop_check_creates_module2_analysis(self):
        self.client.force_authenticate(user=self.user)

        with patch("module2.views.fetch_weather_for_coordinates", return_value=MOCK_WEATHER):
            response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(Module2Analysis.objects.count(), 1)
        record = Module2Analysis.objects.get()
        self.assertEqual(record.farm, self.farm)
        self.assertTrue(record.crop_supported)
        self.assertEqual(record.request_payload["crop"], "wheat")
        self.assertEqual(record.request_payload["farm_id"], str(self.farm.id))
        self.assertEqual(record.response_payload, response.data["data"])
        self.assertIsNotNone(record.created_at)

    def test_unsupported_crop_check_also_creates_module2_analysis(self):
        # See Module2AnalyzeTests' "Unsupported crop behavior" note -- all 15
        # catalog crops are trained-and-supported today, so this exercises
        # the defensive short-circuit branch via a patched crop_model_support()
        # rather than a real unsupported crop value.
        self.client.force_authenticate(user=self.user)

        with patch(
            "module2.views.crop_model_support",
            return_value={"trained_and_supported": []},
        ):
            response = self.client.post(self.url, self._payload(crop="wheat"), format="json")

        self.assertEqual(Module2Analysis.objects.count(), 1)
        record = Module2Analysis.objects.get()
        self.assertFalse(record.crop_supported)
        self.assertFalse(response.data["data"]["crop_supported"])
        self.assertEqual(record.response_payload, response.data["data"])

    def test_validation_failure_does_not_create_module2_analysis(self):
        self.client.force_authenticate(user=self.user)

        self.client.post(self.url, self._payload(crop="banana"), format="json")

        self.assertEqual(Module2Analysis.objects.count(), 0)

    def test_multiple_runs_create_multiple_immutable_records(self):
        self.client.force_authenticate(user=self.user)

        with patch("module2.views.fetch_weather_for_coordinates", return_value=MOCK_WEATHER):
            self.client.post(self.url, self._payload(growth_stage="vegetative"), format="json")
            self.client.post(self.url, self._payload(growth_stage="flowering"), format="json")

        self.assertEqual(Module2Analysis.objects.count(), 2)
        stages = set(
            Module2Analysis.objects.values_list("request_payload__growth_stage", flat=True)
        )
        self.assertEqual(stages, {"vegetative", "flowering"})

        first_record = Module2Analysis.objects.earliest("created_at")
        first_record.refresh_from_db()
        self.assertEqual(first_record.request_payload["growth_stage"], "vegetative")

    def test_latest_analysis_for_farm_is_retrievable_ordered_by_created_at(self):
        self.client.force_authenticate(user=self.user)

        with patch("module2.views.fetch_weather_for_coordinates", return_value=MOCK_WEATHER):
            self.client.post(self.url, self._payload(growth_stage="vegetative"), format="json")
            self.client.post(self.url, self._payload(growth_stage="flowering"), format="json")

        latest = Module2Analysis.objects.filter(farm=self.farm).order_by("-created_at").first()

        self.assertEqual(latest.request_payload["growth_stage"], "flowering")
