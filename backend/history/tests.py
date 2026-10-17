import io
import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from django.core.files.uploadedfile import SimpleUploadedFile

from farms.models import Farm
from predictions.models import Prediction

from .pagination import paginate
from .serializers import DEFAULT_LIMIT, MAX_LIMIT, MAX_PAGE, HistoryQuerySerializer

User = get_user_model()


def make_image_file(name="leaf.jpg"):
    buffer = io.BytesIO()
    Image.new("RGB", (300, 300), color=(34, 139, 34)).save(buffer, format="JPEG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


MOCK_WEATHER_REPORT = {
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


def make_report(disease="Powdery Mildew", confidence=0.91, is_healthy=False, uncertain=False):
    """A Quick Scan report: live Module 1 contract + Module 2 + Module 3."""
    item = {
        "class_id": "tomato_" + disease.lower().replace(" ", "_"),
        "crop": "tomato",
        "disease": disease.lower().replace(" ", "_"),
        "display_name": disease,
        "is_healthy": is_healthy,
        "confidence": confidence,
    }
    return {
        "module1": {
            "status": "uncertain" if uncertain else "ok",
            "farm_id": "farm_001",
            "timestamp": "2026-09-26T04:55:12Z",
            "prediction": None if uncertain else item,
            "top3": [item],
            "crop_source": "user",
            "detected_crop": "tomato",
            "warnings": [],
            "message": None,
            "model_version": "efficientnet_b0-1.0",
            "inference_ms": 14.2,
            "request_id": "abc123def456",
        },
        "module2": None,
        "module3": MOCK_WEATHER_REPORT,
    }


MOCK_PREDICTION_REPORT = make_report()


class HistoryQuerySerializerTests(TestCase):
    """Unit tests for query-parameter validation, per REST_API_SPEC.md
    section 6's documented page/limit/search/sort/from_date/to_date
    parameters.
    """

    def test_defaults_when_nothing_provided(self):
        serializer = HistoryQuerySerializer(data={})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["page"], 1)
        self.assertEqual(serializer.validated_data["limit"], DEFAULT_LIMIT)
        self.assertEqual(serializer.validated_data["sort"], "newest")
        self.assertEqual(serializer.validated_data["search"], "")
        self.assertIsNone(serializer.validated_data["from_date"])
        self.assertIsNone(serializer.validated_data["to_date"])

    def test_rejects_non_integer_page(self):
        serializer = HistoryQuerySerializer(data={"page": "abc"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("page", serializer.errors)

    def test_rejects_zero_or_negative_page(self):
        for value in ("0", "-1"):
            serializer = HistoryQuerySerializer(data={"page": value})
            self.assertFalse(serializer.is_valid())
            self.assertIn("page", serializer.errors)

    def test_rejects_page_above_max(self):
        serializer = HistoryQuerySerializer(data={"page": str(MAX_PAGE + 1)})
        self.assertFalse(serializer.is_valid())
        self.assertIn("page", serializer.errors)

    def test_rejects_absurdly_large_page_without_crashing(self):
        """An offset-based OFFSET/LIMIT slice has no natural upper bound on
        `page`; without MAX_PAGE, a huge value would reach the database as
        an enormous SQL OFFSET instead of failing validation cleanly.
        """
        serializer = HistoryQuerySerializer(data={"page": "9" * 50})
        self.assertFalse(serializer.is_valid())
        self.assertIn("page", serializer.errors)

    def test_accepts_page_at_max(self):
        serializer = HistoryQuerySerializer(data={"page": str(MAX_PAGE)})
        self.assertTrue(serializer.is_valid())

    def test_rejects_non_integer_limit(self):
        serializer = HistoryQuerySerializer(data={"limit": "abc"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("limit", serializer.errors)

    def test_rejects_zero_or_negative_limit(self):
        for value in ("0", "-5"):
            serializer = HistoryQuerySerializer(data={"limit": value})
            self.assertFalse(serializer.is_valid())
            self.assertIn("limit", serializer.errors)

    def test_rejects_limit_above_max(self):
        serializer = HistoryQuerySerializer(data={"limit": str(MAX_LIMIT + 1)})
        self.assertFalse(serializer.is_valid())
        self.assertIn("limit", serializer.errors)

    def test_accepts_limit_at_max(self):
        serializer = HistoryQuerySerializer(data={"limit": str(MAX_LIMIT)})
        self.assertTrue(serializer.is_valid())

    def test_rejects_unsupported_sort_value(self):
        serializer = HistoryQuerySerializer(data={"sort": "highest_confidence"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("sort", serializer.errors)

    def test_rejects_invalid_date_format(self):
        serializer = HistoryQuerySerializer(data={"from_date": "31-07-2026"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("from_date", serializer.errors)

    def test_rejects_from_date_after_to_date(self):
        serializer = HistoryQuerySerializer(
            data={"from_date": "2026-08-01", "to_date": "2026-07-01"}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("from_date", serializer.errors)

    def test_accepts_equal_from_and_to_date(self):
        serializer = HistoryQuerySerializer(
            data={"from_date": "2026-08-01", "to_date": "2026-08-01"}
        )
        self.assertTrue(serializer.is_valid())


class PaginateTests(TestCase):
    def test_slices_by_offset_and_limit(self):
        self.assertEqual(paginate(list(range(10)), page=1, limit=3), [0, 1, 2])
        self.assertEqual(paginate(list(range(10)), page=2, limit=3), [3, 4, 5])
        self.assertEqual(paginate(list(range(10)), page=4, limit=3), [9])
        self.assertEqual(paginate(list(range(10)), page=5, limit=3), [])


class HistoryListViewTests(APITestCase):
    """GET /api/v1/history/ per REST_API_SPEC.md section 6."""

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
        self.url = reverse("history-list")

    def _make_prediction(self, *, user, farm=None, disease="Powdery Mildew", confidence=0.91, uncertain=False, created_at=None):
        prediction = Prediction.objects.create(
            user=user,
            farm=farm or self.farm,
            uploaded_image=make_image_file(),
            prediction_report=make_report(disease, confidence, uncertain=uncertain),
        )
        if created_at is not None:
            Prediction.objects.filter(pk=prediction.pk).update(created_at=created_at)
            prediction.refresh_from_db()
        return prediction

    # --- Authentication ---

    def test_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- Envelope / empty state ---

    def test_response_envelope_matches_standard_contract(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.data.keys()), {"success", "message", "data"})

    def test_returns_empty_list_when_no_predictions(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.data["data"], [])

    def test_list_item_field_names_match_section_6_contract(self):
        self._make_prediction(user=self.user)
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        item = response.data["data"][0]
        self.assertEqual(
            set(item.keys()),
            {"prediction_id", "diagnosis", "confidence", "recommended_crop", "created_at"},
        )
        self.assertEqual(item["diagnosis"], "Powdery Mildew")
        self.assertEqual(item["confidence"], 0.91)

    def test_uncertain_module1_result_lists_null_diagnosis_and_confidence(self):
        self._make_prediction(user=self.user, uncertain=True)
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        item = response.data["data"][0]
        self.assertIsNone(item["diagnosis"])
        self.assertIsNone(item["confidence"])

    def test_recommended_crop_is_always_null(self):
        self._make_prediction(user=self.user)
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertIsNone(response.data["data"][0]["recommended_crop"])

    # --- Ownership ---

    def test_returns_only_own_predictions(self):
        own = self._make_prediction(user=self.user)
        self._make_prediction(user=self.other_user)
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        ids = [item["prediction_id"] for item in response.data["data"]]
        self.assertEqual(ids, [str(own.id)])

    # --- Ordering / sort ---

    def test_default_order_is_newest_first(self):
        older = self._make_prediction(user=self.user, created_at=timezone.now() - timedelta(days=1))
        newer = self._make_prediction(user=self.user)
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        ids = [item["prediction_id"] for item in response.data["data"]]
        self.assertEqual(ids, [str(newer.id), str(older.id)])

    def test_sort_newest_explicit(self):
        older = self._make_prediction(user=self.user, created_at=timezone.now() - timedelta(days=1))
        newer = self._make_prediction(user=self.user)
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url, {"sort": "newest"})

        ids = [item["prediction_id"] for item in response.data["data"]]
        self.assertEqual(ids, [str(newer.id), str(older.id)])

    def test_sort_oldest(self):
        older = self._make_prediction(user=self.user, created_at=timezone.now() - timedelta(days=1))
        newer = self._make_prediction(user=self.user)
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url, {"sort": "oldest"})

        ids = [item["prediction_id"] for item in response.data["data"]]
        self.assertEqual(ids, [str(older.id), str(newer.id)])

    # --- Search ---

    def test_search_matches_diagnosis_case_insensitive_partial(self):
        match = self._make_prediction(user=self.user, disease="Powdery Mildew")
        self._make_prediction(user=self.user, disease="Healthy")
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url, {"search": "mildew"})

        ids = [item["prediction_id"] for item in response.data["data"]]
        self.assertEqual(ids, [str(match.id)])

    def test_search_no_match_returns_empty(self):
        self._make_prediction(user=self.user, disease="Powdery Mildew")
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url, {"search": "nonexistent-disease"})

        self.assertEqual(response.data["data"], [])

    # --- Pagination ---

    def test_page_and_limit_slice_results(self):
        predictions = [
            self._make_prediction(
                user=self.user, created_at=timezone.now() - timedelta(days=4 - i)
            )
            for i in range(5)
        ]  # oldest -> newest: predictions[0]..predictions[4]
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url, {"page": 2, "limit": 2, "sort": "oldest"})

        ids = [item["prediction_id"] for item in response.data["data"]]
        self.assertEqual(ids, [str(predictions[2].id), str(predictions[3].id)])

    def test_default_limit_caps_results(self):
        for i in range(DEFAULT_LIMIT + 5):
            self._make_prediction(user=self.user, created_at=timezone.now() - timedelta(minutes=i))
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(len(response.data["data"]), DEFAULT_LIMIT)

    def test_invalid_page_returns_422(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url, {"page": "0"})

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertFalse(response.data["success"])
        self.assertIn("page", response.data["errors"])

    def test_invalid_limit_returns_422(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url, {"limit": str(MAX_LIMIT + 1)})

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("limit", response.data["errors"])

    def test_page_far_beyond_available_records_returns_empty_list(self):
        self._make_prediction(user=self.user)
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url, {"page": MAX_PAGE})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"], [])

    def test_absurdly_large_page_returns_422_not_500(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url, {"page": "9" * 50})

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("page", response.data["errors"])

    # --- Date filtering ---

    def test_from_date_and_to_date_inclusive_range(self):
        in_range = self._make_prediction(
            user=self.user, created_at=timezone.make_aware(timezone.datetime(2026, 8, 15, 10, 0))
        )
        before_range = self._make_prediction(
            user=self.user, created_at=timezone.make_aware(timezone.datetime(2026, 8, 1, 10, 0))
        )
        after_range = self._make_prediction(
            user=self.user, created_at=timezone.make_aware(timezone.datetime(2026, 9, 1, 10, 0))
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            self.url, {"from_date": "2026-08-10", "to_date": "2026-08-20"}
        )

        ids = [item["prediction_id"] for item in response.data["data"]]
        self.assertEqual(ids, [str(in_range.id)])
        self.assertNotIn(str(before_range.id), ids)
        self.assertNotIn(str(after_range.id), ids)

    def test_to_date_includes_entire_day(self):
        late_on_to_date = self._make_prediction(
            user=self.user, created_at=timezone.make_aware(timezone.datetime(2026, 8, 20, 23, 59))
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url, {"to_date": "2026-08-20"})

        ids = [item["prediction_id"] for item in response.data["data"]]
        self.assertIn(str(late_on_to_date.id), ids)

    def test_invalid_date_returns_422(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url, {"from_date": "not-a-date"})

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("from_date", response.data["errors"])

    def test_from_date_after_to_date_returns_422(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            self.url, {"from_date": "2026-08-20", "to_date": "2026-08-10"}
        )

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("from_date", response.data["errors"])


class HistoryDetailViewTests(APITestCase):
    """GET/DELETE /api/v1/history/{prediction_id}/ per REST_API_SPEC.md
    section 6.
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
            prediction_report=MOCK_PREDICTION_REPORT,
        )
        self.url = reverse("history-detail", args=[self.prediction.id])

    # --- GET ---

    def test_get_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_returns_complete_prediction_information(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["prediction_id"], str(self.prediction.id))
        self.assertEqual(
            response.data["data"]["prediction_report"], self.prediction.prediction_report
        )
        self.assertIsNone(response.data["data"]["final_diagnosis"])
        self.assertIsNone(response.data["data"]["confidence_score"])

    def test_get_nonexistent_prediction_returns_404(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("history-detail", args=[uuid.uuid4()]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_malformed_uuid_returns_404(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/v1/history/not-a-uuid/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_another_users_prediction_returns_404(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(self.url)

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
        self.assertEqual(response.data["message"], "Prediction deleted successfully.")
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

        response = self.client.delete(reverse("history-detail", args=[uuid.uuid4()]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
