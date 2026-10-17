from rest_framework.permissions import BasePermission

from users.models import User


class IsAdminRole(BasePermission):
    """Restricts access to users whose role is Admin, per REST_API_SPEC.md
    section 8 ("Only users with the Admin role are authorized to access
    these endpoints" / "Unauthorized users must receive HTTP 403 Forbidden").

    Always paired with IsAuthenticated (not a replacement for it) in each
    view's permission_classes, so an unauthenticated request still gets 401
    from JWTAuthentication/IsAuthenticated before this check ever runs --
    matching every other protected endpoint's convention in this project.
    """

    message = "Admin access required."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == User.Role.ADMIN)
