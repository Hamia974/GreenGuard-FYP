import io
import uuid
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from ai_services.disease_module_client import DiseaseModuleServiceError
from farms.models import Farm
from module2.models import Module2Analysis
from notifications.models import Notification
from predictions.models import Prediction
from predictions.serializers import (
    PredictionAnalyzeRequestSerializer,
    PredictionAnalyzeResponseSerializer,
    PredictionSerializer,
)
from predictions.storage import generate_prediction_image_filename
from predictions.validators import (
    validate_image_content_type,
    validate_image_format,
    validate_image_resolution,
    validate_image_size,
    validate_plant_image,
)
from weather.services import WeatherServiceError

User = get_user_model()

# Live Module 1 (Disease Detection) contract, per ai/API_CONTRACT.md.
MOCK_MODULE1_RESULT = {
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
    "request_id": "abc123def456",
}

# Module 1 abstaining: prediction is null, top3 still populated.
MOCK_MODULE1_UNCERTAIN_RESULT = {
    **MOCK_MODULE1_RESULT,
    "status": "uncertain",
    "prediction": None,
    "crop_source": "model",
    "warnings": ["BLURRY_IMAGE"],
    "message": "We could not confidently identify a disease from this photo.",
}

MOCK_WEATHER_RESULT = {
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

MOCK_REPORT = {
    "module1": MOCK_MODULE1_RESULT,
    "module2": None,
    "module3": MOCK_WEATHER_RESULT,
}


def make_image_file(name="leaf.jpg", size=(300, 300), fmt="JPEG", extra_bytes=0):
    buffer = io.BytesIO()
    Image.new("RGB", size, color=(34, 139, 34)).save(buffer, format=fmt)
    content = buffer.getvalue() + (b"\0" * extra_bytes)
    return SimpleUploadedFile(name, content, content_type="image/jpeg")


class ValidateImageFormatTests(TestCase):
    def test_accepts_jpg_jpeg_png(self):
        for name in ("leaf.jpg", "leaf.jpeg", "leaf.PNG"):
            validate_image_format(SimpleUploadedFile(name, b"data"))

    def test_rejects_unsupported_extension(self):
        with self.assertRaises(ValidationError):
            validate_image_format(SimpleUploadedFile("leaf.webp", b"data"))

    def test_rejects_missing_extension(self):
        with self.assertRaises(ValidationError):
            validate_image_format(SimpleUploadedFile("leaf", b"data"))


class ValidateImageContentTypeTests(TestCase):
    def test_accepts_jpeg_and_png_content_types(self):
        for content_type in ("image/jpeg", "image/png"):
            validate_image_content_type(
                SimpleUploadedFile("leaf.jpg", b"data", content_type=content_type)
            )

    def test_rejects_disallowed_content_type(self):
        with self.assertRaises(ValidationError):
            validate_image_content_type(
                SimpleUploadedFile("leaf.jpg", b"data", content_type="application/octet-stream")
            )

    def test_missing_content_type_is_not_rejected_here(self):
        # SimpleUploadedFile defaults content_type to "text/plain" -- real
        # multipart uploads always set one, so this only matters for
        # non-browser test fixtures. Resolution validation (Pillow decode)
        # still rejects non-images regardless.
        validate_image_content_type(SimpleUploadedFile("leaf.jpg", b"data", content_type=None))


class ValidateImageSizeTests(TestCase):
    def test_accepts_file_under_limit(self):
        validate_image_size(make_image_file())

    def test_rejects_file_over_10mb(self):
        oversized = make_image_file(extra_bytes=10 * 1024 * 1024 + 1)
        with self.assertRaises(ValidationError):
            validate_image_size(oversized)


class ValidateImageResolutionTests(TestCase):
    def test_accepts_image_at_minimum_resolution(self):
        validate_image_resolution(make_image_file(size=(224, 224)))

    def test_rejects_image_below_minimum_resolution(self):
        with self.assertRaises(ValidationError):
            validate_image_resolution(make_image_file(size=(100, 100)))

    def test_rejects_corrupted_file(self):
        corrupted = SimpleUploadedFile("leaf.jpg", b"not-a-real-image", content_type="image/jpeg")
        with self.assertRaises(ValidationError):
            validate_image_resolution(corrupted)


class ValidatePlantImageTests(TestCase):
    def test_valid_image_passes_all_checks(self):
        validate_plant_image(make_image_file(size=(300, 300)))

    def test_stops_at_first_failing_check(self):
        with self.assertRaises(ValidationError):
            validate_plant_image(SimpleUploadedFile("leaf.gif", b"data"))


class GeneratePredictionImageFilenameTests(TestCase):
    def test_generates_unique_names_for_same_source_filename(self):
        first = generate_prediction_image_filename(None, "leaf.jpg")
        second = generate_prediction_image_filename(None, "leaf.jpg")

        self.assertNotEqual(first, second)
        self.assertTrue(first.startswith("uploads/leaf_"))
        self.assertTrue(first.endswith(".jpg"))

    def test_preserves_extension_case_insensitively(self):
        name = generate_prediction_image_filename(None, "leaf.PNG")
        self.assertTrue(name.endswith(".png"))


class PredictionModelTests(TestCase):
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

    def test_create_prediction_with_required_fields(self):
        prediction = Prediction.objects.create(
            user=self.user,
            farm=self.farm,
            uploaded_image=make_image_file(),
            final_diagnosis="Powdery Mildew",
            confidence_score=0.94,
            prediction_report={"disease": {"label": "Powdery Mildew", "confidence": 0.94}},
            recommendation_summary="Apply a recommended fungicide.",
        )

        self.assertEqual(prediction.prediction_status, Prediction.Status.COMPLETED)
        self.assertEqual(prediction.user, self.user)
        self.assertEqual(prediction.farm, self.farm)
        self.assertIsNotNone(prediction.created_at)

    def test_predictions_ordered_newest_first(self):
        older = Prediction.objects.create(
            user=self.user,
            farm=self.farm,
            uploaded_image=make_image_file(),
            final_diagnosis="Healthy",
            confidence_score=0.80,
            prediction_report={},
            recommendation_summary="No action needed.",
        )
        newer = Prediction.objects.create(
            user=self.user,
            farm=self.farm,
            uploaded_image=make_image_file(),
            final_diagnosis="Nitrogen Deficiency",
            confidence_score=0.88,
            prediction_report={},
            recommendation_summary="Apply nitrogen-rich fertilizer.",
        )

        self.assertEqual(list(Prediction.objects.all()), [newer, older])

    def test_deleting_user_cascades_to_predictions(self):
        Prediction.objects.create(
            user=self.user,
            farm=self.farm,
            uploaded_image=make_image_file(),
            final_diagnosis="Healthy",
            confidence_score=0.80,
            prediction_report={},
            recommendation_summary="No action needed.",
        )

        self.user.delete()

        self.assertEqual(Prediction.objects.count(), 0)

    def test_deleting_farm_cascades_to_predictions(self):
        Prediction.objects.create(
            user=self.user,
            farm=self.farm,
            uploaded_image=make_image_file(),
            final_diagnosis="Healthy",
            confidence_score=0.80,
            prediction_report={},
            recommendation_summary="No action needed.",
        )

        self.farm.delete()

        self.assertEqual(Prediction.objects.count(), 0)

    def test_legacy_fusion_fields_are_optional(self):
        prediction = Prediction.objects.create(
            user=self.user,
            farm=self.farm,
            uploaded_image=make_image_file(),
            prediction_report=MOCK_REPORT,
        )

        self.assertIsNone(prediction.final_diagnosis)
        self.assertIsNone(prediction.confidence_score)
        self.assertIsNone(prediction.recommendation_summary)

    def test_disease_result_reads_module1_prediction_verbatim(self):
        prediction = Prediction(prediction_report=MOCK_REPORT)

        self.assertEqual(prediction.disease_result_name, "Yellow Rust")
        self.assertEqual(prediction.disease_result_confidence, 0.8812)

    def test_disease_result_is_none_when_module1_uncertain(self):
        prediction = Prediction(
            prediction_report={**MOCK_REPORT, "module1": MOCK_MODULE1_UNCERTAIN_RESULT}
        )

        self.assertIsNone(prediction.disease_result_name)
        self.assertIsNone(prediction.disease_result_confidence)

    def test_disease_result_is_none_for_legacy_module1_contract(self):
        prediction = Prediction(
            prediction_report={"module1": {"disease": {"label": "Powdery Mildew"}}}
        )

        self.assertIsNone(prediction.disease_result_name)


class PredictionModule2AnalysisRelationshipTests(TestCase):
    """module2_analysis is nullable, per DATABASE_SPECIFICATION.md section 6A."""

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

    def test_prediction_without_module2_analysis_remains_valid(self):
        prediction = Prediction.objects.create(
            user=self.user,
            farm=self.farm,
            uploaded_image=make_image_file(),
            final_diagnosis="Healthy",
            confidence_score=0.80,
            prediction_report={},
            recommendation_summary="No action needed.",
        )

        self.assertIsNone(prediction.module2_analysis)

    def test_prediction_can_reference_a_module2_analysis_snapshot(self):
        analysis = Module2Analysis.objects.create(
            farm=self.farm,
            crop_supported=True,
            request_payload={"crop": "wheat"},
            response_payload={"crop_supported": True},
        )
        prediction = Prediction.objects.create(
            user=self.user,
            farm=self.farm,
            module2_analysis=analysis,
            uploaded_image=make_image_file(),
            final_diagnosis="Healthy",
            confidence_score=0.80,
            prediction_report={},
            recommendation_summary="No action needed.",
        )

        self.assertEqual(prediction.module2_analysis, analysis)

    def test_deleting_module2_analysis_sets_prediction_field_null(self):
        analysis = Module2Analysis.objects.create(
            farm=self.farm,
            crop_supported=True,
            request_payload={"crop": "wheat"},
            response_payload={"crop_supported": True},
        )
        prediction = Prediction.objects.create(
            user=self.user,
            farm=self.farm,
            module2_analysis=analysis,
            uploaded_image=make_image_file(),
            final_diagnosis="Healthy",
            confidence_score=0.80,
            prediction_report={},
            recommendation_summary="No action needed.",
        )

        analysis.delete()
        prediction.refresh_from_db()

        self.assertEqual(Prediction.objects.count(), 1)
        self.assertIsNone(prediction.module2_analysis)


class PredictionAnalyzeRequestSerializerTests(TestCase):
    """PredictionAnalyzeRequestSerializer, per REST_API_SPEC.md's "Analyze
    Plant" / "Request Parameters" section. Only format-level validation is
    exercised here -- farm existence/ownership is a view-layer 404 concern
    (see module2.views._get_owned_farm's equivalent split), not tested here.
    """

    def test_valid_request_with_image_and_farm_id_is_valid(self):
        serializer = PredictionAnalyzeRequestSerializer(
            data={"image": make_image_file(), "farm_id": str(uuid.uuid4())}
        )

        self.assertTrue(serializer.is_valid())

    def test_missing_image_is_invalid(self):
        serializer = PredictionAnalyzeRequestSerializer(data={"farm_id": str(uuid.uuid4())})

        self.assertFalse(serializer.is_valid())
        self.assertIn("image", serializer.errors)

    def test_missing_farm_id_is_invalid(self):
        serializer = PredictionAnalyzeRequestSerializer(data={"image": make_image_file()})

        self.assertFalse(serializer.is_valid())
        self.assertIn("farm_id", serializer.errors)

    def test_invalid_image_format_is_invalid(self):
        unsupported = SimpleUploadedFile("leaf.gif", b"not-a-real-image", content_type="image/gif")

        serializer = PredictionAnalyzeRequestSerializer(
            data={"image": unsupported, "farm_id": str(uuid.uuid4())}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("image", serializer.errors)

    def test_malformed_farm_id_is_invalid(self):
        serializer = PredictionAnalyzeRequestSerializer(
            data={"image": make_image_file(), "farm_id": "not-a-uuid"}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("farm_id", serializer.errors)

    def test_syntactically_valid_but_nonexistent_farm_id_passes_serializer_validation(self):
        """Existence/ownership is deliberately NOT this serializer's job --
        it returns a 404 at the view layer, a different status than the 422
        this serializer's own failures produce, matching module2's existing
        farm_id split (test_invalid_farm_id_format_returns_422 vs.
        test_nonexistent_farm_id_returns_404 in module2.tests).
        """
        serializer = PredictionAnalyzeRequestSerializer(
            data={"image": make_image_file(), "farm_id": str(uuid.uuid4())}
        )

        self.assertTrue(serializer.is_valid())

    def test_valid_serializer_produces_expected_validated_fields(self):
        farm_id = uuid.uuid4()
        serializer = PredictionAnalyzeRequestSerializer(
            data={"image": make_image_file(), "farm_id": str(farm_id)}
        )

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["farm_id"], farm_id)
        self.assertIsInstance(serializer.validated_data["farm_id"], uuid.UUID)
        self.assertIn("image", serializer.validated_data)

    def test_no_undocumented_fields_are_silently_introduced(self):
        serializer = PredictionAnalyzeRequestSerializer(
            data={
                "image": make_image_file(),
                "farm_id": str(uuid.uuid4()),
                "latitude": 31.5204,
                "longitude": 74.3587,
                "confidence": 0.99,
            }
        )

        self.assertTrue(serializer.is_valid())
        self.assertEqual(set(serializer.validated_data.keys()), {"image", "farm_id"})

    def test_optional_crop_is_normalized(self):
        serializer = PredictionAnalyzeRequestSerializer(
            data={"image": make_image_file(), "farm_id": str(uuid.uuid4()), "crop": " Wheat "}
        )

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["crop"], "wheat")

    def test_blank_crop_becomes_none(self):
        serializer = PredictionAnalyzeRequestSerializer(
            data={"image": make_image_file(), "farm_id": str(uuid.uuid4()), "crop": ""}
        )

        self.assertTrue(serializer.is_valid())
        self.assertIsNone(serializer.validated_data["crop"])


class PredictionAnalyzeResponseSerializerTests(TestCase):
    """PredictionAnalyzeResponseSerializer, per REST_API_SPEC.md's "Standard
    Success Response" envelope.
    """

    def test_response_envelope_has_success_message_and_data(self):
        serializer = PredictionAnalyzeResponseSerializer(
            data={
                "success": True,
                "message": "Prediction completed successfully.",
                "data": {"prediction_report": MOCK_REPORT},
            }
        )

        self.assertTrue(serializer.is_valid())
        self.assertEqual(
            set(serializer.validated_data.keys()), {"success", "message", "data"}
        )

    def test_data_holds_module_report_unchanged(self):
        serializer = PredictionAnalyzeResponseSerializer(
            data={
                "success": True,
                "message": "Prediction completed successfully.",
                "data": {"prediction_report": MOCK_REPORT},
            }
        )

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["data"]["prediction_report"], MOCK_REPORT)


