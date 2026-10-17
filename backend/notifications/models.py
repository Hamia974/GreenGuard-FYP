import uuid

from django.conf import settings
from django.db import models


class Notification(models.Model):
    """User notification, per DATABASE_SPECIFICATION.md section 6.

    This app itself is read/mark-read/delete only (per Phase 8's explicit
    product decision) -- notification rows are created by whichever event
    they describe. `predictions/views.py`'s `PredictionAnalyzeView` creates
    one on every successful analysis ("Prediction Completed", matching
    REST_API_SPEC.md section 7's example verbatim).
    """

    class NotificationType(models.TextChoices):
        SYSTEM = "system", "System"
        PREDICTION = "prediction", "Prediction"
        WEATHER = "weather", "Weather"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["is_read"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return self.title
