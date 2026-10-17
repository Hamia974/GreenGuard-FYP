from django.db import connection
from django.db.utils import OperationalError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """Liveness/readiness probe for orchestration (Docker healthcheck, CI,
    a future hosting platform) -- deliberately separate from the
    authenticated, business-facing `/api/v1/admin/system-health/` endpoint.
    Checks real database connectivity, not just process liveness.
    """
    try:
        connection.ensure_connection()
        database_status = "connected"
        healthy = True
    except OperationalError:
        database_status = "unreachable"
        healthy = False

    return Response(
        {"status": "ok" if healthy else "error", "database": database_status},
        status=200 if healthy else 503,
    )
