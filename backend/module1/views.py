import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ai_services.disease_module_client import (
    DiseaseModuleServiceError,
    call_disease_module_predict,
)
from farms.models import Farm

from .models import DiseaseCheck
from .serializers import DiseaseCheckRequestSerializer

logger = logging.getLogger("greenguard")

# Maps ai/API_CONTRACT.md's documented error codes to (http_status, message)
# for this app's own response. Messages are friendly and farmer-facing, per
# CLAUDE.md ("Always show friendly error messages. Never expose server
# errors."); UNAUTHORIZED (a server-side X-API-Key misconfiguration, never
# the farmer's fault) is deliberately reported as a generic unavailable
# service, not surfaced as an auth problem. INVALID_CROP's upstream message
# already lists the valid crops in the exact farmer-facing wording the AI
# team wrote, so it is forwarded rather than replaced.
_ERROR_RESPONSE_MAP = {
    "MISSING_IMAGE": (status.HTTP_400_BAD_REQUEST, "Please upload a leaf photo to continue."),
    "INVALID_IMAGE": (
        status.HTTP_400_BAD_REQUEST,
        "The uploaded file is not a valid image. Please try a different photo.",
    ),
    "IMAGE_TOO_SMALL": (
        status.HTTP_400_BAD_REQUEST,
        "The image is too small. Please upload a clearer, larger photo.",
    ),
    "INVALID_REQUEST": (
        status.HTTP_400_BAD_REQUEST,
        "The request could not be processed. Please try again.",
    ),
    "FILE_TOO_LARGE": (status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Image size must not exceed 10 MB."),
    "INVALID_CROP": (status.HTTP_422_UNPROCESSABLE_ENTITY, None),
    "UNAUTHORIZED": (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "Disease detection service is currently unavailable. Please try again later.",
    ),
    "MODEL_NOT_READY": (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "Disease detection service is starting up. Please try again in a moment.",
    ),
    "INTERNAL_ERROR": (status.HTTP_500_INTERNAL_SERVER_ERROR, "Prediction Failed"),
}
_DEFAULT_ERROR_RESPONSE = (status.HTTP_500_INTERNAL_SERVER_ERROR, "Prediction Failed")


def _get_owned_farm(user, farm_id):
    try:
        return Farm.objects.get(id=farm_id, user=user)
    except (Farm.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        return None


def _error_response(exc: DiseaseModuleServiceError) -> Response:
    http_status, message = _ERROR_RESPONSE_MAP.get(exc.error_code, _DEFAULT_ERROR_RESPONSE)
    if message is None:
        # INVALID_CROP: the module's own message is already farmer-facing
        # text listing the valid crops (ai/API_CONTRACT.md), not a raw
        # server error -- fall back to a generic message only if it's
        # somehow absent.
        message = exc.upstream_message or "The selected crop isn't recognized. Please choose a supported crop."
    return Response({"success": False, "message": message}, status=http_status)


class DiseaseAnalyzeView(APIView):
    """POST /api/v1/module1/analyze/ -- live Module 1 (Disease Detection).

    Standalone endpoint. Quick Scan (POST /api/v1/predictions/analyze/)
    calls the same live service and stores its response as the analysis
    report's `module1` section.
    Forwards the live Disease Module's full JSON response (`status`,
    `prediction`, `top3`, `crop_source`, `detected_crop`, `warnings`,
    `message`, `model_version`, `inference_ms`, `request_id`) verbatim under
    `data`, per CLAUDE.md's AI Contract ("never modify AI outputs, never
    rename JSON fields"). Every successful call (status "ok" or "uncertain")
    is additionally persisted as a DiseaseCheck row as an internal side
    effect that does not alter the response below.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DiseaseCheckRequestSerializer(data=request.data)
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
        image_file = data["image"]
        crop = data.get("crop")

        farm = _get_owned_farm(request.user, data["farm_id"])
        if farm is None:
            return Response(
                {"success": False, "message": "Farm not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            result = call_disease_module_predict(image_file, crop=crop, farm_id=str(farm.id))
        except DiseaseModuleServiceError as exc:
            logger.error(
                "Disease Module call failed for farm_id=%s (error_code=%s, http_status=%s)",
                farm.id,
                exc.error_code,
                exc.http_status,
            )
            return _error_response(exc)

        DiseaseCheck.objects.create(
            farm=farm,
            crop_requested=crop,
            status_result=result["status"],
            response_payload=result,
        )

        logger.info(
            "Disease check completed for farm_id=%s crop=%s status=%s",
            farm.id,
            crop,
            result["status"],
        )

        return Response(
            {
                "success": True,
                "message": "Disease check completed successfully.",
                "data": result,
            }
        )
