from django.urls import path

from .views import FarmDetailView, FarmGeocodeView, FarmListCreateView

urlpatterns = [
    path("farms/", FarmListCreateView.as_view(), name="farm-list-create"),
    # Must precede farms/<str:farm_id>/, which would otherwise match "geocode".
    path("farms/geocode/", FarmGeocodeView.as_view(), name="farm-geocode"),
    path("farms/<str:farm_id>/", FarmDetailView.as_view(), name="farm-detail"),
]
