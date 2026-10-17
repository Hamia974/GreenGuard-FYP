from django.urls import path

from .views import HistoryDetailView, HistoryListView

urlpatterns = [
    path("history/", HistoryListView.as_view(), name="history-list"),
    path(
        "history/<str:prediction_id>/",
        HistoryDetailView.as_view(),
        name="history-detail",
    ),
]
