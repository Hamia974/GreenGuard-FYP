from django.apps import AppConfig


class AiServicesConfig(AppConfig):
    """Communicates with externally deployed AI microservices.

    Per GREEN_GUARD_SYSTEM_SPECIFICATION_V2.md section 28.6: this app does
    not perform AI inference itself -- it only calls the deployed AI APIs
    (or, until they're deployed, returns fixed mock responses per
    CLAUDE.md's Mock Development Mode). weather/ is a separate app for the
    same reason -- it calls the real, delivered ai/Weather_Module
    microservice (Open-Meteo-backed) rather than living inside this app.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "ai_services"
