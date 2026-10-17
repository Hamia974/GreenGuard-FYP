from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase, override_settings

from ai_services.module2_client import (
    Module2ServiceError,
    call_module2_orchestrator,
    check_stress_module_health,
)


_MODULE2_SUCCESS = {
    "crop_supported": True,
    "module2a": {
        "nitrogen_risk": {"level": "high", "confidence": 0.95},
        "phosphorus_risk": {"level": "low", "confidence": 0.39},
        "potassium_risk": {"level": "medium", "confidence": 0.55},
        "magnesium_risk": {"level": "high", "confidence": 0.41},
        "zinc_risk": {"level": "low", "confidence": 0.7},
        "boron_risk": {"level": "high", "confidence": 0.42},
        "overall_nutrient_health": "moderate",
        "input_typicality": {"anomaly_score": 0.065, "flag": "typical"},
        "model_version": "module2a-v5",
    },
    "module2b": {
        "ph": {
            "current": 4.5,
            "ideal_range": [6.0, 7.5],
            "gap": 1.5,
            "status": "critical",
            "nutrient_lockout_note": "Soil is strongly acidic.",
        },
        "soil_moisture": {"current": 62.0, "ideal_range": [50.0, 70.0], "gap": 0.0, "status": "ok"},
        "light": {"current": 28000.0, "ideal_range": [25000.0, None], "gap": 0.0, "status": "ok"},
        "crop_supported": True,
    },
    "overall_soil_health_score": 47.5,
    "overall_soil_health_label": "poor",
    "recommendation_notes": {
        "headline": "Nitrogen needs attention first.",
        "needs_attention": [
            {
                "nutrient": "Nitrogen",
                "level": "high",
                "confidence_pct": 95,
                "confidence_text": "95% confident — strong match",
                "why": "yellowing on your older leaves, sandy soil",
            }
        ],
        "looking_fine": [
            {
                "nutrient": "Phosphorus",
                "level": "low",
                "confidence_pct": 39,
                "confidence_text": "39% confident — based on limited signs",
            }
        ],
        "caveat": "This advice is based on your answers and soil-meter readings.",
        "soil_condition_note": "Soil is strongly acidic.",
    },
    "model_version": "module2-orchestrator-v1",
    "module2a_model_version": "module2a-v5",
}


@override_settings(ENABLE_MOCK_AI=True)
class CallModule2OrchestratorMockModeTests(SimpleTestCase):
    def test_returns_fixed_mock_response_matching_documented_shape(self):
        result = call_module2_orchestrator({"crop": "wheat"})

        self.assertTrue(result["crop_supported"])
        self.assertEqual(result["model_version"], "module2-orchestrator-mock")
        self.assertEqual(result["module2a_model_version"], "module2a-v5-mock")
        for field in (
            "nitrogen_risk",
            "phosphorus_risk",
            "potassium_risk",
            "magnesium_risk",
            "zinc_risk",
            "boron_risk",
        ):
            self.assertIn(field, result["module2a"])
        self.assertIn("input_typicality", result["module2a"])
        for field in ("ph", "soil_moisture", "light"):
            self.assertIn(field, result["module2b"])
        self.assertIn(result["overall_soil_health_label"], ("good", "moderate", "poor"))
        self.assertIn("headline", result["recommendation_notes"])

    def test_mock_response_is_never_mistaken_for_real_inference(self):
        result = call_module2_orchestrator({"crop": "wheat"})
        self.assertNotEqual(result["model_version"], "module2-orchestrator-v1")
        self.assertNotEqual(result["module2a_model_version"], "module2a-v5")

    def test_does_not_call_requests_when_mocked(self):
        with patch("ai_services.module2_client.requests.post") as mock_post:
            call_module2_orchestrator({"crop": "wheat"})
        mock_post.assert_not_called()


