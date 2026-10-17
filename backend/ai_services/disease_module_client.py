"""Client for the AI team's Module 1 ("Disease Module") -- the real, live
FastAPI service documented in `ai/API_CONTRACT.md`. Deployed independently
(currently on Render), not part of this repo -- Django makes exactly one
call per uploaded leaf image and returns the response untouched.

This is the only Module 1 client used at runtime: by the standalone Disease
Check (`POST /api/v1/module1/analyze/`, `module1/views.py`) and by Quick Scan
(`POST /api/v1/predictions/analyze/`, `predictions/views.py`), which stores
the response verbatim as its report's `module1` section.

Per CLAUDE.md's AI Contract: never modify AI outputs, never rename JSON
fields, never calculate confidence, never infer predictions. This client is
a transport layer only.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger("greenguard")

PREDICT_PATH = "/v1/predict"
HEALTH_PATH = "/health"

# Per ai/API_CONTRACT.md's "POST /v1/predict" table -- the model covers only
# these 7 crops. Kept here (not fetched from GET /v1/classes) because the
# contract documents this exact list as the valid `crop` request values,
# distinct from the 38-class disease list that GET /v1/classes exists to
# avoid hard-coding (see that endpoint's section: "Do NOT hard-code the old
# screenshot list... use GET /v1/classes instead"). This app never needs
# per-class metadata (display names/is_healthy all come back inline on
# every prediction/top3 entry), so GET /v1/classes has no caller here.
SUPPORTED_CROPS = ["wheat", "rice", "cotton", "maize", "sugarcane", "tomato", "potato"]

# Error codes the module documents as retried once (cold start / transient
# model load), per "Integration notes": "Use a 60 s timeout, retry once on
# timeout or 503." Every other documented error code (400s, 401, 413, 422,
# 500) is not retried.
_RETRYABLE_STATUS_CODES = {503}


class DiseaseModuleServiceError(Exception):
    """Raised when the Disease Module (Module 1 live service) is unreachable
    or returns an unusable response.

    `http_status` / `error_code` / `upstream_message` mirror the module's own
    documented error contract (`ai/API_CONTRACT.md` "Errors" section) when
    known, so `module1/views.py` can translate them into the right HTTP
    status and a friendly, non-technical message -- never forwarding a raw
    server error to the farmer, per CLAUDE.md. All three are None for
    network-level failures (timeout, connection error, malformed response)
    that never got a documented error body.
    """

    def __init__(self, message, *, http_status=None, error_code=None, upstream_message=None):
        super().__init__(message)
        self.http_status = http_status
        self.error_code = error_code
        self.upstream_message = upstream_message


# Fixed mock response, matching ai/API_CONTRACT.md's "confident" example
# exactly (aside from model_version). Per CLAUDE.md, mock responses must be
# "fixed mock JSON responses" that match the documented contract -- not a
# simulated/heuristic model -- so this is intentionally static rather than
# computed from the uploaded image, matching module2_client.py's
# precedent of a single fixed mock. The "uncertain"
# shape (status="uncertain", prediction=null) is exercised in tests via the
# real-service (non-mock) code path instead, proving the client passes it
# through unchanged either way.
_MOCK_RESPONSE = {
    "status": "ok",
    "farm_id": None,
    "timestamp": "2026-09-26T04:55:12Z",
    "prediction": {
        "class_id": "wheat_yellow_rust",
        "crop": "wheat",
        "disease": "yellow_rust",
        "display_name": "Yellow Rust",
        "is_healthy": False,
        "confidence": 0.8812,
    },
    "top3": [
        {
            "class_id": "wheat_yellow_rust",
            "crop": "wheat",
            "disease": "yellow_rust",
            "display_name": "Yellow Rust",
            "is_healthy": False,
            "confidence": 0.8812,
        },
        {
            "class_id": "wheat_brown_rust",
            "crop": "wheat",
            "disease": "brown_rust",
            "display_name": "Brown Rust",
            "is_healthy": False,
            "confidence": 0.0713,
        },
        {
            "class_id": "wheat_septoria",
            "crop": "wheat",
            "disease": "septoria",
            "display_name": "Septoria",
            "is_healthy": False,
            "confidence": 0.0208,
        },
    ],
    "crop_source": "user",
    "detected_crop": "wheat",
    "warnings": [],
    "message": None,
    "model_version": "efficientnet_b0-1.0-mock",
    "inference_ms": 14.2,
    "request_id": "mock00000000",
}

_REQUIRED_RESPONSE_KEYS = {
    "status",
    "farm_id",
    "timestamp",
    "prediction",
    "top3",
    "crop_source",
    "detected_crop",
    "warnings",
    "message",
    "model_version",
    "request_id",
}


def _build_files(image_file):
    """Reads the upload into memory once and returns a fresh `files` dict
    usable for both the initial attempt and a retry -- passing the live
    `image_file` object straight to `requests` would leave its stream
    exhausted (position at EOF) on a second attempt.
    """
    image_file.seek(0)
    image_bytes = image_file.read()
    image_file.seek(0)
    filename = getattr(image_file, "name", "leaf.jpg") or "leaf.jpg"
    content_type = getattr(image_file, "content_type", None) or "application/octet-stream"
    return {"image": (filename, image_bytes, content_type)}


def _parse_error_body(response):
    """Best-effort parse of the module's documented error shape
    (`{"status": "error", "error": {"code": ..., "message": ...}, "request_id": ...}`).
    Falls back to (None, None) if the body doesn't match -- callers must not
    assume either value is present.
    """
    try:
        body = response.json()
    except ValueError:
        return None, None
    if not isinstance(body, dict):
        return None, None
    error = body.get("error")
    if isinstance(error, dict):
        return error.get("code"), error.get("message")
    return None, None


def call_disease_module_predict(image_file, *, crop=None, farm_id=None) -> dict:
    """Send an uploaded leaf photo to the live Module 1 (Disease) service.

    `crop` and `farm_id` are forwarded exactly as given (or omitted
    entirely) -- per ai/API_CONTRACT.md both are optional multipart fields,
    never invented here when the caller has none. `crop` should be sent
    "whenever the farmer has chosen one" (the contract: "accuracy is
    materially worse without it") but this function does not enforce or
    default it.

    Returns the module's exact JSON response, unmodified, whether
    `status` is "ok" (a `prediction` is present) or "uncertain"
    (`prediction` is null and `top3` is the fallback result list -- see the
    contract's "Render top3 on EVERY response" section).

    Raises DiseaseModuleServiceError on network failure, an HTTP error
    response (with `http_status`/`error_code`/`upstream_message` populated
    from the module's documented error contract when available), or a
    response missing the documented top-level fields.
    """
    if settings.ENABLE_MOCK_AI:
        logger.info("Disease Module (Module 1): ENABLE_MOCK_AI is on, returning fixed mock response.")
        mock = dict(_MOCK_RESPONSE)
        mock["farm_id"] = str(farm_id) if farm_id is not None else None
        return mock

    url = f"{settings.DISEASE_MODULE_URL}{PREDICT_PATH}"
    headers = {"X-API-Key": settings.GREENGUARD_API_KEY}
    data = {}
    if crop:
        data["crop"] = crop
    if farm_id is not None:
        data["farm_id"] = str(farm_id)

    attempts_left = 2  # one initial attempt + one retry, per the contract
    last_exc = None
    while attempts_left > 0:
        attempts_left -= 1
        files = _build_files(image_file)
        try:
            response = requests.post(
                url,
                headers=headers,
                files=files,
                data=data,
                timeout=settings.DISEASE_MODULE_REQUEST_TIMEOUT_SECONDS,
            )
        except requests.Timeout as exc:
            last_exc = exc
            logger.warning("Disease Module request timed out (attempts_left=%s): %s", attempts_left, exc)
            if attempts_left > 0:
                continue
            logger.error("Disease Module request timed out after retry: %s", exc)
            raise DiseaseModuleServiceError("Disease Module is unavailable.") from exc
        except requests.RequestException as exc:
            logger.error("Disease Module request failed: %s", exc)
            raise DiseaseModuleServiceError("Disease Module is unavailable.") from exc

        if response.status_code in _RETRYABLE_STATUS_CODES and attempts_left > 0:
            logger.warning(
                "Disease Module returned HTTP %s, retrying once.", response.status_code
            )
            continue

        break
    else:  # pragma: no cover -- defensive; loop always breaks or raises above
        raise DiseaseModuleServiceError("Disease Module is unavailable.") from last_exc

    if response.status_code >= 400:
        error_code, upstream_message = _parse_error_body(response)
        logger.error(
            "Disease Module returned HTTP %s (code=%s): %s",
            response.status_code,
            error_code,
            response.text[:500],
        )
        raise DiseaseModuleServiceError(
            "Disease Module returned an error.",
            http_status=response.status_code,
            error_code=error_code,
            upstream_message=upstream_message,
        )

    try:
        result = response.json()
    except ValueError as exc:
        logger.error("Disease Module returned malformed JSON: %s", exc)
        raise DiseaseModuleServiceError("Disease Module returned an unexpected response.") from exc

    if not isinstance(result, dict) or not _REQUIRED_RESPONSE_KEYS.issubset(result.keys()):
        logger.error("Disease Module returned an unexpected response shape: %r", result)
        raise DiseaseModuleServiceError("Disease Module returned an unexpected response.")

    if result["status"] == "ok" and result.get("prediction") is None:
        logger.error("Disease Module status=ok but prediction is null: %r", result)
        raise DiseaseModuleServiceError("Disease Module returned an unexpected response.")

    return result


def check_disease_module_health() -> bool:
    """Used by the Admin system-health / AI-monitoring probes. Returns True
    only on a real HTTP 200 from the module's own /health endpoint -- never
    fabricated when ENABLE_MOCK_AI is on, so Mock Mode is reported honestly
    rather than as a live connection (matching weather/services.py's and
    module2_client.py's check_*_health() precedent). No X-API-Key is sent --
    per the contract, /health "No key required."
    """
    if settings.ENABLE_MOCK_AI:
        return False
    try:
        response = requests.get(
            f"{settings.DISEASE_MODULE_URL}{HEALTH_PATH}",
            timeout=settings.DISEASE_MODULE_HEALTH_TIMEOUT_SECONDS,
        )
        return response.status_code == 200
    except requests.RequestException:
        return False
