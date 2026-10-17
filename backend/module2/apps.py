from django.apps import AppConfig


class Module2Config(AppConfig):
    """Module 2 — Soil & Nutrient Health Check, per REST_API_SPEC.md section 8A.

    Standalone public endpoint, independent of the Plant Image Prediction
    workflow (predictions app) -- the request/response contract of
    POST /api/v1/module2/analyze/ is frozen. Owns request validation,
    farm-ownership checks, resolving weather from the existing Phase 5
    weather service, and combining that into the payload sent to
    ai_services.module2_client. Each successful run is additionally
    persisted as a Module2Analysis row (see DATABASE_SPECIFICATION.md
    section 6A) as an internal side effect only -- this does not change
    the HTTP response returned to the frontend.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "module2"
