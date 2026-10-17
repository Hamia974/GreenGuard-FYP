import uuid

from django.conf import settings
from django.db import models

from .storage import generate_prediction_image_filename


class Prediction(models.Model):
    """One Quick Scan analysis, per DATABASE_SPECIFICATION.md section 6.

    Rows are created by POST /api/v1/predictions/analyze/
    (predictions.views.PredictionAnalyzeView). `prediction_report` holds the
    three independent AI module results verbatim -- `module1` (Disease
    Detection), `module2` (Soil & Nutrient snapshot, or null) and `module3`
    (Weather Risk). Module 4 is the application-level report built from
    those three; it runs no model and produces no result of its own.

    `final_diagnosis`, `confidence_score` and `recommendation_summary` were
    populated by the retired ANN Fusion service. No module produces them any
    more, so new rows leave them null rather than inventing a value; they
    are kept (nullable) only so rows created under the old architecture
    stay readable.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="predictions"
    )
    farm = models.ForeignKey(
        "farms.Farm", on_delete=models.CASCADE, related_name="predictions"
    )
    module2_analysis = models.ForeignKey(
        "module2.Module2Analysis",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="predictions",
    )
    uploaded_image = models.ImageField(
        upload_to=generate_prediction_image_filename, max_length=500
    )
    final_diagnosis = models.CharField(max_length=255, null=True, blank=True)
    confidence_score = models.FloatField(null=True, blank=True)
    prediction_report = models.JSONField()
    recommendation_summary = models.TextField(null=True, blank=True)
    prediction_status = models.CharField(
        max_length=30, choices=Status.choices, default=Status.COMPLETED
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "predictions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["farm", "created_at"]),
            models.Index(fields=["prediction_status"]),
        ]

    def __str__(self):
        return f"{self.disease_result_name or 'Analysis'} ({self.id})"

    @property
    def _module1_prediction(self):
        """Module 1's own `prediction` object from the live Disease Module
        contract (ai/API_CONTRACT.md), or None when Module 1 abstained
        (`status: "uncertain"`) or the row predates that contract."""
        module1 = (self.prediction_report or {}).get("module1")
        if not isinstance(module1, dict) or "top3" not in module1:
            return None
        prediction = module1.get("prediction")
        return prediction if isinstance(prediction, dict) else None

    @property
    def disease_result_name(self):
        """Module 1's `display_name`, read verbatim -- never derived."""
        prediction = self._module1_prediction
        return prediction.get("display_name") if prediction else None

    @property
    def disease_result_confidence(self):
        """Module 1's own `confidence`, read verbatim -- never recalculated."""
        prediction = self._module1_prediction
        return prediction.get("confidence") if prediction else None
