import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ai_services.module2_client import Module2ServiceError, call_module2_orchestrator
from farms.models import Farm
from weather.services import WeatherServiceError, fetch_weather_for_coordinates

from .field_options import crop_model_support
from .models import Module2Analysis
from .serializers import Module2RequestSerializer

logger = logging.getLogger("greenguard")

UNSUPPORTED_CROP_MESSAGE = "Nutrient and soil-condition analysis isn't available yet for this crop."


def _get_owned_farm(user, farm_id):
    try:
        return Farm.objects.get(id=farm_id, user=user)
    except (Farm.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        return None


def _unsupported_crop_data():
    return {
        "crop_supported": False,
        "message": UNSUPPORTED_CROP_MESSAGE,
        "module2a": None,
        "module2b": None,
        "overall_soil_health_score": None,
        "overall_soil_health_label": None,
        "recommendation_notes": None,
    }


def _serializable_request_payload(validated_data):
    """Copy of the validated request with non-JSON types (UUID) made plain.

    Stored as Module2Analysis.request_payload -- the values themselves are
    exactly what was validated, only the Python type is adjusted so it can
    round-trip through a JSONField.
    """
    payload = dict(validated_data)
    payload["farm_id"] = str(payload["farm_id"])
    return payload


def _persist_analysis(farm, *, crop_supported, request_payload, response_payload):
    """Append-only side effect: never affects the HTTP response returned above."""
    Module2Analysis.objects.create(
        farm=farm,
        crop_supported=crop_supported,
        request_payload=request_payload,
        response_payload=response_payload,
    )


class Module2AnalyzeView(APIView):
    """POST /api/v1/module2/analyze/ per REST_API_SPEC.md section 8A.

    Runs a Soil & Nutrient Health Check for a farm from a farmer
    questionnaire. Standalone: independent of the image-based prediction
    workflow (Quick Scan only reads the latest persisted result, never
    calls this live). The request/response
    contract is frozen. Every successful run (supported or unsupported
    crop) is additionally persisted as a Module2Analysis row -- see
    DATABASE_SPECIFICATION.md section 6A -- as an internal side effect that
    does not alter the response below.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = Module2RequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "message": "Validation failed.",
                    "errors": serializer.errors,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        data = serializer.validated_data

        farm = _get_owned_farm(request.user, data["farm_id"])
        if farm is None:
            return Response(
                {"success": False, "message": "Farm not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        crop = data["crop"]
        if crop not in crop_model_support()["trained_and_supported"]:
            logger.info(
                "Module 2 check for unsupported crop=%s (farm_id=%s) -- short-circuiting.",
                crop,
                farm.id,
            )
            response_data = _unsupported_crop_data()
            _persist_analysis(
                farm,
                crop_supported=False,
                request_payload=_serializable_request_payload(data),
                response_payload=response_data,
            )
            return Response(
                {
                    "success": True,
                    "message": "Soil & nutrient health check completed.",
                    "data": response_data,
                }
            )

        try:
            weather = fetch_weather_for_coordinates(
                farm.latitude, farm.longitude, farm_id=str(farm.id)
            )
        except WeatherServiceError:
            logger.warning("Module 2 weather resolution failed for farm_id=%s", farm.id)
            return Response(
                {"success": False, "message": "Weather service is temporarily unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        orchestrator_payload = {
            "crop": crop,
            "growth_stage": data["growth_stage"],
            "soil_type": data["soil_type"],
            "last_fertilizer_type": data["last_fertilizer_type"],
            "days_since_fertilizer": data["days_since_fertilizer"],
            "irrigation_source": data["irrigation_source"],
            "irrigation_adequacy": data["irrigation_adequacy"],
            # Resolved server-side from farm_id via the Module 3 (Weather
            # Risk) service, per REST_API_SPEC.md section 8A -- the farmer
            # never enters these, and the frontend never sends them. Pulled
            # from the nested `weather` object of the Module 3 contract
            # (see weather/services.py) -- field access only, no
            # recalculation.
            "temperature_c": weather["weather"]["temperature"],
            "humidity_pct": weather["weather"]["humidity"],
            "rainfall_mm_last_7_days": weather["weather"]["rainfall_last_7_days_mm"],
            "ph_value": data.get("ph_value"),
            "soil_moisture_pct": data.get("soil_moisture_pct"),
            "light_intensity_lux": data.get("light_intensity_lux"),
            "symptoms": data["symptoms"],
        }

        try:
            result = call_module2_orchestrator(orchestrator_payload)
        except Module2ServiceError:
            logger.error("Module 2 Orchestrator call failed for farm_id=%s", farm.id)
            return Response(
                {"success": False, "message": "AI module is currently unavailable."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info("Module 2 check completed for farm_id=%s crop=%s", farm.id, crop)

        _persist_analysis(
            farm,
            crop_supported=result["crop_supported"],
            request_payload=_serializable_request_payload(data),
            response_payload=result,
        )

        return Response(
            {
                "success": True,
                "message": "Soil & nutrient health check completed successfully.",
                "data": result,
            }
        )
