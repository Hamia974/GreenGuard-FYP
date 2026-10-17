from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.utils import get_md5_hash_password

from users.models import User


class RegisterSerializer(serializers.Serializer):
    """Validates POST /api/v1/auth/register/ per REST_API_SPEC.md."""

    full_name = serializers.CharField(max_length=201)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Email already exists.")
        return email

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": ["Passwords must match."]}
            )
        return attrs

    def create(self, validated_data):
        full_name = validated_data["full_name"].strip()
        parts = full_name.split(maxsplit=1)
        first_name = parts[0] if parts else ""
        last_name = parts[1] if len(parts) > 1 else ""

        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=first_name,
            last_name=last_name,
        )


class LoginSerializer(serializers.Serializer):
    """Validates POST /api/v1/auth/login/ per REST_API_SPEC.md."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    # Optional; omitted means a persistent session, matching the behaviour
    # before "Remember me" was wired up.
    remember_me = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        user = authenticate(
            self.context["request"],
            username=attrs["email"],
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError("Invalid email or password.")
        attrs["user"] = user
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    """Validates POST /api/v1/auth/forgot-password/ per REST_API_SPEC.md."""

    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    """Validates POST /api/v1/auth/reset-password/ per REST_API_SPEC.md."""

    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": ["Passwords must match."]}
            )
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """Validates POST /api/v1/auth/change-password/ per REST_API_SPEC.md."""

    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        validate_password(value, user=self.context["request"].user)
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": ["Passwords must match."]}
            )
        return attrs


class VerifyEmailSerializer(serializers.Serializer):
    """Validates POST /api/v1/auth/verify-email/."""

    token = serializers.CharField()


class PasswordBoundTokenRefreshSerializer(TokenRefreshSerializer):
    """Simple JWT's refresh serializer, plus the CHECK_REVOKE_TOKEN password
    binding that Simple JWT only enforces on access tokens.

    Password change/reset already blacklist every refresh token, but a
    password can also change without that (an admin, ``changepassword``, or
    a hasher upgrade on login). Without this check such a refresh token
    would keep minting access tokens that are rejected on first use.
    """

    def validate(self, attrs):
        refresh = self.token_class(attrs["refresh"])
        user = User.objects.filter(
            **{jwt_settings.USER_ID_FIELD: refresh.payload.get(jwt_settings.USER_ID_CLAIM)}
        ).first()
        if user is not None and refresh.payload.get(
            jwt_settings.REVOKE_TOKEN_CLAIM
        ) != get_md5_hash_password(user.password):
            raise TokenError("Password changed since the token was issued.")
        return super().validate(attrs)
