from django.contrib import admin

from .models import Produccion


@admin.register(Produccion)
class ProduccionAdmin(admin.ModelAdmin):
    list_display = (
        "fecha_cosecha",
        "campania",
        "produccion_kg",
        "rendimiento_kg_ha",
        "requiere_revision",
        "incluir_en_entrenamiento",
    )
    list_filter = ("requiere_revision", "incluir_en_entrenamiento", "calidad")
    search_fields = (
        "campania__parcela__codigo",
        "campania__parcela__productor__apellidos",
        "campania__parcela__productor__nombres",
    )
    date_hierarchy = "fecha_cosecha"
    # Los campos calculados y el estado de la campaña los fija la base:
    # en el admin se ven, no se tocan (decisión de la Semana 8).
    readonly_fields = (
        "produccion_kg",
        "rendimiento_kg_ha",
        "requiere_revision",
        "motivo_revision",
        "registrado_por",
        "creado_en",
        "actualizado_en",
    )
    raw_id_fields = ("campania", "unidad")

    def save_model(self, request, obj, form, change):
        if not change:
            obj.registrado_por = request.user
        super().save_model(request, obj, form, change)
