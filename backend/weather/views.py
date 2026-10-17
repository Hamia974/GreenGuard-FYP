import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from farms.models import Farm

from .services import WeatherServiceError, fetch_weather_for_coordinates

logger = logging.getLogger("greenguard")


class FarmNotFound(Exception):
    """Raised when an explicitly requested farm_id does not belong to the user."""


class NoFarmAvailable(Exception):
    """Raised when the user has no farms at all and none was requested."""


def _resolve_farm(user, farm_id):
    """Same resolution rule as dashboard.views._resolve_farm: an explicit
    ``farm_id`` query parameter, or the user's most recently created farm."""
    queryset = Farm.objects.filter(user=user)
    if farm_id:
        farm = queryset.filter(id=farm_id).first()
        if farm is None:
            raise FarmNotFound
        return farm

    farm = queryset.first()
    if farm is None:
        raise NoFarmAvailable
    return farm


class WeatherCurrentView(APIView):
    """GET /api/v1/weather/current/ -- full Module 3 (Weather Risk Engine)
    report for the Weather page, per REST_API_SPEC.md section 5A and the
    real ai/Weather_Module contract.

    Unlike GET /api/v1/dashboard/weather/ (which returns the pre-existing
    flat dashboard-card summary for backward compatibility), this returns
    the Weather Module's response verbatim -- including `units`,
    `*_reason` explanations, and the nullable `forecast` /
    `predicted_risk_assessment` LSTM add-on fields -- for the dedicated
    Weather page (UI_SPECIFICATION.md section 14).

    Accepts an optional ``farm_id`` query parameter, same pattern as the
    dashboard weather endpoint.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        farm_id = request.query_params.get("farm_id")

        try:
            farm = _resolve_farm(request.user, farm_id)
        except FarmNotFound:
            return Response(
                {"success": False, "message": "Farm not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except NoFarmAvailable:
            return Response(
                {
                    "success": True,
                    "message": "Add a farm to see weather insights.",
                    "data": None,
                }
            )

        try:
            weather = fetch_weather_for_coordinates(
                farm.latitude, farm.longitude, farm_id=str(farm.id)
            )
        except WeatherServiceError:
            logger.warning("Weather retrieval failed for farm_id=%s", farm.id)
            return Response(
                {"success": False, "message": "Weather service is temporarily unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "success": True,
                "message": "Weather report loaded successfully.",
                "data": weather,
            }
        )
