from django.contrib import admin

from .models import (
    Agente,
    Cultivo,
    EtapaFenologica,
    Recurso,
    TipoActividad,
    TipoIncidencia,
    Unidad,
    Variedad,
)


@admin.register(Cultivo)
class CultivoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "descripcion", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)


@admin.register(Variedad)
class VariedadAdmin(admin.ModelAdmin):
    list_display = ("nombre", "cultivo", "activo")
    list_filter = ("cultivo", "activo")
    search_fields = ("nombre", "cultivo__nombre")


@admin.register(EtapaFenologica)
class EtapaFenologicaAdmin(admin.ModelAdmin):
    list_display = ("orden", "nombre", "cultivo")
    list_filter = ("cultivo",)
    search_fields = ("nombre", "cultivo__nombre")
    ordering = ("cultivo", "orden")


@admin.register(Unidad)
class UnidadAdmin(admin.ModelAdmin):
    list_display = ("nombre", "simbolo", "tipo", "factor_a_base", "es_base", "activo")
    list_filter = ("tipo", "es_base", "activo")
    search_fields = ("nombre", "simbolo")


@admin.register(TipoActividad)
class TipoActividadAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")
    # El código es fijo (lo exige la regla automática): sin altas y solo lectura
    readonly_fields = ("codigo",)

    def has_add_permission(self, request):
        return False


@admin.register(Recurso)
class RecursoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "tipo_unidad", "activo")
    list_filter = ("categoria", "tipo_unidad", "activo")
    search_fields = ("nombre",)


@admin.register(TipoIncidencia)
class TipoIncidenciaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "activo")
    list_filter = ("categoria", "activo")
    search_fields = ("nombre",)


@admin.register(Agente)
class AgenteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "activo")
    list_filter = ("tipo", "activo")
    search_fields = ("nombre",)
