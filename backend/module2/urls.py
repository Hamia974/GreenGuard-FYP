from django.urls import path

from .views import Module2AnalyzeView

urlpatterns = [
    path("module2/analyze/", Module2AnalyzeView.as_view(), name="module2-analyze"),
]
