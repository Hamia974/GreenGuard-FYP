from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from predictions.validators import (
    validate_image_content_type,
    validate_image_format,
    validate_image_size,
)


class ProfileSerializer(serializers.Serializer):
    """Shapes the /api/v1/profile/ response per REST_API_SPEC.md section 4."""

    user_id = serializers.SerializerMethodField()
    full_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    role = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()
    is_verified = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    def get_user_id(self, user):
        return str(user.id)

    def get_role(self, user):
        return user.role.capitalize()

    def get_profile_image(self, user):
        if not user.profile_image:
            return None
        request = self.context.get("request")
        url = user.profile_image.url
        return request.build_absolute_uri(url) if request else url


class AccountDeletionSerializer(serializers.Serializer):
    """Validates DELETE /api/v1/profile/ — requires the current password.

    Per the approved account-deletion contract change, the frontend's
    "type DELETE to confirm" step is a UI safeguard only; the backend must
    independently verify the password server-side rather than trusting it.
    """

    current_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value


class ProfileUpdateSerializer(serializers.Serializer):
    """Validates PUT /api/v1/profile/ per REST_API_SPEC.md section 4."""

    full_name = serializers.CharField(max_length=201)
    profile_image = serializers.ImageField(required=False, allow_null=True)

    def validate_profile_image(self, value):
        """Same extension/MIME-type/size checks predictions/validators.py
        enforces for plant images -- reused here (not duplicated) so avatar
        uploads get the same file-upload security as plant-image uploads.
        The 224x224 minimum-resolution check is intentionally skipped: it's
        a plant-image-analysis quality rule, not a security control, and no
        doc specifies a minimum avatar resolution.
        """
        if value is None:
            return value
        try:
            validate_image_format(value)
            validate_image_content_type(value)
            validate_image_size(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message)
        return value

    def update(self, instance, validated_data):
        full_name = validated_data["full_name"].strip()
        parts = full_name.split(maxsplit=1)
        instance.first_name = parts[0] if parts else ""
        instance.last_name = parts[1] if len(parts) > 1 else ""

        if "profile_image" in validated_data:
            instance.profile_image = validated_data["profile_image"]

        instance.save(update_fields=["first_name", "last_name", "profile_image", "updated_at"])
        return instance
