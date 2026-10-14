"""API de seguimiento: actividades productivas (Semana 7) y usos de
recursos (Semana 9).

Actividades: listar, ver detalle, crear, editar, anular y reactivar. SIN
borrado: DELETE responde 405 (la anulación es el «borrado lógico»: conserva
la traza y el dataset la excluye). El estado es anulada: solo cambia con las
acciones propias anular (actividades.desactivar, exige motivo) y reactivar
(actividades.desactivar; la campaña debe seguir abierta y la fecha aún
válida). Al anular, la Semana 9 añade la anulación en cascada de los usos
de recursos activos de la actividad, con el mismo motivo y en la misma
transacción (si algo falla, no se anula nada); reactivar NO los reactiva.

El Técnico solo ve y registra actividades de campañas de SUS productores
asignados (reutiliza el filtro de la Semana 4): una campaña ajena al
crear responde el mismo mensaje que si no existiera y una actividad ajena
en detalle responde 404. Búsqueda por código de parcela, apellidos y
nombres del productor, método y observaciones; filtros por campaña, tipo,
fechas (desde/hasta), productor, parcela, cultivo y estado
(ACTIVA/ANULADA); orden por fecha descendente y paginación global
(20 por página).

Usos de recursos: registrar qué insumo, cuánto y cuándo se usó en cada
campaña (HU-67 a HU-75). Misma fórmula que actividades: SIN DELETE (405),
anulación lógica con motivo (recursos.desactivar), reactivar solo si la
campaña sigue abierta y la fecha sigue válida, y permisos
recursos.ver/crear/editar/desactivar. Búsqueda por código de parcela,
productor, recurso y observaciones; filtros por campaña, actividad,
recurso, categoría, fechas (desde/hasta), productor, parcela, cultivo y
estado (ACTIVA/ANULADA).
"""
from django.db import IntegrityError, transaction
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from campanias.models import Campania
from productores.views import (
    BusquedaPorNombre,
    PermisosPorAccion,
    SoloSusProductores,
    _id_numerico,
)

from .models import Actividad, UsoRecurso
from .serializers import (
    ActividadDetalleSerializer,
    ActividadEscrituraSerializer,
    ActividadListaSerializer,
    UsoRecursoDetalleSerializer,
    UsoRecursoEscrituraSerializer,
    UsoRecursoListaSerializer,
)


class PermisosActividad(PermisosPorAccion):
    """Permisos de actividades: actividades.ver/crear/editar/desactivar.
    Anular y reactivar comparten actividades.desactivar (hoy solo del
    Administrador); crear y editar también están del Técnico."""

    permiso_requerido = "actividades.ver"
    PERMISOS = {
        "list": "actividades.ver",
        "retrieve": "actividades.ver",
        "create": "actividades.crear",
        "update": "actividades.editar",
        "partial_update": "actividades.editar",
        "anular": "actividades.desactivar",
        "reactivar": "actividades.desactivar",
    }


