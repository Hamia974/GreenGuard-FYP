import logging

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle, UserRateThrottle
from rest_framework.views import APIView

from .geocoding import GeocodingError, geocode_address
from .models import Farm
from .serializers import FarmGeocodeSerializer, FarmSerializer, FarmWriteSerializer

logger = logging.getLogger("greenguard")


def _validation_error(serializer):
    return Response(
        {
            "success": False,
            "message": "Validation failed.",
            "errors": serializer.errors,
        },
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


def _not_found():
    return Response(
        {"success": False, "message": "Farm not found."},
        status=status.HTTP_404_NOT_FOUND,
    )


def _get_owned_farm(user, farm_id):
    try:
        return Farm.objects.get(id=farm_id, user=user)
    except (Farm.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        return None


class FarmListCreateView(APIView):
    """GET/POST /api/v1/farms/ per REST_API_SPEC.md section 2."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        farms = Farm.objects.filter(user=request.user)
        serializer = FarmSerializer(farms, many=True)
        return Response(
            {
                "success": True,
                "message": "Farms retrieved successfully.",
                "data": serializer.data,
            }
        )

    def post(self, request):
        serializer = FarmWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer)

        farm = serializer.save(user=request.user)
        logger.info("Farm created: %s (user %s)", farm.id, request.user.email)

        return Response(
            {
                "success": True,
                "message": "Farm created successfully.",
                "data": FarmSerializer(farm).data,
            },
            status=status.HTTP_201_CREATED,
        )


class FarmDetailView(APIView):
    """GET/PUT/DELETE /api/v1/farms/{farm_id}/ per REST_API_SPEC.md section 2."""

    permission_classes = [IsAuthenticated]

    def get(self, request, farm_id):
        farm = _get_owned_farm(request.user, farm_id)
        if farm is None:
            return _not_found()

        return Response(
            {
                "success": True,
                "message": "Farm retrieved successfully.",
                "data": FarmSerializer(farm).data,
            }
        )

    def put(self, request, farm_id):
        farm = _get_owned_farm(request.user, farm_id)
        if farm is None:
            return _not_found()

        serializer = FarmWriteSerializer(instance=farm, data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer)

        farm = serializer.save()
        logger.info("Farm updated: %s (user %s)", farm.id, request.user.email)

        return Response(
            {
                "success": True,
                "message": "Farm updated successfully.",
                "data": FarmSerializer(farm).data,
            }
        )

    def delete(self, request, farm_id):
        farm = _get_owned_farm(request.user, farm_id)
        if farm is None:
            return _not_found()

        farm.delete()
        logger.info("Farm deleted: %s (user %s)", farm_id, request.user.email)

        return Response({"success": True, "message": "Farm deleted successfully."})


class FarmGeocodeView(APIView):
    """POST /api/v1/farms/geocode/ per REST_API_SPEC.md section 2.

    Turns the farmer's free-text address into candidate coordinates for the
    Farm form. Nothing is saved here -- the farmer confirms one candidate
    and the form submits it through the unchanged create/update endpoints.
    """

    permission_classes = [IsAuthenticated]
    # Extra per-user cap on top of the global user rate: every call may hit
    # a paid / rate-limited third-party provider.
    throttle_classes = [] if settings.TESTING else [UserRateThrottle, ScopedRateThrottle]
    throttle_scope = "geocode"

    def post(self, request):
        serializer = FarmGeocodeSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer)

        try:
            results = geocode_address(
                serializer.validated_data["address"], serializer.validated_data["language"]
            )
        except GeocodingError:
            return Response(
                {"success": False, "message": "Location service is temporarily unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "success": True,
                "message": (
                    "Locations found." if results else "No location found for this address."
                ),
                "data": {"results": results},
            }
        )
