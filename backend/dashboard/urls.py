from django.urls import path

from .views import (
    DashboardOverviewView,
    DashboardRecentPredictionsView,
    DashboardRecommendationsView,
    DashboardWeatherView,
)

urlpatterns = [
    path("dashboard/", DashboardOverviewView.as_view(), name="dashboard-overview"),
    path("dashboard/weather/", DashboardWeatherView.as_view(), name="dashboard-weather"),
    path(
        "dashboard/recent-predictions/",
        DashboardRecentPredictionsView.as_view(),
        name="dashboard-recent-predictions",
    ),
    path(
        "dashboard/recommendations/",
        DashboardRecommendationsView.as_view(),
        name="dashboard-recommendations",
    ),
]
