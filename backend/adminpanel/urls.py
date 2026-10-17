from django.urls import path

from .views import (
    AdminAIMonitoringView,
    AdminDashboardView,
    AdminPredictionDetailView,
    AdminPredictionListView,
    AdminStatisticsView,
    AdminSystemHealthView,
    AdminUserDetailView,
    AdminUserListView,
    AdminUserStatusView,
)

urlpatterns = [
    path("admin/dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("admin/users/", AdminUserListView.as_view(), name="admin-user-list"),
    path("admin/users/<str:user_id>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
    path(
        "admin/users/<str:user_id>/status/",
        AdminUserStatusView.as_view(),
        name="admin-user-status",
    ),
    path("admin/predictions/", AdminPredictionListView.as_view(), name="admin-prediction-list"),
    path(
        "admin/predictions/<str:prediction_id>/",
        AdminPredictionDetailView.as_view(),
        name="admin-prediction-detail",
    ),
    path("admin/ai-monitoring/", AdminAIMonitoringView.as_view(), name="admin-ai-monitoring"),
    path("admin/system-health/", AdminSystemHealthView.as_view(), name="admin-system-health"),
    path("admin/statistics/", AdminStatisticsView.as_view(), name="admin-statistics"),
]
