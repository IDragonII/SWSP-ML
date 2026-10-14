from django.contrib import admin

from .models import Actividad, UsoRecurso


@admin.register(Actividad)
class ActividadAdmin(admin.ModelAdmin):
    list_display = (
        "fecha",
        "tipo_actividad",
        "campania",
        "horas",
        "costo",
        "anulada",
    )
    list_filter = ("anulada", "tipo_actividad", "campania")
    search_fields = (
        "metodo",
        "observaciones",
        "campania__parcela__codigo",
        "campania__parcela__productor__apellidos",
        "campania__parcela__productor__nombres",
    )
    date_hierarchy = "fecha"
    # Anulación solo desde la API: en el admin se ve, no se toca
    # (decisión de la Semana 7; el admin es de consulta y trazabilidad).
    readonly_fields = (
        "anulada",
        "motivo_anulacion",
        "registrado_por",
        "creado_en",
        "actualizado_en",
    )
    raw_id_fields = ("campania",)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.registrado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(UsoRecurso)
class UsoRecursoAdmin(admin.ModelAdmin):
    """Semana 9: consulta y trazabilidad; la anulación solo desde la API."""

    list_display = (
        "fecha",
        "recurso",
        "campania",
        "cantidad",
        "unidad",
        "cantidad_base",
        "anulada",
    )
    list_filter = ("recurso__categoria", "recurso", "anulada", "campania")
    search_fields = (
        "observaciones",
        "campania__parcela__codigo",
        "campania__parcela__productor__apellidos",
        "campania__parcela__productor__nombres",
    )
    date_hierarchy = "fecha"
    readonly_fields = (
        "cantidad_base",
        "anulada",
        "motivo_anulacion",
        "registrado_por",
        "creado_en",
        "actualizado_en",
    )
    raw_id_fields = ("campania", "actividad", "recurso", "unidad")

    def save_model(self, request, obj, form, change):
        if not change:
            obj.registrado_por = request.user
        super().save_model(request, obj, form, change)
