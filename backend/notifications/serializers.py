from rest_framework import serializers


class NotificationSerializer(serializers.Serializer):
    """Shapes one notification per REST_API_SPEC.md section 7's documented
    "Get Notifications" example: {notification_id, title, message, is_read,
    created_at}.

    ``notification_type`` is a stored DATABASE_SPECIFICATION.md section 6
    column but is not part of section 7's response example, so per explicit
    product decision it is left out of the API-facing shape here -- matching
    the documented contract literally rather than adding an undocumented
    field, the same precedent Phase 7 used for its list-item contract.
    """

    notification_id = serializers.SerializerMethodField()
    title = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)
    is_read = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    def get_notification_id(self, notification):
        return str(notification.id)
