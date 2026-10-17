from django.apps import AppConfig


class Module1Config(AppConfig):
    """Module 1 -- live Disease Detection, per ai/API_CONTRACT.md.

    Standalone public endpoint. The same live service (via
    ai_services.disease_module_client) also supplies the `module1` section
    of a Quick Scan analysis (`predictions` app). The request/
    response contract of POST /api/v1/module1/analyze/ mirrors the live
    Disease Module's own contract as closely as this backend's standard
    envelope allows: the module's full JSON response is forwarded verbatim
    under `data`, never modified. Owns request validation, farm-ownership
    checks, and calling ai_services.disease_module_client. Each successful
    run is additionally persisted as a DiseaseCheck row as an internal side
    effect only -- this does not change the HTTP response returned to the
    frontend.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "module1"