@override_settings(
    ENABLE_MOCK_AI=False,
    STRESS_MODULE_URL="https://stress.example.test",
    STRESS_MODULE_REQUEST_TIMEOUT_SECONDS=5,
)
class CallModule2OrchestratorRealModeTests(SimpleTestCase):
    """Exercises call_module2_orchestrator against the Stress Module's real,
    documented contract (ai/Stress_Module/docs/INTEGRATION_GUIDE.md): a single
    POST to /predict, non-422/503/500 errors using {"message": ...}, 422
    validation errors using FastAPI's default {"detail": [...]}."""

    def _mock_response(self, status_code=200, json_value=None, text=""):
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_response.text = text
        if json_value is not None:
            mock_response.json.return_value = json_value
        return mock_response

    @patch("ai_services.module2_client.requests.post")
    def test_returns_parsed_json_on_success(self, mock_post):
        mock_post.return_value = self._mock_response(200, _MODULE2_SUCCESS)

        result = call_module2_orchestrator({"crop": "wheat"})

        self.assertEqual(result, _MODULE2_SUCCESS)
        mock_post.assert_called_once()
        called_url = mock_post.call_args[0][0]
        self.assertEqual(called_url, "https://stress.example.test/predict")

    @patch("ai_services.module2_client.requests.post")
    def test_raises_service_error_on_connection_failure(self, mock_post):
        mock_post.side_effect = requests.ConnectionError("boom")

        with self.assertRaises(Module2ServiceError):
            call_module2_orchestrator({"crop": "wheat"})

    @patch("ai_services.module2_client.requests.post")
    def test_raises_service_error_on_timeout(self, mock_post):
        mock_post.side_effect = requests.Timeout("timed out")

        with self.assertRaises(Module2ServiceError):
            call_module2_orchestrator({"crop": "wheat"})

    @patch("ai_services.module2_client.requests.post")
    def test_raises_service_error_on_422_validation_error(self, mock_post):
        # The module's documented 422 body: FastAPI's default {"detail": [...]}.
        mock_post.return_value = self._mock_response(
            422, text='{"detail": [{"type": "missing", "loc": ["ph_value"], "msg": "Field required"}]}'
        )

        with self.assertRaises(Module2ServiceError):
            call_module2_orchestrator({"crop": "wheat"})

    @patch("ai_services.module2_client.requests.post")
    def test_raises_service_error_on_503_model_unavailable(self, mock_post):
        # The module's documented 503 body (v1.1.0+): {"message": "..."}.
        mock_post.return_value = self._mock_response(
            503, text='{"message": "Prediction Failed: model artifacts unavailable."}'
        )

        with self.assertRaises(Module2ServiceError):
            call_module2_orchestrator({"crop": "wheat"})

    @patch("ai_services.module2_client.requests.post")
    def test_raises_service_error_on_500_internal_failure(self, mock_post):
        mock_post.return_value = self._mock_response(500, text='{"message": "Prediction Failed"}')

        with self.assertRaises(Module2ServiceError):
            call_module2_orchestrator({"crop": "wheat"})

    @patch("ai_services.module2_client.requests.post")
    def test_raises_service_error_on_malformed_response_missing_required_keys(self, mock_post):
        mock_post.return_value = self._mock_response(200, {"unexpected": "shape"})

        with self.assertRaises(Module2ServiceError):
            call_module2_orchestrator({"crop": "wheat"})

    @patch("ai_services.module2_client.requests.post")
    def test_raises_service_error_when_supported_crop_missing_version_fields(self, mock_post):
        incomplete = dict(_MODULE2_SUCCESS)
        del incomplete["model_version"]
        mock_post.return_value = self._mock_response(200, incomplete)

        with self.assertRaises(Module2ServiceError):
            call_module2_orchestrator({"crop": "wheat"})

    @patch("ai_services.module2_client.requests.post")
    def test_raises_service_error_on_non_json_response(self, mock_post):
        mock_response = self._mock_response(200)
        mock_response.json.side_effect = ValueError("not json")
        mock_post.return_value = mock_response

        with self.assertRaises(Module2ServiceError):
            call_module2_orchestrator({"crop": "wheat"})

    @patch("ai_services.module2_client.requests.get")
    def test_health_check_true_on_200(self, mock_get):
        mock_get.return_value = Mock(status_code=200)
        self.assertTrue(check_stress_module_health())

    @patch("ai_services.module2_client.requests.get")
    def test_health_check_false_on_non_200(self, mock_get):
        mock_get.return_value = Mock(status_code=503)
        self.assertFalse(check_stress_module_health())

    @patch("ai_services.module2_client.requests.get")
    def test_health_check_false_on_connection_error(self, mock_get):
        mock_get.side_effect = requests.ConnectionError("refused")
        self.assertFalse(check_stress_module_health())


@override_settings(ENABLE_MOCK_AI=True)
class CheckStressModuleHealthMockModeTests(SimpleTestCase):
    def test_mock_mode_health_check_reports_not_connected(self):
        # Mock Mode must never claim a live connection to the real module.
        self.assertFalse(check_stress_module_health())
