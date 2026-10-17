import logging

from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.cookies import clear_auth_cookies

from .serializers import (
    AccountDeletionSerializer,
    ProfileSerializer,
    ProfileUpdateSerializer,
)

logger = logging.getLogger("greenguard")


class ProfileView(APIView):
    """GET/PUT/DELETE /api/v1/profile/ per REST_API_SPEC.md section 4."""

    permission_classes = [IsAuthenticated]
    # JSONParser supports the DELETE body (current_password); PUT keeps using
    # multipart for the profile_image upload.
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        serializer = ProfileSerializer(request.user, context={"request": request})
        return Response(
            {
                "success": True,
                "message": "Profile retrieved successfully.",
                "data": serializer.data,
            }
        )

    def put(self, request):
        serializer = ProfileUpdateSerializer(instance=request.user, data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "message": "Validation failed.",
                    "errors": serializer.errors,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        serializer.save()
        return Response(
            {"success": True, "message": "Profile updated successfully."}
        )

    def delete(self, request):
        serializer = AccountDeletionSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "message": "Validation failed.",
                    "errors": serializer.errors,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        logger.info("Deleting account for user %s", request.user.id)
        request.user.delete()
        response = Response(
            {"success": True, "message": "Account deleted successfully."}
        )
        clear_auth_cookies(response)
        return response
