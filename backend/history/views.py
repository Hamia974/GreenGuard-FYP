import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from predictions.models import Prediction

from .pagination import paginate
from .serializers import HistoryDetailSerializer, HistoryListItemSerializer, HistoryQuerySerializer

logger = logging.getLogger("greenguard")


def _prediction_not_found():
    return Response(
        {"success": False, "message": "Prediction not found."},
        status=status.HTTP_404_NOT_FOUND,
    )


def _get_owned_prediction(user, prediction_id):
    """Same lookup shape as predictions.views._get_owned_prediction, kept as
    a local copy (not a cross-app import) per the Phase 7 architecture
    decision to isolate the history app from predictions' view-layer
    internals -- only the Prediction *model* is reused, not its views.
    """
    try:
        return Prediction.objects.get(id=prediction_id, user=user)
    except (Prediction.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        return None


def _get_deletable_prediction(user, prediction_id):
    """Owner or admin, per REST_API_SPEC.md section 6's "Delete Prediction"
    ("Only the owner of the prediction may delete it. Administrators may
    delete any record."). Mirrors predictions.views._get_deletable_prediction
    for the same reason as _get_owned_prediction above.
    """
    try:
        prediction = Prediction.objects.get(id=prediction_id)
    except (Prediction.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        return None
    if prediction.user_id != user.id and user.role != user.Role.ADMIN:
        return None
    return prediction


class HistoryListView(APIView):
    """GET /api/v1/history/ per REST_API_SPEC.md section 6 ("Get Prediction
    History").

    Reuses the same ``predictions`` table Phase 6 already built -- per
    DATABASE_SPECIFICATION.md section 6, there is only one predictions
    table; no second history table/model is introduced. This is a distinct
    API contract from GET /api/v1/predictions/ (Phase 6, untouched by this
    view): a narrower summary shape with real search/pagination/sort/date
    filtering, per section 6's own documented parameters.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = HistoryQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return Response(
                {
                    "success": False,
                    "message": "Validation failed.",
                    "errors": query.errors,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        params = query.validated_data
        predictions = Prediction.objects.filter(user=request.user)

        if params["search"]:
            predictions = predictions.filter(
                prediction_report__module1__prediction__display_name__icontains=params["search"]
            )

        if params["from_date"]:
            predictions = predictions.filter(created_at__date__gte=params["from_date"])
        if params["to_date"]:
            predictions = predictions.filter(created_at__date__lte=params["to_date"])

        predictions = predictions.order_by(
            "created_at" if params["sort"] == "oldest" else "-created_at"
        )

        page = paginate(predictions, page=params["page"], limit=params["limit"])
        serializer = HistoryListItemSerializer(page, many=True)

        return Response(
            {
                "success": True,
                "message": "Prediction history retrieved successfully.",
                "data": serializer.data,
            }
        )


class HistoryDetailView(APIView):
    """GET/DELETE /api/v1/history/{prediction_id}/ per REST_API_SPEC.md
    section 6 ("Get Prediction Details" / "Delete Prediction").
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, prediction_id):
        prediction = _get_owned_prediction(request.user, prediction_id)
        if prediction is None:
            return _prediction_not_found()

        serializer = HistoryDetailSerializer(prediction, context={"request": request})
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
            "Prediction %s deleted via history endpoint by user %s",
            prediction_id,
            request.user.email,
        )

        return Response({"success": True, "message": "Prediction deleted successfully."})
