import uuid

from django.db import models


class Module2Analysis(models.Model):
    """One Soil & Nutrient Health Check run, per DATABASE_SPECIFICATION.md section 6A.

    Append-only: rows are never updated after creation, so a Prediction that
    references one (predictions.Prediction.module2_analysis) keeps a stable,
    reproducible snapshot even if the farm's Module 2 result changes later.
    Standalone from the Prediction workflow -- a row is created for every
    successful POST /api/v1/module2/analyze/ call regardless of whether a
    Prediction is ever made for the farm. request_payload/response_payload
    are stored exactly as validated/returned; Module 2's API contract itself
    is unaffected by this model.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm = models.ForeignKey(
        "farms.Farm", on_delete=models.CASCADE, related_name="module2_analyses"
    )
    crop_supported = models.BooleanField()
    request_payload = models.JSONField()
    response_payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "module2_analyses"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["farm", "created_at"]),
        ]

    def __str__(self):
        return f"Module2Analysis({self.farm_id}, {self.created_at:%Y-%m-%d %H:%M:%S})"
