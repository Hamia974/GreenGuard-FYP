"""System-health / AI-monitoring probes for the Admin Dashboard.

Per CLAUDE.md's AI Contract: never invent AI health metrics or pretend real
inference is happening. ENABLE_MOCK_AI's state is reported honestly ("Mock
Mode"); when it is off, each real AI module is probed through its own
documented `GET /health` endpoint -- Module 1 (Disease Detection) and
Module 2 (Soil & Nutrient) are the live deployed services, Module 3 (Weather
Risk) the local service. Module 4 is the application-level report, not a
service, so it is never probed or reported as an outage.
"""

import logging

from django.conf import settings
from django.db import connection
from django.db.utils import OperationalError

from ai_services.disease_module_client import check_disease_module_health
from ai_services.module2_client import check_stress_module_health
from weather.services import check_weather_module_health

logger = logging.getLogger("greenguard")

# Module 4 is the in-app integration/report layer (it runs no model and is
# not a separate service), so its monitoring row states that rather than a
# reachability result.
INTEGRATION_LAYER_STATUS = "Not used — integration layer"


def check_database() -> str:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return "Healthy"
    except OperationalError:
        logger.exception("Admin system-health: database check failed.")
        return "Unhealthy"


def check_image_module() -> str:
    """Probes the live Module 1 (Disease Detection) service's own
    `GET /health` -- see ai_services/disease_module_client.py. Same "Mock
    Mode" vs. "Connected"/"Unreachable" convention as check_weather_api()."""
    if settings.ENABLE_MOCK_AI:
        return "Mock Mode"
    return "Connected" if check_disease_module_health() else "Unreachable"


def check_ai_services() -> str:
    """Overall status of the two deployed AI services (Module 1 and Module
    2) for System Health's `ai_services` field. Module 3 is reported
    separately as `weather_api`. Reachability only -- no inference call."""
    if settings.ENABLE_MOCK_AI:
        return "Mock Mode"
    reachable = [check_disease_module_health(), check_stress_module_health()]
    if all(reachable):
        return "Healthy"
    if any(reachable):
        return "Degraded"
    return "Unreachable"


def check_weather_api() -> str:
    """Probes the real Module 3 (Weather Risk Engine) microservice's own
    `GET /health` -- see weather/services.py. Reports "Mock Mode" honestly
    when ENABLE_MOCK_AI is on, matching check_ai_services()'s convention,
    rather than claiming a live connection that isn't happening."""
    if settings.ENABLE_MOCK_AI:
        return "Mock Mode"
    return "Connected" if check_weather_module_health() else "Unreachable"


def check_soil_module() -> str:
    """Probes the real Module 2 (Stress Module) microservice's own
    `GET /health` -- see ai_services/module2_client.py. Same "Mock Mode" vs.
    "Connected"/"Unreachable" convention as check_weather_api()."""
    if settings.ENABLE_MOCK_AI:
        return "Mock Mode"
    return "Connected" if check_stress_module_health() else "Unreachable"


def get_ai_module_status() -> dict:
    """AI Monitoring per REST_API_SPEC.md section 8: one status per module.

    Modules 1-3 are each probed via their own /health endpoint.
    `fusion_module` keeps its documented key but reports Module 4 as the
    integration layer it now is -- there is no Fusion service to probe.
    """
    return {
        "image_module": check_image_module(),
        "soil_module": check_soil_module(),
        "weather_module": check_weather_api(),
        "fusion_module": INTEGRATION_LAYER_STATUS,
    }


def get_system_health() -> dict:
    """System Health per REST_API_SPEC.md section 8's documented response
    shape (backend/database/ai_services/weather_api only -- the "Storage"
    bullet in that section's prose has no field in the actual JSON example,
    so it is not fabricated here, matching this project's established
    precedent of following the literal example over undocumented prose).
    """
    return {
        "backend": "Healthy",
        "database": check_database(),
        "ai_services": check_ai_services(),
        "weather_api": check_weather_api(),
    }


def compute_overall_system_status() -> str:
    """Compact status for the Admin Dashboard overview's `system_status`
    field. "Healthy" only when the backend's own database is reachable --
    AI/weather reachability intentionally excluded here since Mock Mode is
    an expected, non-degraded state, not a fault.
    """
    return "Healthy" if check_database() == "Healthy" else "Degraded"
