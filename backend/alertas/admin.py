from django.contrib import admin

from .models import Alerta


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    """Panel de administración (Semana 15): solo consulta — las alertas
    las crea y cierra el sistema y la API no ofrece escritura."""

    list_display = (
        "id",
        "tipo",
        "productor",
        "campania",
        "creada_en",
        "atendida",
        "atendida_en",
    )
    list_filter = ("tipo", "atendida")
    search_fields = ("productor__codigo", "productor__nombres", "productor__apellidos")
    autocomplete_fields = ()
    fields = (
        "id",
        "productor",
        "campania",
        "incidencia",
        "tipo",
        "mensaje",
        "creada_en",
        "atendida",
        "atendida_por",
        "atendida_en",
        "nota_atencion",
    )
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
