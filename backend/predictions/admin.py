from django.contrib import admin

from .models import Prediction


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = (
        "final_diagnosis",
        "user",
        "farm",
        "prediction_status",
        "confidence_score",
        "created_at",
    )
    list_filter = ("prediction_status", "created_at")
    search_fields = ("final_diagnosis", "user__email", "farm__farm_name")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)
