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
from module1.views import _error_response as _disease_module_error_response
from module2.models import Module2Analysis
from notifications.models import Notification
from weather.services import WeatherServiceError, fetch_weather_for_coordinates

from .models import Prediction
from .serializers import PredictionAnalyzeRequestSerializer, PredictionSerializer

logger = logging.getLogger("greenguard")


def _get_owned_farm(user, farm_id):
    try:
        return Farm.objects.get(id=farm_id, user=user)
    except (Farm.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        return None


def _prediction_not_found():
    return Response(
        {"success": False, "message": "Prediction not found."},
        status=status.HTTP_404_NOT_FOUND,
    )


def _get_owned_prediction(user, prediction_id):
    try:
        return Prediction.objects.get(id=prediction_id, user=user)
    except (Prediction.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        return None


def _get_deletable_prediction(user, prediction_id):
    """Owner or admin, per REST_API_SPEC.md's "Delete Prediction" section
    ("Only the owner of the prediction may delete it. Admin users may
    delete any prediction.") -- the only endpoint in this section with an
    admin override, so this lookup is kept separate from
    _get_owned_prediction rather than folding the override into it.
    """
    try:
        prediction = Prediction.objects.get(id=prediction_id)
    except (Prediction.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        return None
    if prediction.user_id != user.id and user.role != user.Role.ADMIN:
        return None
    return prediction


def _latest_module2_payload(farm):
    """The farm's latest persisted Module 2 snapshot, verbatim, or None.

    Module 2 needs the farmer's Soil & Nutrient questionnaire, which Quick
    Scan does not collect, so it is never invoked live here -- the result of
    the farmer's latest standalone Soil Test (POST /api/v1/module2/analyze/)
    is used instead. Whatever that row holds (a supported-crop result, an
    unsupported-crop result, or nothing at all) is passed straight through
    with no inspection or transformation.
    """
    analysis = Module2Analysis.objects.filter(farm=farm).order_by("-created_at").first()
    if analysis is None:
        return None, None
    return analysis, analysis.response_payload


class PredictionAnalyzeView(APIView):
    """POST /api/v1/predictions/analyze/ (Quick Scan) per REST_API_SPEC.md's
    "Analyze Plant" section.

    Collects the three independent AI module results and stores them
    together as one analysis -- Module 4 is this application-level report,
    not a model, and nothing here combines, scores, or reinterprets them:

    - module1: live Disease Module response (ai/API_CONTRACT.md), verbatim,
      including the `status: "uncertain"` / `prediction: null` case.
    - module2: the farm's latest persisted Soil & Nutrient result, or null.
    - module3: live Weather Risk Module response, verbatim.

    The Prediction row is created exactly once, after every module call has
    succeeded -- either one complete row is written or nothing is persisted.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PredictionAnalyzeRequestSerializer(data=request.data)
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

        farm = _get_owned_farm(request.user, data["farm_id"])
        if farm is None:
            return Response(
                {"success": False, "message": "Farm not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            module1_result = call_disease_module_predict(
                image_file, crop=data.get("crop"), farm_id=str(farm.id)
            )
        except DiseaseModuleServiceError as exc:
            logger.error(
                "Module 1 call failed for farm_id=%s (error_code=%s, http_status=%s)",
                farm.id,
                exc.error_code,
                exc.http_status,
            )
            return _disease_module_error_response(exc)

        # Rewind before Django's ImageField reads the upload again to store it.
        image_file.seek(0)

        module2_analysis, module2_payload = _latest_module2_payload(farm)

        try:
            module3_result = fetch_weather_for_coordinates(
                farm.latitude, farm.longitude, farm_id=str(farm.id)
            )
        except WeatherServiceError:
            logger.warning("Weather resolution failed for farm_id=%s", farm.id)
            return Response(
                {"success": False, "message": "Weather service is temporarily unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        prediction = Prediction.objects.create(
            user=request.user,
            farm=farm,
            module2_analysis=module2_analysis,
            uploaded_image=image_file,
            prediction_report={
                "module1": module1_result,
                "module2": module2_payload,
                "module3": module3_result,
            },
        )

        logger.info(
            "Analysis %s created for farm_id=%s (module1 status=%s, module2_analysis=%s)",
            prediction.id,
            farm.id,
            module1_result["status"],
            module2_analysis.id if module2_analysis else None,
        )

        # Real trigger for the deferred "wire automatic triggers (e.g. on
        # prediction completion)" note in notifications/models.py -- title
        # and message match REST_API_SPEC.md section 7's own documented
        # "Get Notifications" example verbatim, not invented here.
        Notification.objects.create(
            user=request.user,
            title="Prediction Completed",
            message="Your latest plant analysis is ready.",
            notification_type=Notification.NotificationType.PREDICTION,
        )

        return Response(
            {
                "success": True,
                "message": "Prediction completed successfully.",
                "data": PredictionSerializer(prediction, context={"request": request}).data,
            }
        )


class PredictionListView(APIView):
    """GET /api/v1/predictions/ per REST_API_SPEC.md section 3 ("Get
    Prediction History" / "Get All Predictions").

    Returns every prediction owned by the authenticated user, newest
    first (the model's default ordering). The spec documents this
    endpoint as "supporting" search/pagination/filtering/sorting but
    gives no concrete query-parameter or response contract for them
    (unlike Section 6's separate, not-yet-built /api/v1/history/
    endpoint, which does) -- so none of that is implemented here.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        predictions = Prediction.objects.filter(user=request.user)
        serializer = PredictionSerializer(
            predictions, many=True, context={"request": request}
        )
        return Response(
            {
                "success": True,
                "message": "Predictions retrieved successfully.",
                "data": serializer.data,
            }
        )


class PredictionDetailView(APIView):
    """GET/DELETE /api/v1/predictions/{prediction_id}/ per
    REST_API_SPEC.md section 3 ("Get Prediction Details" / "Delete
    Prediction").
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, prediction_id):
        prediction = _get_owned_prediction(request.user, prediction_id)
        if prediction is None:
            return _prediction_not_found()

        serializer = PredictionSerializer(prediction, context={"request": request})
        return Response(
            {
                "success": True,
                "message": "Prediction retrieved successfully.",
                "data": serializer.data,
            }
        )

    def delete(self, request, prediction_id):
        prediction = _get_deletable_prediction(request.user, prediction_id)
        if prediction is None:
            return _prediction_not_found()

        prediction.delete()
        logger.info(
            "Prediction %s deleted by user %s", prediction_id, request.user.email
        )

        return Response({"success": True, "message": "Prediction deleted successfully."})
