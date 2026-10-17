from decimal import ROUND_HALF_UP, Decimal

from django.contrib import admin

from .models import Actividad, Clima, Incidencia, SeguimientoEtapa, UsoRecurso
from .serializers import _umbral_helada


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


@admin.register(Clima)
class ClimaAdmin(admin.ModelAdmin):
    """Semana 10: consulta y trazabilidad del registro de clima. Solo
    lectura lo que calcula el servidor: fuente (siempre MANUAL desde el
    admin), temp_prom (punto medio si vienen mínima y máxima) y helada
    (derivada del umbral cuando hay mínima; sin mínima, sin marcar). Los
    datos se dan de alta y se corrigen por la API (decisión de la
    Semana 10)."""

    list_display = (
        "fecha",
        "parcela",
        "temp_min",
        "temp_max",
        "temp_prom",
        "precipitacion_mm",
        "helada",
        "fuente",
    )
    list_filter = ("fuente", "helada")
    search_fields = (
        "parcela__codigo",
        "parcela__productor__apellidos",
        "parcela__productor__nombres",
        "parcela__comunidad__nombre",
    )
    date_hierarchy = "fecha"
    readonly_fields = (
        "fuente",
        "temp_prom",
        "helada",
        "registrado_por",
        "creado_en",
        "actualizado_en",
    )
    raw_id_fields = ("parcela",)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.registrado_por = request.user
        obj.fuente = Clima.FUENTE_MANUAL
        if (
            obj.temp_prom is None
            and obj.temp_min is not None
            and obj.temp_max is not None
        ):
            obj.temp_prom = (
                (obj.temp_min + obj.temp_max) / Decimal("2")
            ).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        if obj.temp_min is not None:
            obj.helada = obj.temp_min <= _umbral_helada()
        super().save_model(request, obj, form, change)


@admin.register(Incidencia)
class IncidenciaAdmin(admin.ModelAdmin):
    """Semana 11: consulta y trazabilidad de las incidencias. La anulación
    y la reactivación solo desde la API (decisión de la Semana 11; el
    admin es de consulta, igual que actividades y usos de recursos)."""

    list_display = (
        "fecha",
        "tipo_incidencia",
        "severidad",
        "campania",
        "agente",
        "superficie_afectada_ha",
        "anulada",
    )
    list_filter = ("severidad", "tipo_incidencia__categoria", "anulada", "campania")
    search_fields = (
        "descripcion",
        "agente__nombre",
        "campania__parcela__codigo",
        "campania__parcela__productor__apellidos",
        "campania__parcela__productor__nombres",
    )
    date_hierarchy = "fecha"
    readonly_fields = (
        "anulada",
        "motivo_anulacion",
        "registrado_por",
        "creado_en",
        "actualizado_en",
    )
    raw_id_fields = ("campania", "tipo_incidencia", "agente")

    def save_model(self, request, obj, form, change):
        if not change:
            obj.registrado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(SeguimientoEtapa)
class SeguimientoEtapaAdmin(admin.ModelAdmin):
    """Semana 12: etapas de la línea de tiempo. Alta y corrección desde
    la API y desde la pantalla; el panel es de consulta (filtros por
    cultivo y etapa, búsqueda por parcela y productor). La tabla no
    tiene fechas de creación/cambio en el diseño: solo registrado_por."""

    list_display = (
        "fecha_inicio",
        "fecha_fin",
        "etapa",
        "campania",
    )
    list_filter = ("etapa__cultivo", "etapa")
    search_fields = (
        "observaciones",
        "campania__parcela__codigo",
        "campania__parcela__productor__apellidos",
        "campania__parcela__productor__nombres",
    )
    date_hierarchy = "fecha_inicio"
    readonly_fields = ("registrado_por",)
    raw_id_fields = ("campania", "etapa")

    def save_model(self, request, obj, form, change):
        if not change:
            obj.registrado_por = request.user
        super().save_model(request, obj, form, change)
