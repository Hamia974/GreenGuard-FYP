"""Weather Risk Module (Module 3) client.

Calls the real, delivered `ai/Weather_Module` FastAPI microservice -- see
docs/MODULE3_INTEGRATION_STATUS.md for the earlier blocked delivery
(`ai/weather.zip` containing only a video file) that this replaces, and
`ai/Weather_Module/Weather_Module/docs/INTEGRATION_GUIDE.md` for the
module's own documentation of this contract.

Per CLAUDE.md's AI Contract, this app treats the Weather Module as an
external service: it never recalculates `risk_assessment`/
`predicted_risk_assessment`, never renames or drops fields, and never
fabricates `forecast` data. It only calls the service, validates the
response has the shape callers can rely on, and forwards it unchanged.

This previously called NASA POWER directly and re-derived risk labels with
its own thresholds (see git history) -- removed because Module 3 has now
been delivered as a real, runnable service that already owns that logic.
"""

import copy
import logging
from datetime import datetime, timezone

import requests
from django.conf import settings

logger = logging.getLogger("greenguard")

PREDICT_PATH = "/predict"
HEALTH_PATH = "/health"

_REQUIRED_TOP_LEVEL_KEYS = {"farm_id", "timestamp", "weather", "risk_assessment"}
_REQUIRED_WEATHER_KEYS = {"temperature", "humidity", "rainfall_last_7_days_mm", "wind_speed"}
_REQUIRED_RISK_KEYS = {
    "fungal_disease_risk",
    "fungal_disease_reason",
    "heat_stress_risk",
    "heat_stress_reason",
    "drought_risk",
    "drought_reason",
}

# Fixed mock response, mirroring
# ai/Weather_Module/Weather_Module/samples/sample_response.json exactly (a
# real, live-captured response per that module's INTEGRATION_GUIDE.md) so
# mock and real shapes can never drift apart. Per CLAUDE.md's Mock
# Development Mode, used only while ENABLE_MOCK_AI=True -- farm_id and
# timestamp are overwritten per-request below, everything else is static,
# matching module2_client.py's precedent of a single
# fixed mock rather than a simulated model.
_MOCK_RESPONSE = {
    "farm_id": "unknown",
    "timestamp": "2026-09-01T22:39:35Z",
    "weather": {
        "temperature": 28.0,
        "humidity": 78.0,
        "rainfall_last_7_days_mm": 1.8,
        "wind_speed": 2.2,
    },
    "units": {
        "temperature": "celsius",
        "humidity": "percent",
        "rainfall_last_7_days_mm": "mm",
        "wind_speed": "m/s",
    },
    "risk_assessment": {
        "fungal_disease_risk": "Moderate",
        "fungal_disease_reason": (
            "Humidity is 78%, above the 65% threshold that raises fungal risk, though "
            "today's temperature/humidity combination isn't in the high-risk range."
        ),
        "heat_stress_risk": "Low",
        "heat_stress_reason": (
            "Current temperature (28.0°C) is at or below 35°C and no recent day averaged "
            "above that threshold."
        ),
        "drought_risk": "High",
        "drought_reason": "Only 1.8mm of rain fell in the last 7 days, below the 10mm high-drought threshold.",
    },
    "forecast": {
        "temperature": 31.5,
        "humidity": 63.5,
        "rainfall_mm": 2.0,
    },
    "predicted_risk_assessment": {
        "fungal_disease_risk": "Low",
        "fungal_disease_reason": "Humidity (63.5%) is below the 65% risk threshold and no day in the last 3 was fungal-conducive.",
        "heat_stress_risk": "Low",
        "heat_stress_reason": (
            "Current temperature (31.5°C) is at or below 35°C and no recent day averaged "
            "above that threshold."
        ),
        "drought_risk": "High",
        "drought_reason": "Only 3.8mm of rain fell in the last 7 days, below the 10mm high-drought threshold.",
    },
}


class WeatherServiceError(Exception):
    """Raised when the Weather Risk Module (Module 3) is unreachable or returns an unusable response."""


def _validate_response(result) -> None:
    """Sanity-checks the module's response has the fields callers rely on.

    `forecast` and `predicted_risk_assessment` are intentionally NOT
    required here -- the module documents both as nullable, best-effort
    fields (see INTEGRATION_GUIDE.md), so their absence is not a malformed
    response.
    """
    if not isinstance(result, dict) or not _REQUIRED_TOP_LEVEL_KEYS.issubset(result.keys()):
        raise WeatherServiceError("Weather service returned an unexpected response.")

    weather = result.get("weather")
    if not isinstance(weather, dict) or not _REQUIRED_WEATHER_KEYS.issubset(weather.keys()):
        raise WeatherServiceError("Weather service returned an unexpected response.")

    risk = result.get("risk_assessment")
    if not isinstance(risk, dict) or not _REQUIRED_RISK_KEYS.issubset(risk.keys()):
        raise WeatherServiceError("Weather service returned an unexpected response.")


