import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from farms.models import Farm
from notifications.models import Notification
from predictions.models import Prediction
from weather.services import (
    WeatherServiceError,
    fetch_weather_for_coordinates,
    to_dashboard_summary,
)

logger = logging.getLogger("greenguard")

# GET /api/v1/dashboard/recent-predictions/ `limit` bounds. The spec gives
# only the `?limit=5` example; 50 caps abusive requests.
DEFAULT_RECENT_LIMIT = 5
MAX_RECENT_LIMIT = 50

EMPTY_WEATHER_SUMMARY = {
    "temperature": None,
    "humidity": None,
    "rainfall": None,
    "wind_speed": None,
    "fungal_disease_risk": None,
    "heat_stress_risk": None,
    "drought_risk": None,
}


class FarmNotFound(Exception):
    """Raised when an explicitly requested farm_id does not belong to the user."""


class NoFarmAvailable(Exception):
    """Raised when the user has no farms at all and none was requested."""


def _resolve_farm(user, farm_id):
    """Resolve which farm's coordinates to use for weather retrieval.

    REST_API_SPEC.md's dashboard weather endpoint documents no parameters,
    and "active farm" (Phase 3) is deliberately frontend-only, never
    persisted to the database. So this accepts an optional ``farm_id`` query
    parameter (additive, non-breaking, same pattern already used for
    ``limit`` on recent-predictions): the frontend passes the user's
    locally-selected active farm. If omitted, falls back to the user's most
    recently created farm (Farm's default ordering).
    """
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


def _parse_limit(raw):
    try:
        limit = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_RECENT_LIMIT
    return max(1, min(limit, MAX_RECENT_LIMIT))


def _recent_prediction_item(prediction):
    """One recent-predictions row. `diagnosis`/`confidence` are Module 1's
    own result read verbatim (null when Module 1 was uncertain) -- see
    Prediction.disease_result_name."""
    return {
        "prediction_id": str(prediction.id),
        "diagnosis": prediction.disease_result_name,
        "confidence": prediction.disease_result_confidence,
        "created_at": prediction.created_at,
    }


class DashboardOverviewView(APIView):
    """GET /api/v1/dashboard/ per REST_API_SPEC.md section 5.

    Prediction statistics count Module 1's own `prediction.is_healthy` flag
    on the user's analyses -- uncertain results fall in neither count.
    `accuracy` stays null: no module reports one.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        predictions = Prediction.objects.filter(user=user)
        total_predictions = predictions.count()
        healthy_count = predictions.filter(
            prediction_report__module1__prediction__is_healthy=True
        ).count()
        diseased_count = predictions.filter(
            prediction_report__module1__prediction__is_healthy=False
        ).count()
        total_farms = Farm.objects.filter(user=user).count()
        unread_notification_count = Notification.objects.filter(
            user=user, is_read=False
        ).count()

        return Response(
            {
                "success": True,
                "message": "Dashboard loaded successfully.",
                "data": {
                    "welcome_message": f"Welcome back, {user.full_name}",
                    "total_predictions": total_predictions,
                    "recent_predictions": min(total_predictions, DEFAULT_RECENT_LIMIT),
                    "notification_count": unread_notification_count,
                    # This compact snippet isn't rendered anywhere in the
                    # frontend (the dashboard Weather Card calls
                    # /dashboard/weather/ directly), so it is intentionally
                    # left null rather than issuing a second, redundant
                    # Weather Module request on every dashboard load.
                    "weather_summary": None,
                    "farm_summary": {"total_farms": total_farms},
                    "prediction_statistics": {
                        "healthy_count": healthy_count,
                        "diseased_count": diseased_count,
                        "accuracy": None,
                    },
                },
            }
        )


class DashboardWeatherView(APIView):
    """GET /api/v1/dashboard/weather/ per REST_API_SPEC.md section 5.

    Accepts an optional ``farm_id`` query parameter (see ``_resolve_farm``).
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
                    "data": EMPTY_WEATHER_SUMMARY,
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
                "message": "Weather summary loaded successfully.",
                "data": to_dashboard_summary(weather),
            }
        )


class DashboardRecentPredictionsView(APIView):
    """GET /api/v1/dashboard/recent-predictions/ per REST_API_SPEC.md section 5.

    The user's newest analyses first, bounded by the documented ``limit``
    query parameter (invalid values fall back to the default).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        limit = _parse_limit(request.query_params.get("limit", DEFAULT_RECENT_LIMIT))
        predictions = Prediction.objects.filter(user=request.user).order_by("-created_at")[:limit]
        return Response(
            {
                "success": True,
                "message": "Recent predictions retrieved successfully.",
                "data": [_recent_prediction_item(prediction) for prediction in predictions],
            }
        )


class DashboardRecommendationsView(APIView):
    """GET /api/v1/dashboard/recommendations/ per REST_API_SPEC.md section 5.

    Always empty: these were the retired Fusion layer's recommendations, and
    no current module produces a cross-module recommendation list. Module 2's
    own recommendation notes are shown on its result instead.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "success": True,
                "message": "Recommendations loaded successfully.",
                "data": [],
            }
        )
