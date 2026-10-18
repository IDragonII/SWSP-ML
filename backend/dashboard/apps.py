from django.apps import AppConfig


class DashboardConfig(AppConfig):
    """App de la Semana 16 (HU-133..HU-140): panel de indicadores de
    solo lectura, sin modelos ni migraciones propias."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "dashboard"
    verbose_name = "Dashboard"
