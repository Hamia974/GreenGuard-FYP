import io
from unittest.mock import Mock, patch

import requests
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from ai_services.disease_module_client import (
    DiseaseModuleServiceError,
    call_disease_module_predict,
    check_disease_module_health,
)
from farms.models import Farm
from module1.models import DiseaseCheck

User = get_user_model()


def make_image_file(name="leaf.jpg", size=(300, 300), fmt="JPEG"):
    buffer = io.BytesIO()
    Image.new("RGB", size, color=(34, 139, 34)).save(buffer, format=fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


# The live Disease Module's documented "confident" example, per
# ai/API_CONTRACT.md.
CONFIDENT_RESPONSE = {
    "status": "ok",
    "farm_id": "farm_001",
    "timestamp": "2026-09-26T04:55:12Z",
    "prediction": {
        "class_id": "wheat_yellow_rust",
        "crop": "wheat",
        "disease": "yellow_rust",
        "display_name": "Yellow Rust",
        "is_healthy": False,
        "confidence": 0.8812,
    },
    "top3": [
        {
            "class_id": "wheat_yellow_rust",
            "crop": "wheat",
            "disease": "yellow_rust",
            "display_name": "Yellow Rust",
            "is_healthy": False,
            "confidence": 0.8812,
        },
        {
            "class_id": "wheat_brown_rust",
            "crop": "wheat",
            "disease": "brown_rust",
            "display_name": "Brown Rust",
            "is_healthy": False,
            "confidence": 0.0713,
        },
        {
            "class_id": "wheat_septoria",
            "crop": "wheat",
            "disease": "septoria",
            "display_name": "Septoria",
            "is_healthy": False,
            "confidence": 0.0208,
        },
    ],
    "crop_source": "user",
    "detected_crop": "wheat",
    "warnings": [],
    "message": None,
    "model_version": "efficientnet_b0-1.0",
    "inference_ms": 14.2,
    "request_id": "3f9a1c2b7d4e",
}

# The live Disease Module's documented "uncertain" example.
UNCERTAIN_RESPONSE = {
    "status": "uncertain",
    "prediction": None,
    "top3": [
        {
            "class_id": "wheat_yellow_rust",
            "crop": "wheat",
            "disease": "yellow_rust",
            "display_name": "Yellow Rust",
            "is_healthy": False,
            "confidence": 0.3821,
        },
        {
            "class_id": "wheat_brown_rust",
            "crop": "wheat",
            "disease": "brown_rust",
            "display_name": "Brown Rust",
            "is_healthy": False,
            "confidence": 0.2944,
        },
        {
            "class_id": "wheat_healthy",
            "crop": "wheat",
            "disease": "healthy",
            "display_name": "Healthy",
            "is_healthy": True,
            "confidence": 0.2015,
        },
    ],
    "warnings": ["BLURRY_IMAGE"],
    "message": (
        "Image unclear. Please retake the photo in good light, close to one leaf. "
        "The photo looks blurry — hold the phone steady and tap to focus on the leaf."
    ),
    "crop_source": "model",
    "detected_crop": "wheat",
    "farm_id": "farm_001",
    "timestamp": "2026-09-26T04:55:13Z",
    "model_version": "efficientnet_b0-1.0",
    "inference_ms": 15.9,
    "request_id": "7c1e4a90b3d2",
}


# ---------------------------------------------------------------------------
# ai_services.disease_module_client
# ---------------------------------------------------------------------------


@override_settings(ENABLE_MOCK_AI=True)
class CallDiseaseModulePredictMockModeTests(SimpleTestCase):
    def test_returns_fixed_mock_response_matching_documented_shape(self):
        result = call_disease_module_predict(make_image_file())

        self.assertEqual(result["status"], "ok")
        self.assertIsNotNone(result["prediction"])
        self.assertEqual(len(result["top3"]), 3)

    def test_mock_response_uses_mock_specific_model_version(self):
        result = call_disease_module_predict(make_image_file())
        self.assertNotEqual(result["model_version"], "efficientnet_b0-1.0")
        self.assertTrue(result["model_version"].endswith("-mock"))

    def test_mock_echoes_farm_id_given(self):
        result = call_disease_module_predict(make_image_file(), farm_id="farm-123")
        self.assertEqual(result["farm_id"], "farm-123")

    def test_mock_farm_id_is_none_when_not_given(self):
        result = call_disease_module_predict(make_image_file())
        self.assertIsNone(result["farm_id"])

    def test_does_not_call_requests_when_mocked(self):
        with patch("ai_services.disease_module_client.requests.post") as mock_post:
            call_disease_module_predict(make_image_file())
        mock_post.assert_not_called()


@override_settings(
    ENABLE_MOCK_AI=False,
    DISEASE_MODULE_URL="https://disease.example.test",
    DISEASE_MODULE_REQUEST_TIMEOUT_SECONDS=5,
    GREENGUARD_API_KEY="test-secret-key",
)
class CallDiseaseModulePredictRealModeTests(SimpleTestCase):
    def _mock_response(self, status_code=200, json_value=None, text=""):
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_response.text = text
        if json_value is not None:
            mock_response.json.return_value = json_value
        else:
            mock_response.json.side_effect = ValueError("not json")
        return mock_response

    @patch("ai_services.disease_module_client.requests.post")
    def test_returns_confident_response_unchanged(self, mock_post):
        mock_post.return_value = self._mock_response(200, CONFIDENT_RESPONSE)

        result = call_disease_module_predict(make_image_file(), crop="wheat", farm_id="farm_001")

        self.assertEqual(result, CONFIDENT_RESPONSE)
        called_url = mock_post.call_args[0][0]
        self.assertEqual(called_url, "https://disease.example.test/v1/predict")

    @patch("ai_services.disease_module_client.requests.post")
    def test_returns_uncertain_response_unchanged_with_prediction_null(self, mock_post):
        mock_post.return_value = self._mock_response(200, UNCERTAIN_RESPONSE)

        result = call_disease_module_predict(make_image_file(), crop="wheat", farm_id="farm_001")

        self.assertEqual(result, UNCERTAIN_RESPONSE)
        self.assertIsNone(result["prediction"])
        self.assertEqual(len(result["top3"]), 3)

    @patch("ai_services.disease_module_client.requests.post")
    def test_sends_x_api_key_header(self, mock_post):
        mock_post.return_value = self._mock_response(200, CONFIDENT_RESPONSE)

        call_disease_module_predict(make_image_file(), crop="wheat", farm_id="farm_001")

        _, called_kwargs = mock_post.call_args
        self.assertEqual(called_kwargs["headers"]["X-API-Key"], "test-secret-key")

    @patch("ai_services.disease_module_client.requests.post")
    def test_forwards_crop_and_farm_id_as_form_fields(self, mock_post):
        mock_post.return_value = self._mock_response(200, CONFIDENT_RESPONSE)

        call_disease_module_predict(make_image_file(), crop="wheat", farm_id="farm_001")

        _, called_kwargs = mock_post.call_args
        self.assertEqual(called_kwargs["data"]["crop"], "wheat")
        self.assertEqual(called_kwargs["data"]["farm_id"], "farm_001")

    @patch("ai_services.disease_module_client.requests.post")
    def test_omits_crop_when_not_given(self, mock_post):
        mock_post.return_value = self._mock_response(200, CONFIDENT_RESPONSE)

        call_disease_module_predict(make_image_file(), farm_id="farm_001")

        _, called_kwargs = mock_post.call_args
        self.assertNotIn("crop", called_kwargs["data"])

    @patch("ai_services.disease_module_client.requests.post")
    def test_forwards_image_bytes(self, mock_post):
        mock_post.return_value = self._mock_response(200, CONFIDENT_RESPONSE)
        image = make_image_file()
        image_bytes = image.read()
        image.seek(0)

        call_disease_module_predict(image, farm_id="farm_001")

        _, called_kwargs = mock_post.call_args
        sent_name, sent_bytes, _sent_content_type = called_kwargs["files"]["image"]
        self.assertEqual(sent_name, "leaf.jpg")
        self.assertEqual(sent_bytes, image_bytes)

    @patch("ai_services.disease_module_client.requests.post")
    def test_raises_service_error_on_connection_failure(self, mock_post):
        mock_post.side_effect = requests.ConnectionError("boom")

        with self.assertRaises(DiseaseModuleServiceError):
            call_disease_module_predict(make_image_file(), farm_id="farm_001")

    @patch("ai_services.disease_module_client.requests.post")
    def test_retries_once_on_timeout_then_succeeds(self, mock_post):
        mock_post.side_effect = [requests.Timeout("timed out"), self._mock_response(200, CONFIDENT_RESPONSE)]

        result = call_disease_module_predict(make_image_file(), farm_id="farm_001")

        self.assertEqual(result, CONFIDENT_RESPONSE)
        self.assertEqual(mock_post.call_count, 2)

    @patch("ai_services.disease_module_client.requests.post")
    def test_raises_service_error_after_timeout_on_retry_too(self, mock_post):
        mock_post.side_effect = [requests.Timeout("timed out"), requests.Timeout("timed out again")]

        with self.assertRaises(DiseaseModuleServiceError):
            call_disease_module_predict(make_image_file(), farm_id="farm_001")
        self.assertEqual(mock_post.call_count, 2)

    @patch("ai_services.disease_module_client.requests.post")
    def test_retries_once_on_503_then_succeeds(self, mock_post):
        mock_post.side_effect = [
            self._mock_response(
                503,
                text='{"status": "error", "error": {"code": "MODEL_NOT_READY", "message": "loading"}}',
                json_value={"status": "error", "error": {"code": "MODEL_NOT_READY", "message": "loading"}},
            ),
            self._mock_response(200, CONFIDENT_RESPONSE),
        ]

        result = call_disease_module_predict(make_image_file(), farm_id="farm_001")

        self.assertEqual(result, CONFIDENT_RESPONSE)
        self.assertEqual(mock_post.call_count, 2)

    @patch("ai_services.disease_module_client.requests.post")
    def test_does_not_retry_on_400(self, mock_post):
        mock_post.return_value = self._mock_response(
            400,
            json_value={"status": "error", "error": {"code": "INVALID_IMAGE", "message": "bad image"}},
        )

        with self.assertRaises(DiseaseModuleServiceError) as ctx:
            call_disease_module_predict(make_image_file(), farm_id="farm_001")

        self.assertEqual(mock_post.call_count, 1)
        self.assertEqual(ctx.exception.error_code, "INVALID_IMAGE")
        self.assertEqual(ctx.exception.http_status, 400)

    @patch("ai_services.disease_module_client.requests.post")
    def test_does_not_retry_on_401(self, mock_post):
        mock_post.return_value = self._mock_response(
            401,
            json_value={"status": "error", "error": {"code": "UNAUTHORIZED", "message": "bad key"}},
        )

        with self.assertRaises(DiseaseModuleServiceError) as ctx:
            call_disease_module_predict(make_image_file(), farm_id="farm_001")

        self.assertEqual(mock_post.call_count, 1)
        self.assertEqual(ctx.exception.error_code, "UNAUTHORIZED")

    @patch("ai_services.disease_module_client.requests.post")
    def test_does_not_retry_on_413(self, mock_post):
        mock_post.return_value = self._mock_response(
            413,
            json_value={"status": "error", "error": {"code": "FILE_TOO_LARGE", "message": "too big"}},
        )

        with self.assertRaises(DiseaseModuleServiceError) as ctx:
            call_disease_module_predict(make_image_file(), farm_id="farm_001")

        self.assertEqual(mock_post.call_count, 1)
        self.assertEqual(ctx.exception.error_code, "FILE_TOO_LARGE")

    @patch("ai_services.disease_module_client.requests.post")
    def test_does_not_retry_on_422(self, mock_post):
        mock_post.return_value = self._mock_response(
            422,
            json_value={
                "status": "error",
                "error": {"code": "INVALID_CROP", "message": "not a valid crop"},
            },
        )

        with self.assertRaises(DiseaseModuleServiceError) as ctx:
            call_disease_module_predict(make_image_file(), crop="banana", farm_id="farm_001")

        self.assertEqual(mock_post.call_count, 1)
        self.assertEqual(ctx.exception.error_code, "INVALID_CROP")
        self.assertEqual(ctx.exception.upstream_message, "not a valid crop")

    @patch("ai_services.disease_module_client.requests.post")
    def test_raises_service_error_on_malformed_response_missing_required_keys(self, mock_post):
        mock_post.return_value = self._mock_response(200, {"unexpected": "shape"})

        with self.assertRaises(DiseaseModuleServiceError):
            call_disease_module_predict(make_image_file(), farm_id="farm_001")

    @patch("ai_services.disease_module_client.requests.post")
    def test_raises_service_error_on_non_json_response(self, mock_post):
        mock_post.return_value = self._mock_response(200)

        with self.assertRaises(DiseaseModuleServiceError):
            call_disease_module_predict(make_image_file(), farm_id="farm_001")

    @patch("ai_services.disease_module_client.requests.get")
    def test_health_check_true_on_200(self, mock_get):
        mock_get.return_value = Mock(status_code=200)
        self.assertTrue(check_disease_module_health())

    @patch("ai_services.disease_module_client.requests.get")
    def test_health_check_false_on_non_200(self, mock_get):
        mock_get.return_value = Mock(status_code=503)
        self.assertFalse(check_disease_module_health())

    @patch("ai_services.disease_module_client.requests.get")
    def test_health_check_does_not_send_api_key(self, mock_get):
        mock_get.return_value = Mock(status_code=200)
        check_disease_module_health()
        _, called_kwargs = mock_get.call_args
        self.assertNotIn("headers", called_kwargs)


@override_settings(ENABLE_MOCK_AI=True)
class CheckDiseaseModuleHealthMockModeTests(SimpleTestCase):
    def test_mock_mode_health_check_reports_not_connected(self):
        self.assertFalse(check_disease_module_health())


# ---------------------------------------------------------------------------
# POST /api/v1/module1/analyze/
# ---------------------------------------------------------------------------


class DiseaseAnalyzeViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="farmer@example.com",
            password="StrongPassword123",
            first_name="Test",
            last_name="Farmer",
        )
        self.farm = Farm.objects.create(
            user=self.user,
            farm_name="Green Valley Farm",
            address="123 Farm Road, Lahore",
            latitude=31.5204,
            longitude=74.3587,
        )
        self.url = reverse("module1-analyze")

    def _post(self, **overrides):
        payload = {"image": make_image_file(), "farm_id": str(self.farm.id)}
        payload.update(overrides)
        return self.client.post(self.url, payload, format="multipart")

    def test_requires_authentication(self):
        response = self._post()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_requires_farm_id(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {"image": make_image_file()}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_farm_not_owned_by_user_returns_404(self):
        other_user = User.objects.create_user(
            email="other@example.com", password="StrongPassword123", first_name="O", last_name="U"
        )
        other_farm = Farm.objects.create(
            user=other_user, farm_name="Other Farm", address="x", latitude=1, longitude=1
        )
        self.client.force_authenticate(user=self.user)

        response = self._post(farm_id=str(other_farm.id))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("module1.views.call_disease_module_predict")
    def test_confident_prediction_returns_data_and_persists_check(self, mock_call):
        mock_call.return_value = CONFIDENT_RESPONSE
        self.client.force_authenticate(user=self.user)

        response = self._post(crop="wheat")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"], CONFIDENT_RESPONSE)
        self.assertEqual(DiseaseCheck.objects.count(), 1)
        check = DiseaseCheck.objects.get()
        self.assertEqual(check.farm_id, self.farm.id)
        self.assertEqual(check.crop_requested, "wheat")
        self.assertEqual(check.status_result, "ok")
        self.assertEqual(check.response_payload, CONFIDENT_RESPONSE)

    @patch("module1.views.call_disease_module_predict")
    def test_top3_present_when_confident(self, mock_call):
        mock_call.return_value = CONFIDENT_RESPONSE
        self.client.force_authenticate(user=self.user)

        response = self._post(crop="wheat")

        self.assertEqual(len(response.data["data"]["top3"]), 3)
        self.assertIsNotNone(response.data["data"]["prediction"])

    @patch("module1.views.call_disease_module_predict")
    def test_uncertain_prediction_returns_null_prediction_and_all_top3(self, mock_call):
        mock_call.return_value = UNCERTAIN_RESPONSE
        self.client.force_authenticate(user=self.user)

        response = self._post(crop="wheat")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["data"]["prediction"])
        self.assertEqual(len(response.data["data"]["top3"]), 3)
        self.assertEqual(response.data["data"]["message"], UNCERTAIN_RESPONSE["message"])
        self.assertEqual(response.data["data"]["warnings"], ["BLURRY_IMAGE"])
        self.assertEqual(DiseaseCheck.objects.get().status_result, "uncertain")

    @patch("module1.views.call_disease_module_predict")
    def test_healthy_top3_result_is_forwarded_unchanged(self, mock_call):
        mock_call.return_value = UNCERTAIN_RESPONSE
        self.client.force_authenticate(user=self.user)

        response = self._post(crop="wheat")

        healthy_entries = [item for item in response.data["data"]["top3"] if item["is_healthy"]]
        self.assertEqual(len(healthy_entries), 1)
        self.assertEqual(healthy_entries[0]["display_name"], "Healthy")

    @patch("module1.views.call_disease_module_predict")
    def test_unhealthy_top3_result_is_forwarded_unchanged(self, mock_call):
        mock_call.return_value = CONFIDENT_RESPONSE
        self.client.force_authenticate(user=self.user)

        response = self._post(crop="wheat")

        unhealthy_entries = [item for item in response.data["data"]["top3"] if not item["is_healthy"]]
        self.assertEqual(len(unhealthy_entries), 3)

    @patch("module1.views.call_disease_module_predict")
    def test_confidence_is_forwarded_as_raw_decimal_not_recalculated(self, mock_call):
        mock_call.return_value = CONFIDENT_RESPONSE
        self.client.force_authenticate(user=self.user)

        response = self._post(crop="wheat")

        self.assertEqual(response.data["data"]["prediction"]["confidence"], 0.8812)

    @patch("module1.views.call_disease_module_predict")
    def test_crop_is_forwarded_to_client(self, mock_call):
        mock_call.return_value = CONFIDENT_RESPONSE
        self.client.force_authenticate(user=self.user)

        self._post(crop="Wheat")

        _, called_kwargs = mock_call.call_args
        self.assertEqual(called_kwargs["crop"], "wheat")

    @patch("module1.views.call_disease_module_predict")
    def test_farm_id_is_forwarded_to_client(self, mock_call):
        mock_call.return_value = CONFIDENT_RESPONSE
        self.client.force_authenticate(user=self.user)

        self._post(crop="wheat")

        _, called_kwargs = mock_call.call_args
        self.assertEqual(called_kwargs["farm_id"], str(self.farm.id))

    @patch("module1.views.call_disease_module_predict")
    def test_crop_is_optional(self, mock_call):
        mock_call.return_value = CONFIDENT_RESPONSE
        self.client.force_authenticate(user=self.user)

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        _, called_kwargs = mock_call.call_args
        self.assertIsNone(called_kwargs["crop"])

    @patch("module1.views.call_disease_module_predict")
    def test_invalid_crop_returns_422_with_upstream_message(self, mock_call):
        mock_call.side_effect = DiseaseModuleServiceError(
            "Disease Module returned an error.",
            http_status=422,
            error_code="INVALID_CROP",
            upstream_message="'banana' is not a valid crop. Valid crops: wheat, rice, cotton, maize, sugarcane, tomato, potato.",
        )
        self.client.force_authenticate(user=self.user)

        response = self._post(crop="banana")

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("banana", response.data["message"])
        self.assertEqual(DiseaseCheck.objects.count(), 0)

    @patch("module1.views.call_disease_module_predict")
    def test_unauthorized_upstream_response_never_exposes_api_key_or_auth_detail(self, mock_call):
        mock_call.side_effect = DiseaseModuleServiceError(
            "Disease Module returned an error.",
            http_status=401,
            error_code="UNAUTHORIZED",
            upstream_message="Missing or invalid X-API-Key",
        )
        self.client.force_authenticate(user=self.user)

        response = self._post(crop="wheat")

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        body = str(response.data)
        self.assertNotIn("X-API-Key", body)
        self.assertNotIn("UNAUTHORIZED", body)

    @patch("module1.views.call_disease_module_predict")
    def test_model_not_ready_after_retry_returns_503(self, mock_call):
        mock_call.side_effect = DiseaseModuleServiceError(
            "Disease Module returned an error.", http_status=503, error_code="MODEL_NOT_READY"
        )
        self.client.force_authenticate(user=self.user)

        response = self._post(crop="wheat")

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @patch("module1.views.call_disease_module_predict")
    def test_internal_error_returns_500_prediction_failed(self, mock_call):
        mock_call.side_effect = DiseaseModuleServiceError(
            "Disease Module returned an error.", http_status=500, error_code="INTERNAL_ERROR"
        )
        self.client.force_authenticate(user=self.user)

        response = self._post(crop="wheat")

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data["message"], "Prediction Failed")

    @patch("module1.views.call_disease_module_predict")
    def test_failed_call_does_not_persist_a_disease_check(self, mock_call):
        mock_call.side_effect = DiseaseModuleServiceError(
            "Disease Module returned an error.", http_status=500, error_code="INTERNAL_ERROR"
        )
        self.client.force_authenticate(user=self.user)

        self._post(crop="wheat")

        self.assertEqual(DiseaseCheck.objects.count(), 0)

    @override_settings(GREENGUARD_API_KEY="super-secret-value")
    def test_response_never_contains_the_configured_api_key(self):
        with patch("module1.views.call_disease_module_predict") as mock_call:
            mock_call.return_value = CONFIDENT_RESPONSE
            self.client.force_authenticate(user=self.user)

            response = self._post(crop="wheat")

        self.assertNotIn("super-secret-value", str(response.data))


class DiseaseCheckModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="farmer@example.com",
            password="StrongPassword123",
            first_name="Test",
            last_name="Farmer",
        )
        self.farm = Farm.objects.create(
            user=self.user,
            farm_name="Green Valley Farm",
            address="123 Farm Road, Lahore",
            latitude=31.5204,
            longitude=74.3587,
        )

    def test_create_disease_check_with_required_fields(self):
        check = DiseaseCheck.objects.create(
            farm=self.farm,
            crop_requested="wheat",
            status_result="ok",
            response_payload=CONFIDENT_RESPONSE,
        )
        self.assertIsNotNone(check.id)
        self.assertEqual(check.response_payload["status"], "ok")
