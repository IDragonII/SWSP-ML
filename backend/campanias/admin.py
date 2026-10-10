from django.contrib import admin

from .models import Campania


@admin.register(Campania)
class CampaniaAdmin(admin.ModelAdmin):
    list_display = (
        "periodo",
        "parcela",
        "cultivo",
        "variedad",
        "superficie_sembrada_ha",
        "estado",
    )
    list_filter = ("estado", "cultivo", "periodo")
    search_fields = (
        "parcela__codigo",
        "parcela__productor__apellidos",
        "parcela__productor__nombres",
    )
    # Estado y fecha de siembra en solo lectura (decisión de la Semana 6):
    # el estado solo cambia con iniciar/cancelar y la siembra la llena la
    # actividad de siembra del Sprint 4.
    readonly_fields = (
        "estado",
        "fecha_siembra",
        "creado_por",
        "creado_en",
        "actualizado_en",
    )
    fieldsets = (
        (
            "Campaña",
            {
                "fields": (
                    "periodo",
                    "parcela",
                    "cultivo",
                    "variedad",
                    "estado",
                )
            },
        ),
        (
            "Fechas y superficie",
            {
                "fields": (
                    "fecha_inicio",
                    "fecha_fin_prevista",
                    "fecha_siembra",
                    "superficie_sembrada_ha",
                )
            },
        ),
        ("Seguimiento", {"fields": ("observaciones",)}),
        ("Trazabilidad", {"fields": ("creado_por", "creado_en", "actualizado_en")}),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)
