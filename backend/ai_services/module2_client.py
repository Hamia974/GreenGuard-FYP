"""Client for the AI team's Module 2 ("Stress Module") -- the real, delivered
FastAPI microservice at `ai/Stress_Module` (Module 2A nutrient-risk ML +
Module 2B pH/moisture/light rules, combined by the module's own internal
orchestrator). See `ai/Stress_Module/docs/INTEGRATION_GUIDE.md` and
`Module2_Orchestrator_Spec.md` for the module's own documentation of this
contract, and REST_API_SPEC.md's "AI Module 2" section for the internal
service contract as consumed here.

Module 2A and Module 2B are internal to that service -- Django makes exactly
one HTTP call to its single public endpoint, `POST /predict`, and returns the
response untouched. Per CLAUDE.md's AI Contract: never calculate nutrient
risk or soil health score here, never modify AI output, never rename fields.

Module 2, like Module 1 and Module 3, has its own dedicated service URL
(`STRESS_MODULE_URL`) because it is a real, independently deployed service.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger("greenguard")

PREDICT_PATH = "/predict"
HEALTH_PATH = "/health"

# Fixed mock response, matching ai/Stress_Module/samples/sample_response.json's
# shape (module version 1.2.0 -- module2a with input_typicality + model_version,
# top-level recommendation_notes + module2a_model_version). Per CLAUDE.md, mock
# responses must be "fixed mock JSON responses" that match the documented
# contract -- not a simulated/heuristic model -- so this is intentionally
# static rather than computed from the request payload. model_version values
# are deliberately "-mock" suffixed so mock output can never be mistaken for a
# real inference result.
_MOCK_RESPONSE = {
    "crop_supported": True,
    "module2a": {
        "nitrogen_risk": {"level": "high", "confidence": 0.82},
        "phosphorus_risk": {"level": "medium", "confidence": 0.46},
        "potassium_risk": {"level": "low", "confidence": 0.71},
        "magnesium_risk": {"level": "medium", "confidence": 0.48},
        "zinc_risk": {"level": "low", "confidence": 0.66},
        "boron_risk": {"level": "medium", "confidence": 0.44},
        "overall_nutrient_health": "moderate",
        "input_typicality": {"anomaly_score": 0.07, "flag": "typical"},
        "model_version": "module2a-v5-mock",
    },
    "module2b": {
        "ph": {
            "current": 5.1,
            "ideal_range": [6.5, 7.0],
            "gap": 1.4,
            "status": "critical",
            "nutrient_lockout_note": (
                "This pH severely limits potassium, nitrogen, phosphorus, calcium, "
                "and magnesium, and can raise aluminum/manganese to toxic levels. "
                "Fertilizer alone will not fix this — consider liming."
            ),
        },
        "soil_moisture": {"current": 62, "ideal_range": [50, 75], "gap": 0, "status": "ok"},
        "light": {"current": 28000, "ideal_range": [25000, None], "gap": 0, "status": "ok"},
        "crop_supported": True,
    },
    "overall_soil_health_score": 52.5,
    "overall_soil_health_label": "moderate",
    "recommendation_notes": {
        "headline": "Nitrogen needs attention first.",
        "needs_attention": [
            {
                "nutrient": "Nitrogen",
                "level": "high",
                "confidence_pct": 82,
                "confidence_text": "82% confident — strong match",
                "why": "sandy soil (nutrients wash out faster), no fertilizer applied",
            },
            {
                "nutrient": "Phosphorus",
                "level": "medium",
                "confidence_pct": 46,
                "confidence_text": "46% confident — based on limited signs",
                "why": "no fertilizer applied",
            },
            {
                "nutrient": "Magnesium",
                "level": "medium",
                "confidence_pct": 48,
                "confidence_text": "48% confident — based on limited signs",
                "why": "sandy soil (nutrients wash out faster)",
            },
            {
                "nutrient": "Boron",
                "level": "medium",
                "confidence_pct": 44,
                "confidence_text": "44% confident — based on limited signs",
                "why": "sandy soil (nutrients wash out faster)",
            },
        ],
        "looking_fine": [
            {
                "nutrient": "Potassium",
                "level": "low",
                "confidence_pct": 71,
                "confidence_text": "71% confident — likely",
            },
            {
                "nutrient": "Zinc",
                "level": "low",
                "confidence_pct": 66,
                "confidence_text": "66% confident — likely",
            },
        ],
        "caveat": (
            "This advice is based on your answers and soil-meter readings. "
            "A soil lab test can add exact nutrient levels if you need them."
        ),
        "soil_condition_note": (
            "This pH severely limits potassium, nitrogen, phosphorus, calcium, "
            "and magnesium, and can raise aluminum/manganese to toxic levels. "
            "Fertilizer alone will not fix this — consider liming."
        ),
    },
    "model_version": "module2-orchestrator-mock",
    "module2a_model_version": "module2a-v5-mock",
}

# Present on every response (supported or unsupported crop) per
# module2_field_options.json -> module2_orchestrator_output_schema.
_REQUIRED_RESPONSE_KEYS = {
    "crop_supported",
    "module2a",
    "module2b",
    "overall_soil_health_score",
    "overall_soil_health_label",
    "recommendation_notes",
}
# Only documented as present when crop_supported is true.
_REQUIRED_SUPPORTED_KEYS = {"model_version", "module2a_model_version"}


class Module2ServiceError(Exception):
    """Raised when the Module 2 (Stress Module) service is unreachable or returns an unusable response."""


def call_module2_orchestrator(payload: dict) -> dict:
    """Call the Module 2 (Stress Module) service with a farmer questionnaire + resolved weather payload.

    Callers must only invoke this for crops already confirmed
    trained-and-supported -- module2.views short-circuits unsupported crops
    before reaching this point, per REST_API_SPEC.md Section 8A's
    recommended handling (avoids an unnecessary AI call).

    Raises Module2ServiceError on connection failure, timeout, a non-2xx
    response (422 validation / 503 model-unavailable / 500 internal -- see
    the module's documented error contract), malformed JSON, or a response
    missing the documented top-level fields. Every failure is logged with
    enough detail to diagnose which of these occurred; only a single generic
    message is ever raised to the caller, matching this project's existing
    external API contract (REST_API_SPEC.md: 500 "AI module is currently
    unavailable" for any Orchestrator failure) -- CLAUDE.md forbids exposing
    raw server errors or internal detail to the farmer.
    """
    if settings.ENABLE_MOCK_AI:
        logger.info("Module 2 (Stress Module): ENABLE_MOCK_AI is on, returning fixed mock response.")
        return dict(_MOCK_RESPONSE)

    url = f"{settings.STRESS_MODULE_URL}{PREDICT_PATH}"
    try:
        response = requests.post(url, json=payload, timeout=settings.STRESS_MODULE_REQUEST_TIMEOUT_SECONDS)
    except requests.Timeout as exc:
        logger.error("Stress Module request timed out: %s", exc)
        raise Module2ServiceError("Module 2 (Stress Module) is unavailable.") from exc
    except requests.RequestException as exc:
        logger.error("Stress Module request failed: %s", exc)
        raise Module2ServiceError("Module 2 (Stress Module) is unavailable.") from exc

    if response.status_code >= 400:
        # The module's documented error contract (INTEGRATION_GUIDE.md): 422
        # validation errors use FastAPI's default {"detail": [...]}; 503
        # (model artifacts unavailable) and 500 (internal failure) both use
        # {"message": ...}. Logged only for diagnosis -- never forwarded
        # verbatim to farmers, per CLAUDE.md ("never expose server errors").
        # A 422 here would mean Django's own validation (module2/serializers.py)
        # diverged from the module's -- worth surfacing in logs, not retried.
        logger.error(
            "Stress Module returned HTTP %s: %s", response.status_code, response.text[:500]
        )
        raise Module2ServiceError("Module 2 (Stress Module) returned an error.")

    try:
        result = response.json()
    except ValueError as exc:
        logger.error("Stress Module returned malformed JSON: %s", exc)
        raise Module2ServiceError("Module 2 (Stress Module) returned an unexpected response.") from exc

    if not isinstance(result, dict) or not _REQUIRED_RESPONSE_KEYS.issubset(result.keys()):
        logger.error("Stress Module returned an unexpected response shape: %r", result)
        raise Module2ServiceError("Module 2 (Stress Module) returned an unexpected response.")

    if result.get("crop_supported") and not _REQUIRED_SUPPORTED_KEYS.issubset(result.keys()):
        logger.error("Stress Module supported-crop response missing version fields: %r", result)
        raise Module2ServiceError("Module 2 (Stress Module) returned an unexpected response.")

    return result


def check_stress_module_health() -> bool:
    """Used by the Admin system-health / AI-monitoring probes. Returns True
    only on a real HTTP 200 from the module's own /health endpoint -- never
    fabricated when ENABLE_MOCK_AI is on, so Mock Mode is reported honestly
    rather than as a live connection (matching weather/services.py's
    check_weather_module_health() precedent)."""
    if settings.ENABLE_MOCK_AI:
        return False
    try:
        response = requests.get(
            f"{settings.STRESS_MODULE_URL}{HEALTH_PATH}",
            timeout=settings.STRESS_MODULE_HEALTH_TIMEOUT_SECONDS,
        )
        return response.status_code == 200
    except requests.RequestException:
        return False
