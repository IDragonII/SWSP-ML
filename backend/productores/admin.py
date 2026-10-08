from django.contrib import admin

from .models import AsignacionTecnico, Comunidad, Distrito, Parcela, Productor, Provincia


@admin.register(Provincia)
class ProvinciaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)


@admin.register(Distrito)
class DistritoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "provincia", "activo")
    list_filter = ("provincia", "activo")
    search_fields = ("nombre",)


@admin.register(Comunidad)
class ComunidadAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "distrito",
        "distrito__provincia",
        "activo",
    )
    list_filter = (
        "distrito__provincia",
        "distrito",
        "activo",
    )
    search_fields = ("nombre",)


@admin.register(Productor)
class ProductorAdmin(admin.ModelAdmin):
    list_display = (
        "codigo",
        "apellidos",
        "nombres",
        "dni",
        "comunidad",
        "estado",
    )
    list_filter = (
        "estado",
        "comunidad__distrito__provincia",
        "comunidad__distrito",
    )
    search_fields = ("codigo", "nombres", "apellidos", "dni")
    # El código lo genera la base de datos (trigger): solo lectura
    readonly_fields = ("codigo", "creado_por", "creado_en", "actualizado_en")
    fieldsets = (
        ("Identidad", {"fields": ("codigo", "nombres", "apellidos", "dni", "telefono")}),
        (
            "Ubicación",
            {
                "fields": (
                    "comunidad",
                    "referencia_ubicacion",
                    "fecha_incorporacion",
                    "estado",
                )
            },
        ),
        (
            "Trazabilidad",
            {"fields": ("creado_por", "creado_en", "actualizado_en")},
        ),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)
        # El código lo rellena el trigger después del INSERT
        obj.refresh_from_db()


@admin.register(Parcela)
class ParcelaAdmin(admin.ModelAdmin):
    list_display = (
        "codigo",
        "productor",
        "comunidad",
        "superficie_ha",
        "altitud_msnm",
        "estado",
    )
    list_filter = (
        "estado",
        "tipo_suelo",
        "sistema_riego",
        "comunidad__distrito__provincia",
    )
    search_fields = (
        "codigo",
        "productor__apellidos",
        "productor__nombres",
        "referencia_ubicacion",
    )
    # El código y las fechas de trazabilidad son de sólo lectura
    readonly_fields = ("codigo", "creado_por", "creado_en", "actualizado_en")
    fieldsets = (
        (
            "Parcela",
            {
                "fields": (
                    "codigo",
                    "productor",
                    "comunidad",
                    "referencia_ubicacion",
                    "estado",
                )
            },
        ),
        (
            "Terreno",
            {
                "fields": (
                    "superficie_ha",
                    "altitud_msnm",
                    "latitud",
                    "longitud",
                    "tipo_suelo",
                    "pendiente",
                    "disponibilidad_agua",
                    "sistema_riego",
                )
            },
        ),
        (
            "Trazabilidad",
            {"fields": ("creado_por", "creado_en", "actualizado_en")},
        ),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)
        # El código lo rellena el trigger después del INSERT
        obj.refresh_from_db()


@admin.register(AsignacionTecnico)
class AsignacionTecnicoAdmin(admin.ModelAdmin):
    list_display = ("tecnico", "productor", "fecha_asignacion", "activo")
    list_filter = ("activo", "fecha_asignacion")
    search_fields = (
        "productor__apellidos",
        "productor__nombres",
        "tecnico__username",
    )
    # Sin campos de trazabilidad: la tabla de diseño no los tiene
