from django.urls import path

from .views import DiseaseAnalyzeView

urlpatterns = [
    path("module1/analyze/", DiseaseAnalyzeView.as_view(), name="module1-analyze"),
]
