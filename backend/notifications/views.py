import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSerializer

logger = logging.getLogger("greenguard")


def _notification_not_found():
    return Response(
        {"success": False, "message": "Notification not found."},
        status=status.HTTP_404_NOT_FOUND,
    )


def _get_owned_notification(user, notification_id):
    """Same lookup shape as farms/history/predictions' local
    ``_get_owned_*`` helpers -- kept as a local copy, not a cross-app
    import, per the project's established app-isolation convention.
    """
    try:
        return Notification.objects.get(id=notification_id, user=user)
    except (Notification.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        return None


class NotificationListView(APIView):
    """GET /api/v1/notifications/ per REST_API_SPEC.md section 7.

    Returns all of the authenticated user's notifications, newest first.
    No pagination/search/filter query parameters -- section 7 documents
    none, per explicit product decision not to add any beyond the contract.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user)
        serializer = NotificationSerializer(notifications, many=True)
        return Response(
            {
                "success": True,
                "message": "Notifications retrieved successfully.",
                "data": serializer.data,
            }
        )


class NotificationMarkReadView(APIView):
    """PUT /api/v1/notifications/{notification_id}/read/ per
    REST_API_SPEC.md section 7. Owner-only -- no admin override, since
    section 7's Notification Rules define none.
    """

    permission_classes = [IsAuthenticated]

    def put(self, request, notification_id):
        notification = _get_owned_notification(request.user, notification_id)
        if notification is None:
            return _notification_not_found()

        notification.is_read = True
        notification.save(update_fields=["is_read", "updated_at"])

        return Response({"success": True, "message": "Notification marked as read."})


class NotificationDetailView(APIView):
    """DELETE /api/v1/notifications/{notification_id}/ per
    REST_API_SPEC.md section 7. Owner-only -- no admin override, since
    section 7's Notification Rules define none.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, notification_id):
        notification = _get_owned_notification(request.user, notification_id)
        if notification is None:
            return _notification_not_found()

        notification.delete()
        logger.info(
            "Notification %s deleted by user %s", notification_id, request.user.email
        )

        return Response({"success": True, "message": "Notification deleted successfully."})
