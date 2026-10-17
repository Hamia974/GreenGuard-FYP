import uuid

from django.db import models


class DiseaseCheck(models.Model):
    """One live Module 1 (Disease Detection) call, mirroring the append-only
    Module2Analysis pattern (module2/models.py) rather than the Prediction
    model (predictions/models.py), which holds a full Quick Scan report
    (Module 1+2+3 results) this standalone check does not produce.

    Rows are never updated after creation. `response_payload` stores the
    live Disease Module's exact JSON response (ai/API_CONTRACT.md) -- never
    modified, never re-derived. The uploaded image itself is not persisted:
    the module's contract carries no requirement to keep it, and every
    result field a farmer needs (crop, disease, confidence, is_healthy,
    top3, warnings, message) already lives in `response_payload`.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm = models.ForeignKey(
        "farms.Farm", on_delete=models.CASCADE, related_name="disease_checks"
    )
    crop_requested = models.CharField(max_length=32, null=True, blank=True)
    status_result = models.CharField(max_length=16)
    response_payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "disease_checks"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["farm", "created_at"]),
        ]

    def __str__(self):
        return f"DiseaseCheck({self.farm_id}, {self.created_at:%Y-%m-%d %H:%M:%S})"
