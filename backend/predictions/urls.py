from django.urls import path

from .views import PredictionAnalyzeView, PredictionDetailView, PredictionListView

urlpatterns = [
    path("predictions/analyze/", PredictionAnalyzeView.as_view(), name="predictions-analyze"),
    path("predictions/", PredictionListView.as_view(), name="predictions-list"),
    path(
        "predictions/<str:prediction_id>/",
        PredictionDetailView.as_view(),
        name="predictions-detail",
    ),
]