class PredictionAnalyzeViewTests(APITestCase):
    """POST /api/v1/predictions/analyze/ (Quick Scan), per REST_API_SPEC.md's
    "Analyze Plant" section. Module 1 and Module 3 are mocked at their
    predictions.views import site -- no real network calls are made.
    Module 2 is deliberately never mocked as "called", because the view
    must never call it live at all (see test_module2_is_never_invoked_live).
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
        self.url = reverse("predictions-analyze")

        self.mock_module1 = patch(
            "predictions.views.call_disease_module_predict",
            return_value=dict(MOCK_MODULE1_RESULT),
        ).start()
        self.mock_weather = patch(
            "predictions.views.fetch_weather_for_coordinates",
            return_value=dict(MOCK_WEATHER_RESULT),
        ).start()
        self.addCleanup(patch.stopall)

    def _payload(self, **overrides):
        payload = {"image": make_image_file(), "farm_id": str(self.farm.id)}
        payload.update(overrides)
        return payload

    def _post(self, **overrides):
        return self.client.post(self.url, self._payload(**overrides), format="multipart")

    def _create_module2_analysis(self, *, crop_supported, response_payload, created_at=None):
        analysis = Module2Analysis.objects.create(
            farm=self.farm,
            crop_supported=crop_supported,
            request_payload={"crop": "wheat"},
            response_payload=response_payload,
        )
        if created_at is not None:
            Module2Analysis.objects.filter(pk=analysis.pk).update(created_at=created_at)
            analysis.refresh_from_db()
        return analysis

    # --- Authentication ---

    def test_requires_authentication(self):
        response = self._post()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- Successful path ---

    def test_successful_analysis_returns_saved_report(self):
        self.client.force_authenticate(user=self.user)

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Prediction completed successfully.")
        prediction = Prediction.objects.get()
        self.assertEqual(response.data["data"]["prediction_id"], str(prediction.id))
        self.assertEqual(response.data["data"]["prediction_report"], MOCK_REPORT)

    def test_response_envelope_matches_standard_contract(self):
        self.client.force_authenticate(user=self.user)

        response = self._post()

        self.assertEqual(set(response.data.keys()), {"success", "message", "data"})

    def test_report_contains_exactly_the_three_module_results(self):
        self.client.force_authenticate(user=self.user)

        self._post()

        prediction = Prediction.objects.get()
        self.assertEqual(
            set(prediction.prediction_report.keys()), {"module1", "module2", "module3"}
        )
        self.assertEqual(prediction.prediction_report["module1"], MOCK_MODULE1_RESULT)
        self.assertIsNone(prediction.prediction_report["module2"])
        self.assertEqual(prediction.prediction_report["module3"], MOCK_WEATHER_RESULT)

    def test_no_combined_diagnosis_confidence_or_recommendation_is_invented(self):
        self.client.force_authenticate(user=self.user)

        response = self._post()

        prediction = Prediction.objects.get()
        self.assertIsNone(prediction.final_diagnosis)
        self.assertIsNone(prediction.confidence_score)
        self.assertIsNone(prediction.recommendation_summary)
        self.assertNotIn("module4", prediction.prediction_report)
        self.assertIsNone(response.data["data"]["final_diagnosis"])
        self.assertIsNone(response.data["data"]["confidence_score"])

    def test_successful_analysis_creates_prediction_record(self):
        self.client.force_authenticate(user=self.user)

        self._post()

        self.assertEqual(Prediction.objects.count(), 1)
        prediction = Prediction.objects.get()
        self.assertEqual(prediction.user, self.user)
        self.assertEqual(prediction.farm, self.farm)
        self.assertIsNone(prediction.module2_analysis)
        self.assertEqual(prediction.prediction_status, Prediction.Status.COMPLETED)
        self.assertTrue(prediction.uploaded_image.name)

    def test_successful_analysis_creates_notification(self):
        self.client.force_authenticate(user=self.user)

        self._post()

        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)
        notification = Notification.objects.get(user=self.user)
        self.assertEqual(notification.title, "Prediction Completed")
        self.assertEqual(notification.message, "Your latest plant analysis is ready.")
        self.assertEqual(notification.notification_type, Notification.NotificationType.PREDICTION)
        self.assertFalse(notification.is_read)

    # --- Request validation ---

    def test_missing_image_returns_422(self):
        self.client.force_authenticate(user=self.user)
        payload = self._payload()
        del payload["image"]

        response = self.client.post(self.url, payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("image", response.data["errors"])
        self.assertEqual(Prediction.objects.count(), 0)

    def test_missing_farm_id_returns_422(self):
        self.client.force_authenticate(user=self.user)
        payload = self._payload()
        del payload["farm_id"]

        response = self.client.post(self.url, payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("farm_id", response.data["errors"])

    def test_validation_failure_does_not_call_any_ai_service(self):
        self.client.force_authenticate(user=self.user)
        payload = self._payload()
        del payload["image"]

        self.client.post(self.url, payload, format="multipart")

        self.mock_module1.assert_not_called()
        self.mock_weather.assert_not_called()

    # --- Farm resolution ---

    def test_nonexistent_farm_returns_404(self):
        self.client.force_authenticate(user=self.user)

        response = self._post(farm_id="8f14e45f-ceea-4c9a-b3f4-000000000099")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data["success"])
        self.assertEqual(Prediction.objects.count(), 0)

    def test_farm_belonging_to_another_user_returns_404(self):
        other_user = User.objects.create_user(
            email="other@example.com",
            password="StrongPass123!",
            first_name="Other",
            last_name="Farmer",
        )
        other_farm = Farm.objects.create(
            user=other_user,
            farm_name="Another Field",
            address="789 Farm Rd",
            latitude="31.1",
            longitude="74.1",
        )
        self.client.force_authenticate(user=self.user)

        response = self._post(farm_id=str(other_farm.id))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- Module 1 (Disease Detection) ---

    def test_module1_receives_crop_and_farm_id(self):
        self.client.force_authenticate(user=self.user)

        self._post(crop="Wheat")

        _, called_kwargs = self.mock_module1.call_args
        self.assertEqual(called_kwargs["crop"], "wheat")
        self.assertEqual(called_kwargs["farm_id"], str(self.farm.id))

    def test_module1_called_without_crop_when_none_chosen(self):
        self.client.force_authenticate(user=self.user)

        self._post()

        _, called_kwargs = self.mock_module1.call_args
        self.assertIsNone(called_kwargs["crop"])

    def test_uncertain_module1_result_is_stored_verbatim(self):
        self.mock_module1.return_value = dict(MOCK_MODULE1_UNCERTAIN_RESULT)
        self.client.force_authenticate(user=self.user)

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        prediction = Prediction.objects.get()
        module1 = prediction.prediction_report["module1"]
        self.assertEqual(module1, MOCK_MODULE1_UNCERTAIN_RESULT)
        self.assertIsNone(module1["prediction"])
        self.assertEqual(len(module1["top3"]), 3)
        self.assertIsNone(prediction.disease_result_name)

    def test_module1_unavailable_returns_friendly_error(self):
        self.client.force_authenticate(user=self.user)
        self.mock_module1.side_effect = DiseaseModuleServiceError("unavailable")

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertFalse(response.data["success"])
        self.assertEqual(Prediction.objects.count(), 0)

    def test_module1_documented_error_code_is_mapped(self):
        self.client.force_authenticate(user=self.user)
        self.mock_module1.side_effect = DiseaseModuleServiceError(
            "error",
            http_status=503,
            error_code="MODEL_NOT_READY",
            upstream_message="Model loading",
        )

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertNotIn("Model loading", response.data["message"])

    def test_module1_failure_does_not_call_weather(self):
        self.client.force_authenticate(user=self.user)
        self.mock_module1.side_effect = DiseaseModuleServiceError("unavailable")

        self._post()

        self.mock_weather.assert_not_called()

    def test_module1_is_called_exactly_once(self):
        self.client.force_authenticate(user=self.user)

        self._post()

        self.mock_module1.assert_called_once()

    # --- Module 3 / Weather ---

    def test_weather_failure_returns_503(self):
        self.client.force_authenticate(user=self.user)
        self.mock_weather.side_effect = WeatherServiceError("unavailable")

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertFalse(response.data["success"])
        self.assertEqual(Prediction.objects.count(), 0)

    # --- Module 2 (persisted snapshot only, never invoked live) ---

    def test_module2_is_never_invoked_live(self):
        self.client.force_authenticate(user=self.user)

        with patch("ai_services.module2_client.call_module2_orchestrator") as mock_module2:
            self._post()

        mock_module2.assert_not_called()

    def test_supported_module2_payload_passes_through_unchanged(self):
        supported_payload = {
            "crop_supported": True,
            "module2a": {"nitrogen_risk": {"level": "high", "confidence": 0.82}},
            "module2b": {"ph": {"current": 5.1, "status": "critical"}},
            "overall_soil_health_score": 52.5,
            "overall_soil_health_label": "moderate",
            "model_version": "module2-orchestrator-v1",
        }
        self._create_module2_analysis(crop_supported=True, response_payload=supported_payload)
        self.client.force_authenticate(user=self.user)

        self._post()

        prediction = Prediction.objects.get()
        self.assertEqual(prediction.prediction_report["module2"], supported_payload)
        self.assertEqual(prediction.module2_analysis.response_payload, supported_payload)

    def test_unsupported_crop_module2_payload_passes_through_unchanged(self):
        unsupported_payload = {
            "crop_supported": False,
            "message": "Nutrient and soil-condition analysis is not available yet for this crop.",
            "module2a": None,
            "module2b": None,
            "overall_soil_health_score": None,
            "overall_soil_health_label": None,
        }
        self._create_module2_analysis(crop_supported=False, response_payload=unsupported_payload)
        self.client.force_authenticate(user=self.user)

        self._post()

        prediction = Prediction.objects.get()
        self.assertEqual(prediction.prediction_report["module2"], unsupported_payload)

    def test_latest_module2_analysis_is_used(self):
        older_payload = {"crop_supported": True, "overall_soil_health_label": "poor"}
        newer_payload = {"crop_supported": True, "overall_soil_health_label": "good"}
        self._create_module2_analysis(
            crop_supported=True,
            response_payload=older_payload,
            created_at=timezone.now() - timedelta(days=1),
        )
        newer = self._create_module2_analysis(crop_supported=True, response_payload=newer_payload)
        self.client.force_authenticate(user=self.user)

        self._post()

        prediction = Prediction.objects.get()
        self.assertEqual(prediction.prediction_report["module2"], newer_payload)
        self.assertEqual(prediction.module2_analysis, newer)


class PredictionSerializerTests(TestCase):
    """PredictionSerializer, used by both the list and detail endpoints."""

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
        self.prediction = Prediction.objects.create(
            user=self.user,
            farm=self.farm,
            uploaded_image=make_image_file(),
            prediction_report=MOCK_REPORT,
        )

    def test_serializes_expected_fields(self):
        data = PredictionSerializer(self.prediction).data

        self.assertEqual(
            set(data.keys()),
            {
                "prediction_id",
                "farm_id",
                "uploaded_image",
                "final_diagnosis",
                "confidence_score",
                "prediction_report",
                "recommendation_summary",
                "prediction_status",
                "created_at",
                "updated_at",
            },
        )
        self.assertEqual(data["prediction_id"], str(self.prediction.id))
        self.assertEqual(data["farm_id"], str(self.farm.id))
        self.assertEqual(data["prediction_report"], self.prediction.prediction_report)

    def test_uploaded_image_is_absolute_url_with_request_context(self):
        factory = APIRequestFactory()
        request = factory.get("/")

        data = PredictionSerializer(self.prediction, context={"request": request}).data

        self.assertTrue(data["uploaded_image"].startswith("http://testserver/"))


class PredictionListViewTests(APITestCase):
    """GET /api/v1/predictions/ per REST_API_SPEC.md section 3."""

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
        self.farm = Farm.objects.create(
            user=self.user,
            farm_name="North Field",
            address="123 Farm Rd",
            latitude="31.5204",
            longitude="74.3587",
        )
        self.url = reverse("predictions-list")

    def _make_prediction(self, *, user, farm, created_at=None):
        prediction = Prediction.objects.create(
            user=user,
            farm=farm,
            uploaded_image=make_image_file(),
            prediction_report=MOCK_REPORT,
        )
        if created_at is not None:
            Prediction.objects.filter(pk=prediction.pk).update(created_at=created_at)
            prediction.refresh_from_db()
        return prediction

    def test_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_empty_list_when_no_predictions(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"], [])

    def test_returns_only_the_authenticated_users_predictions(self):
        other_farm = Farm.objects.create(
            user=self.other_user,
            farm_name="Other Field",
            address="456 Farm Rd",
            latitude="30.0",
            longitude="70.0",
        )
        mine = self._make_prediction(user=self.user, farm=self.farm)
        self._make_prediction(user=self.other_user, farm=other_farm)
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["prediction_id"], str(mine.id))

    def test_returns_predictions_newest_first(self):
        older = self._make_prediction(
            user=self.user, farm=self.farm, created_at=timezone.now() - timedelta(days=1)
        )
        newer = self._make_prediction(user=self.user, farm=self.farm)
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        ids = [item["prediction_id"] for item in response.data["data"]]
        self.assertEqual(ids, [str(newer.id), str(older.id)])


class PredictionDetailViewTests(APITestCase):
    """GET/DELETE /api/v1/predictions/{prediction_id}/ per
    REST_API_SPEC.md section 3.
    """

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
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="StrongPass123!",
            first_name="Admin",
            last_name="User",
            role=User.Role.ADMIN,
        )
        self.farm = Farm.objects.create(
            user=self.user,
            farm_name="North Field",
            address="123 Farm Rd",
            latitude="31.5204",
            longitude="74.3587",
        )
        self.prediction = Prediction.objects.create(
            user=self.user,
            farm=self.farm,
            uploaded_image=make_image_file(),
            prediction_report=MOCK_REPORT,
        )
        self.url = reverse("predictions-detail", args=[self.prediction.id])

    # --- GET ---

    def test_get_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_returns_complete_prediction_report(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(
            response.data["data"]["prediction_id"], str(self.prediction.id)
        )
        self.assertEqual(
            response.data["data"]["prediction_report"],
            self.prediction.prediction_report,
        )

    def test_get_nonexistent_prediction_returns_404(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse("predictions-detail", args=[uuid.uuid4()])
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_another_users_prediction_returns_404(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_malformed_prediction_id_returns_404(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/v1/predictions/not-a-uuid/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- DELETE ---

    def test_delete_requires_authentication(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_owner_can_delete_own_prediction(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertFalse(Prediction.objects.filter(id=self.prediction.id).exists())

    def test_non_owner_cannot_delete_prediction(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Prediction.objects.filter(id=self.prediction.id).exists())

    def test_admin_can_delete_any_prediction(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Prediction.objects.filter(id=self.prediction.id).exists())

    def test_delete_nonexistent_prediction_returns_404(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(
            reverse("predictions-detail", args=[uuid.uuid4()])
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