def fetch_weather_for_coordinates(latitude, longitude, farm_id=None) -> dict:
    """Retrieve the Weather Risk Module's full report for a coordinate pair.

    Returns the module's exact JSON contract, unmodified: `farm_id`,
    `timestamp`, `weather`, `units`, `risk_assessment`, and the nullable
    `forecast` / `predicted_risk_assessment` (present only when the LSTM
    add-on produced a prediction). Callers must not assume the last two are
    present, and must never recompute or reinterpret `risk_assessment`.

    Raises WeatherServiceError if the module is unreachable, times out, or
    returns something that doesn't match its documented contract.
    """
    farm_id_str = str(farm_id) if farm_id is not None else "unknown"

    if settings.ENABLE_MOCK_AI:
        logger.info("Weather Module: ENABLE_MOCK_AI is on, returning fixed mock response.")
        mock = copy.deepcopy(_MOCK_RESPONSE)
        mock["farm_id"] = farm_id_str
        mock["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return mock

    url = f"{settings.WEATHER_MODULE_URL}{PREDICT_PATH}"
    payload = {"latitude": float(latitude), "longitude": float(longitude), "farm_id": farm_id_str}

    try:
        response = requests.post(
            url, json=payload, timeout=settings.WEATHER_MODULE_REQUEST_TIMEOUT_SECONDS
        )
    except requests.Timeout as exc:
        logger.error("Weather Module request timed out for farm_id=%s: %s", farm_id_str, exc)
        raise WeatherServiceError("Weather service is temporarily unavailable.") from exc
    except requests.RequestException as exc:
        logger.error("Weather Module request failed for farm_id=%s: %s", farm_id_str, exc)
        raise WeatherServiceError("Weather service is temporarily unavailable.") from exc

    if response.status_code >= 400:
        # The module's documented error contract is {"message": ...} for 500s
        # (weather provider unavailable / internal failure) and FastAPI's
        # default {"detail": [...]} for 422 validation errors -- logged for
        # debugging only, never forwarded verbatim to our own API consumers
        # (per CLAUDE.md: "never expose server errors").
        logger.error(
            "Weather Module returned HTTP %s for farm_id=%s: %s",
            response.status_code,
            farm_id_str,
            response.text[:500],
        )
        raise WeatherServiceError("Weather service is temporarily unavailable.")

    try:
        result = response.json()
    except ValueError as exc:
        logger.error("Weather Module returned malformed JSON for farm_id=%s: %s", farm_id_str, exc)
        raise WeatherServiceError("Weather service is temporarily unavailable.") from exc

    _validate_response(result)

    logger.info("Weather Module report retrieved for farm_id=%s", farm_id_str)
    return result


def to_dashboard_summary(weather_response: dict) -> dict:
    """Flattens the Weather Module's nested contract into the flat shape
    documented for GET /api/v1/dashboard/weather/ (REST_API_SPEC.md section
    5, unchanged since before this integration). Field access only -- no
    risk value is recalculated, reinterpreted, or renamed in meaning, only
    lifted out of the nested `weather`/`risk_assessment` objects.
    """
    weather = weather_response["weather"]
    risk = weather_response["risk_assessment"]
    return {
        "temperature": weather["temperature"],
        "humidity": weather["humidity"],
        "rainfall": weather["rainfall_last_7_days_mm"],
        "wind_speed": weather["wind_speed"],
        "fungal_disease_risk": risk["fungal_disease_risk"],
        "heat_stress_risk": risk["heat_stress_risk"],
        "drought_risk": risk["drought_risk"],
    }


def check_weather_module_health() -> bool:
    """Used by the Admin system-health / AI-monitoring probes. Returns
    True only on a real HTTP 200 from the module's own /health endpoint --
    never fabricated when ENABLE_MOCK_AI is on, so Mock Mode is reported
    honestly rather than as a live connection."""
    if settings.ENABLE_MOCK_AI:
        return False
    try:
        response = requests.get(
            f"{settings.WEATHER_MODULE_URL}{HEALTH_PATH}",
            timeout=settings.WEATHER_MODULE_HEALTH_TIMEOUT_SECONDS,
        )
        return response.status_code == 200
    except requests.RequestException:
        return False
