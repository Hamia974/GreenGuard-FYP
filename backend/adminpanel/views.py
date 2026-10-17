import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q
from django.db.models.fields.json import KT
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from predictions.models import Prediction
from users.models import User

from . import services
from .pagination import paginate
from .permissions import IsAdminRole
from .serializers import (
    AdminPredictionListItemSerializer,
    AdminUserDetailSerializer,
    AdminUserListItemSerializer,
    PredictionListQuerySerializer,
    UserListQuerySerializer,
    UserStatusUpdateSerializer,
)

logger = logging.getLogger("greenguard")


def _validation_failed(errors):
    return Response(
        {"success": False, "message": "Validation failed.", "errors": errors},
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


def _user_not_found():
    return Response(
        {"success": False, "message": "User not found."},
        status=status.HTTP_404_NOT_FOUND,
    )


def _prediction_not_found():
    return Response(
        {"success": False, "message": "Prediction not found."},
        status=status.HTTP_404_NOT_FOUND,
    )


def _get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except (User.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        return None


def _get_prediction(prediction_id):
    try:
        return Prediction.objects.select_related("user").get(id=prediction_id)
    except (Prediction.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        return None


class AdminDashboardView(APIView):
    """GET /api/v1/admin/dashboard/ per REST_API_SPEC.md section 8 ("Admin
    Dashboard"). Response shape follows that section's literal JSON example
    (total_users, active_users, total_predictions, system_status) -- the
    "Dashboard Includes" prose bullets list several fields (Total AI
    Requests, Recent Activities, Latest Notifications, ...) that never made
    it into the documented example and have no reliable backing data source
    in this schema, so they are not fabricated here, matching this
    project's established precedent of the literal example being the
    contract, not the surrounding prose.
    """

    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        return Response(
            {
                "success": True,
                "message": "Admin dashboard loaded successfully.",
                "data": {
                    "total_users": User.objects.count(),
                    "active_users": User.objects.filter(is_active=True).count(),
                    "total_predictions": Prediction.objects.count(),
                    "system_status": services.compute_overall_system_status(),
                },
            }
        )


class AdminUserListView(APIView):
    """GET /api/v1/admin/users/ per REST_API_SPEC.md section 8 ("Get All
    Users"): search, pagination, sorting, status filtering.
    """

    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        query = UserListQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return _validation_failed(query.errors)

        params = query.validated_data
        users = User.objects.all()

        if params["search"]:
            search = params["search"]
            users = users.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
            )

        if params["status"]:
            users = users.filter(is_active=(params["status"] == "Active"))

        sort = params["sort"]
        if sort == "oldest":
            users = users.order_by("created_at")
        elif sort == "name":
            users = users.order_by("first_name", "last_name")
        else:
            users = users.order_by("-created_at")

        page = paginate(users, page=params["page"], limit=params["limit"])
        serializer = AdminUserListItemSerializer(page, many=True)

        return Response(
            {
                "success": True,
                "message": "Users retrieved successfully.",
                "data": serializer.data,
            }
        )


class AdminUserDetailView(APIView):
    """GET/DELETE /api/v1/admin/users/{user_id}/ per REST_API_SPEC.md
    section 8 ("Get User Details" / "Delete User").
    """

    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request, user_id):
        user = _get_user(user_id)
        if user is None:
            return _user_not_found()

        serializer = AdminUserDetailSerializer(user, context={"request": request})
        return Response(
            {
                "success": True,
                "message": "User retrieved successfully.",
                "data": serializer.data,
            }
        )

    def delete(self, request, user_id):
        user = _get_user(user_id)
        if user is None:
            return _user_not_found()

        # Not part of the documented contract -- an explicit safety guard so
        # an admin can never lock themselves out of the Admin Dashboard by
        # deleting their own account through this endpoint (self-service
        # account deletion already exists at DELETE /api/v1/profile/, with
        # its own password confirmation).
        if user.id == request.user.id:
            return Response(
                {"success": False, "message": "You cannot delete your own account here."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(
            "User %s deleted via admin panel by %s", user.email, request.user.email
        )
        user.delete()
        return Response({"success": True, "message": "User deleted successfully."})


class AdminUserStatusView(APIView):
    """PUT /api/v1/admin/users/{user_id}/status/ per REST_API_SPEC.md
    section 8 ("Activate / Deactivate User").
    """

    permission_classes = [IsAuthenticated, IsAdminRole]

    def put(self, request, user_id):
        user = _get_user(user_id)
        if user is None:
            return _user_not_found()

        serializer = UserStatusUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_failed(serializer.errors)

        new_status = serializer.validated_data["status"]

        # Same self-lockout guard as AdminUserDetailView.delete -- not in
        # the documented contract, but deactivating one's own only Admin
        # account would leave the platform with no way back into the Admin
        # Dashboard.
        if user.id == request.user.id and new_status == "Inactive":
            return Response(
                {"success": False, "message": "You cannot deactivate your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = new_status == "Active"
        user.save(update_fields=["is_active", "updated_at"])
        logger.info(
            "User %s status set to %s via admin panel by %s",
            user.email,
            new_status,
            request.user.email,
        )

        return Response({"success": True, "message": "User status updated successfully."})


class AdminPredictionListView(APIView):
    """GET /api/v1/admin/predictions/ per REST_API_SPEC.md section 8 ("Get
    All Predictions"): search, pagination, filtering, sorting.
    """

    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        query = PredictionListQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return _validation_failed(query.errors)

        params = query.validated_data
        predictions = Prediction.objects.select_related("user")

        if params["search"]:
            search = params["search"]
            predictions = predictions.filter(
                Q(prediction_report__module1__prediction__display_name__icontains=search)
                | Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__email__icontains=search)
            )

        if params["status"]:
            predictions = predictions.filter(prediction_status=params["status"])

        predictions = predictions.order_by(
            "created_at" if params["sort"] == "oldest" else "-created_at"
        )

        page = paginate(predictions, page=params["page"], limit=params["limit"])
        serializer = AdminPredictionListItemSerializer(page, many=True)

        return Response(
            {
                "success": True,
                "message": "Predictions retrieved successfully.",
                "data": serializer.data,
            }
        )


class AdminPredictionDetailView(APIView):
    """DELETE /api/v1/admin/predictions/{prediction_id}/ per
    REST_API_SPEC.md section 8 ("Delete Prediction").
    """

    permission_classes = [IsAuthenticated, IsAdminRole]

    def delete(self, request, prediction_id):
        prediction = _get_prediction(prediction_id)
        if prediction is None:
            return _prediction_not_found()

        logger.info(
            "Prediction %s deleted via admin panel by %s",
            prediction_id,
            request.user.email,
        )
        prediction.delete()
        return Response({"success": True, "message": "Prediction deleted successfully."})


class AdminAIMonitoringView(APIView):
    """GET /api/v1/admin/ai-monitoring/ per REST_API_SPEC.md section 8 ("AI
    Monitoring"). Read-only, per that section's "Admin Rules" ("AI
    monitoring endpoints are read-only.").
    """

    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        return Response(
            {
                "success": True,
                "message": "AI monitoring loaded successfully.",
                "data": services.get_ai_module_status(),
            }
        )


class AdminSystemHealthView(APIView):
    """GET /api/v1/admin/system-health/ per REST_API_SPEC.md section 8
    ("System Health"). Exposes only coarse Healthy/Unhealthy/Connected/
    Unreachable labels -- per that section's "Admin Rules" ("System health
    endpoints do not expose sensitive server information."), no host names,
    stack traces, credentials, or internal config values are ever returned.
    """

    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        return Response(
            {
                "success": True,
                "message": "System health retrieved successfully.",
                "data": services.get_system_health(),
            }
        )


class AdminStatisticsView(APIView):
    """GET /api/v1/admin/statistics/ per REST_API_SPEC.md section 8
    ("Platform Statistics"). Follows that section's literal JSON example
    (total_users, total_predictions, active_users, most_detected_disease,
    most_recommended_crop) -- most_recommended_crop has no backing data
    source anywhere in the current schema (Module 2 records a soil-health
    check for a crop the farmer already picked, it does not recommend one;
    see module2.models.Module2Analysis), so it always returns null rather
    than being fabricated, matching the identical, already-established
    precedent for `recommended_crop` in history.serializers.HistoryListItemSerializer.
    """

    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        # Counted from Module 1's own confident, non-healthy results only --
        # uncertain results (prediction: null) and healthy classes are not
        # a detected disease.
        most_detected = (
            Prediction.objects.filter(
                prediction_report__module1__prediction__is_healthy=False
            )
            .annotate(disease=KT("prediction_report__module1__prediction__display_name"))
            .values("disease")
            .annotate(count=Count("id"))
            .order_by("-count")
            .first()
        )

        return Response(
            {
                "success": True,
                "message": "Statistics retrieved successfully.",
                "data": {
                    "total_users": User.objects.count(),
                    "total_predictions": Prediction.objects.count(),
                    "active_users": User.objects.filter(is_active=True).count(),
                    "most_detected_disease": (
                        most_detected["disease"] if most_detected else None
                    ),
                    "most_recommended_crop": None,
                },
            }
        )