class ActividadViewSet(
    PermisosActividad,
    SoloSusProductores,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """CRUD de actividades sin DELETE (405) y con las acciones de anulación."""

    queryset = Actividad.objects.select_related(
        "campania",
        "campania__parcela",
        "campania__parcela__productor",
        "campania__cultivo",
        "tipo_actividad",
        "registrado_por",
    )
    serializer_class = ActividadDetalleSerializer
    escritura_serializer = ActividadEscrituraSerializer
    filter_backends = (BusquedaPorNombre,)
    search_fields = (
        "campania__parcela__codigo",
        "campania__parcela__productor__apellidos",
        "campania__parcela__productor__nombres",
        "metodo",
        "observaciones",
    )

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return self.escritura_serializer
        if self.action == "list":
            return ActividadListaSerializer
        return self.serializer_class

    def get_queryset(self):
        queryset = self._filtrar_asignados(
            super().get_queryset(), "campania__parcela__productor_id"
        )
        params = self.request.query_params
        if params.get("estado"):
            estado = params["estado"]
            if estado not in ("ACTIVA", "ANULADA"):
                raise ValidationError({"estado": "Use ACTIVA o ANULADA."})
            queryset = queryset.filter(anulada=(estado == "ANULADA"))
        if params.get("campania"):
            queryset = queryset.filter(
                campania_id=_id_numerico(params["campania"], "campania")
            )
        if params.get("tipo"):
            queryset = queryset.filter(
                tipo_actividad_id=_id_numerico(params["tipo"], "tipo")
            )
        if params.get("fecha_desde"):
            queryset = queryset.filter(fecha__gte=params["fecha_desde"])
        if params.get("fecha_hasta"):
            queryset = queryset.filter(fecha__lte=params["fecha_hasta"])
        if params.get("productor"):
            queryset = queryset.filter(
                campania__parcela__productor_id=_id_numerico(
                    params["productor"], "productor"
                )
            )
        if params.get("parcela"):
            queryset = queryset.filter(
                campania__parcela_id=_id_numerico(params["parcela"], "parcela")
            )
        if params.get("cultivo"):
            queryset = queryset.filter(
                campania__cultivo_id=_id_numerico(params["cultivo"], "cultivo")
            )
        return queryset

    def perform_create(self, serializer):
        serializer.save(registrado_por=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                self.perform_create(serializer)
        except IntegrityError:
            # Choque improbable con la base (carrera entre la validación
            # y el INSERT): 400 en vez de un 500
            raise ValidationError(
                "No se pudo guardar la actividad: los datos chocan con una "
                "restricción de la base de datos."
            )
        # Los triggers pudieron cambiar fecha_siembra/estado de la campaña
        # y fijar actualizado_en: se releen antes de responder
        serializer.instance.refresh_from_db()
        serializer.instance.campania.refresh_from_db()
        return Response(self._lectura(serializer.instance).data, status=201)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                self.perform_update(serializer)
        except IntegrityError:
            raise ValidationError(
                "No se pudo guardar la actividad: los datos chocan con una "
                "restricción de la base de datos."
            )
        serializer.instance.refresh_from_db()
        serializer.instance.campania.refresh_from_db()
        return Response(self._lectura(serializer.instance).data)

    def _lectura(self, obj):
        return ActividadDetalleSerializer(obj, context=self.get_serializer_context())

    @action(detail=True, methods=("post",), url_path="anular")
    def anular(self, request, pk=None):
        """Anulación lógica (HU-50): exige motivo y actividades.desactivar.
        Si era una siembra activa, fn_actividad_siembra recalcula la fecha
        de siembra de la campaña (la campaña NO vuelve a planificada).
        Semana 9: anula también, en la MISMA transacción, los usos de
        recursos activos de la actividad (mismo motivo) y la respuesta
        informa cuántos recursos se anularon con ella; si algo falla, no
        se anula nada."""
        actividad = self.get_object()
        if actividad.anulada:
            raise ValidationError({"estado": "La actividad ya está anulada."})
        motivo = (request.data.get("motivo") or "").strip()
        if not motivo:
            raise ValidationError(
                {"motivo": "El motivo de anulación es obligatorio."}
            )
        with transaction.atomic():
            actividad.anulada = True
            actividad.motivo_anulacion = motivo
            actividad.save(update_fields=("anulada", "motivo_anulacion"))
            usos = UsoRecurso.objects.filter(actividad=actividad, anulada=False)
            recursos_anulados = usos.count()
            usos.update(anulada=True, motivo_anulacion=motivo)
        actividad.refresh_from_db()
        actividad.campania.refresh_from_db()
        datos = self._lectura(actividad).data
        datos["recursos_anulados"] = recursos_anulados
        return Response(datos)

    @action(detail=True, methods=("post",), url_path="reactivar")
    def reactivar(self, request, pk=None):
        """Reactiva una actividad anulada (HU-51): la campaña debe seguir
        abierta y la fecha aún dentro del período (los triggers son la red
        de seguridad; aquí se responde 400 en español antes de tocar la
        base). Si era siembra, la fecha de siembra se recalcula otra vez."""
        actividad = self.get_object()
        if not actividad.anulada:
            raise ValidationError({"estado": "La actividad no está anulada."})
        campania = actividad.campania
        if campania.estado not in Campania.ESTADOS_ACTIVOS:
            raise ValidationError(
                {
                    "estado": (
                        f"La campaña está {campania.estado} y no admite nuevos "
                        "registros."
                    )
                }
            )
        if not campania.fecha_inicio <= actividad.fecha <= campania.fecha_fin_prevista:
            raise ValidationError(
                {
                    "fecha": (
                        f"La fecha {actividad.fecha} está fuera del período de "
                        f"la campaña ({campania.fecha_inicio} a "
                        f"{campania.fecha_fin_prevista})."
                    )
                }
            )
        actividad.anulada = False
        actividad.motivo_anulacion = None
        actividad.save(update_fields=("anulada", "motivo_anulacion"))
        actividad.refresh_from_db()
        actividad.campania.refresh_from_db()
        return Response(self._lectura(actividad).data)


class PermisosUsoRecurso(PermisosPorAccion):
    """Permisos de usos de recursos: recursos.ver/crear/editar/desactivar.
    Anular y reactivar comparten recursos.desactivar (hoy solo del
    Administrador); crear y editar también están del Técnico."""

    permiso_requerido = "recursos.ver"
    PERMISOS = {
        "list": "recursos.ver",
        "retrieve": "recursos.ver",
        "create": "recursos.crear",
        "update": "recursos.editar",
        "partial_update": "recursos.editar",
        "anular": "recursos.desactivar",
        "reactivar": "recursos.desactivar",
    }


class UsoRecursoViewSet(
    PermisosUsoRecurso,
    SoloSusProductores,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """CRUD de usos de recursos sin DELETE (405) y con anulación lógica."""

    queryset = UsoRecurso.objects.select_related(
        "campania",
        "campania__parcela",
        "campania__parcela__productor",
        "campania__cultivo",
        "actividad",
        "actividad__tipo_actividad",
        "recurso",
        "unidad",
        "registrado_por",
    )
    serializer_class = UsoRecursoDetalleSerializer
    escritura_serializer = UsoRecursoEscrituraSerializer
    filter_backends = (BusquedaPorNombre,)
    search_fields = (
        "campania__parcela__codigo",
        "campania__parcela__productor__apellidos",
        "campania__parcela__productor__nombres",
        "recurso__nombre",
        "observaciones",
    )

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return self.escritura_serializer
        if self.action == "list":
            return UsoRecursoListaSerializer
        return self.serializer_class

    def get_queryset(self):
        queryset = self._filtrar_asignados(
            super().get_queryset(), "campania__parcela__productor_id"
        )
        params = self.request.query_params
        if params.get("estado"):
            estado = params["estado"]
            if estado not in ("ACTIVA", "ANULADA"):
                raise ValidationError({"estado": "Use ACTIVA o ANULADA."})
            queryset = queryset.filter(anulada=(estado == "ANULADA"))
        if params.get("campania"):
            queryset = queryset.filter(
                campania_id=_id_numerico(params["campania"], "campania")
            )
        if params.get("actividad"):
            queryset = queryset.filter(
                actividad_id=_id_numerico(params["actividad"], "actividad")
            )
        if params.get("recurso"):
            queryset = queryset.filter(
                recurso_id=_id_numerico(params["recurso"], "recurso")
            )
        if params.get("categoria"):
            queryset = queryset.filter(recurso__categoria=params["categoria"])
        if params.get("fecha_desde"):
            queryset = queryset.filter(fecha__gte=params["fecha_desde"])
        if params.get("fecha_hasta"):
            queryset = queryset.filter(fecha__lte=params["fecha_hasta"])
        if params.get("productor"):
            queryset = queryset.filter(
                campania__parcela__productor_id=_id_numerico(
                    params["productor"], "productor"
                )
            )
        if params.get("parcela"):
            queryset = queryset.filter(
                campania__parcela_id=_id_numerico(params["parcela"], "parcela")
            )
        if params.get("cultivo"):
            queryset = queryset.filter(
                campania__cultivo_id=_id_numerico(params["cultivo"], "cultivo")
            )
        return queryset

    def perform_create(self, serializer):
        serializer.save(registrado_por=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                self.perform_create(serializer)
        except IntegrityError:
            raise ValidationError(
                "No se pudo guardar el uso de recurso: los datos chocan con "
                "una restricción de la base de datos."
            )
        # fn_uso_recurso fijó cantidad_base y pudo mover estado/fechas de
        # la campaña: se releen antes de responder
        serializer.instance.refresh_from_db()
        serializer.instance.campania.refresh_from_db()
        return Response(self._lectura(serializer.instance).data, status=201)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                self.perform_update(serializer)
        except IntegrityError:
            raise ValidationError(
                "No se pudo guardar el uso de recurso: los datos chocan con "
                "una restricción de la base de datos."
            )
        serializer.instance.refresh_from_db()
        serializer.instance.campania.refresh_from_db()
        return Response(self._lectura(serializer.instance).data)

    def _lectura(self, obj):
        return UsoRecursoDetalleSerializer(obj, context=self.get_serializer_context())

    @action(detail=True, methods=("post",), url_path="anular")
    def anular(self, request, pk=None):
        """Anulación lógica (HU-72): exige motivo y recursos.desactivar.
        Solo si la campaña sigue admitiendo registros (lo impide la base
        al cambiar la fecha; aquí se responde 400 en español)."""
        uso = self.get_object()
        if uso.anulada:
            raise ValidationError({"estado": "El uso de recurso ya está anulado."})
        campania = uso.campania
        if campania.estado not in Campania.ESTADOS_ACTIVOS:
            raise ValidationError(
                {
                    "estado": (
                        f"La campaña está {campania.estado} y no admite nuevos "
                        "registros."
                    )
                }
            )
        motivo = (request.data.get("motivo") or "").strip()
        if not motivo:
            raise ValidationError(
                {"motivo": "El motivo de anulación es obligatorio."}
            )
        uso.anulada = True
        uso.motivo_anulacion = motivo
        uso.save(update_fields=("anulada", "motivo_anulacion"))
        uso.refresh_from_db()
        uso.campania.refresh_from_db()
        return Response(self._lectura(uso).data)

    @action(detail=True, methods=("post",), url_path="reactivar")
    def reactivar(self, request, pk=None):
        """Reactiva un uso anulado (HU-73): la campaña debe seguir abierta
        y la fecha aún dentro del período (los triggers son la red de
        seguridad; aquí se responde 400 en español antes de tocar la
        base)."""
        uso = self.get_object()
        if not uso.anulada:
            raise ValidationError({"estado": "El uso de recurso no está anulado."})
        campania = uso.campania
        if campania.estado not in Campania.ESTADOS_ACTIVOS:
            raise ValidationError(
                {
                    "estado": (
                        f"La campaña está {campania.estado} y no admite nuevos "
                        "registros."
                    )
                }
            )
        if not campania.fecha_inicio <= uso.fecha <= campania.fecha_fin_prevista:
            raise ValidationError(
                {
                    "fecha": (
                        f"La fecha {uso.fecha} está fuera del período de "
                        f"la campaña ({campania.fecha_inicio} a "
                        f"{campania.fecha_fin_prevista})."
                    )
                }
            )
        uso.anulada = False
        uso.motivo_anulacion = None
        uso.save(update_fields=("anulada", "motivo_anulacion"))
        uso.refresh_from_db()
        uso.campania.refresh_from_db()
        return Response(self._lectura(uso).data)
