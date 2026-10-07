from django.contrib import admin

from .models import Comunidad, Distrito, Productor, Provincia


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
