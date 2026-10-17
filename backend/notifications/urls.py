from django.urls import path

from .views import NotificationDetailView, NotificationListView, NotificationMarkReadView

urlpatterns = [
    path("notifications/", NotificationListView.as_view(), name="notification-list"),
    path(
        "notifications/<str:notification_id>/read/",
        NotificationMarkReadView.as_view(),
        name="notification-mark-read",
    ),
    path(
        "notifications/<str:notification_id>/",
        NotificationDetailView.as_view(),
        name="notification-detail",
    ),
]
