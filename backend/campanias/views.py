"""API de campañas (Semana 6): el recurso central del sistema.

Listar, ver detalle, crear, editar, iniciar y cancelar. SIN borrado:
DELETE responde 405 (las campañas se cancelan, nunca se borran). El
estado es de solo lectura: solo cambia con las acciones propias iniciar
(campanias.editar) y cancelar (campanias.desactivar, hoy solo del
Administrador; el motivo queda en observaciones).

El Técnico solo ve y edita campañas de sus productores asignados
(reutiliza el filtro de la Semana 4): una campaña ajena responde 404,
nunca 403. Búsqueda general por código de parcela, apellidos/nombres del
productor, cultivo y variedad; filtros por estado, cultivo, variedad,
período, distrito, provincia, comunidad, productor y parcela; orden por
período descendente y paginación global (20 por página).
"""
from django.db import IntegrityError, transaction
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from productores.views import (
    BusquedaPorNombre,
    PermisosPorAccion,
    SoloSusProductores,
    _id_numerico,
)

from .models import Campania
from .serializers import (
    CampaniaDetalleSerializer,
    CampaniaEscrituraSerializer,
    CampaniaListaSerializer,
)

_ESTADOS = ("PLANIFICADA", "EN_PRODUCCION", "COSECHADA", "CERRADA", "CANCELADA")


class PermisosCampania(PermisosPorAccion):
    """Permisos de campañas: campanias.ver/crear/editar/desactivar.
    Iniciar comparte campanias.editar; cancelar exige campanias.desactivar
    (hoy solo lo tiene el Administrador)."""

    permiso_requerido = "campanias.ver"
    PERMISOS = {
        "list": "campanias.ver",
        "retrieve": "campanias.ver",
        "create": "campanias.crear",
        "update": "campanias.editar",
        "partial_update": "campanias.editar",
        "iniciar": "campanias.editar",
        "cancelar": "campanias.desactivar",
    }


class CampaniaViewSet(
    PermisosCampania,
    SoloSusProductores,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """CRUD de campañas sin DELETE (405) y con las acciones de estado."""

    queryset = Campania.objects.select_related(
        "parcela",
        "parcela__productor",
        "parcela__comunidad",
        "cultivo",
        "variedad",
        "creado_por",
    )
    serializer_class = CampaniaDetalleSerializer
    escritura_serializer = CampaniaEscrituraSerializer
    filter_backends = (BusquedaPorNombre,)
    search_fields = (
        "parcela__codigo",
        "parcela__productor__apellidos",
        "parcela__productor__nombres",
        "cultivo__nombre",
        "variedad__nombre",
    )

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return self.escritura_serializer
        if self.action == "list":
            return CampaniaListaSerializer
        return self.serializer_class

    def get_queryset(self):
        queryset = self._filtrar_asignados(
            super().get_queryset(), "parcela__productor_id"
        )
        params = self.request.query_params
        if params.get("estado"):
            estado = params["estado"]
            if estado not in _ESTADOS:
                raise ValidationError(
                    {
                        "estado": (
                            "Use PLANIFICADA, EN_PRODUCCION, COSECHADA, "
                            "CERRADA o CANCELADA."
                        )
                    }
                )
            queryset = queryset.filter(estado=estado)
        if params.get("cultivo"):
            queryset = queryset.filter(
                cultivo_id=_id_numerico(params["cultivo"], "cultivo")
            )
        if params.get("variedad"):
            queryset = queryset.filter(
                variedad_id=_id_numerico(params["variedad"], "variedad")
            )
        if params.get("periodo"):
            queryset = queryset.filter(periodo=params["periodo"])
        if params.get("parcela"):
            queryset = queryset.filter(
                parcela_id=_id_numerico(params["parcela"], "parcela")
            )
        if params.get("productor"):
            queryset = queryset.filter(
                parcela__productor_id=_id_numerico(params["productor"], "productor")
            )
        if params.get("comunidad"):
            queryset = queryset.filter(
                parcela__comunidad_id=_id_numerico(params["comunidad"], "comunidad")
            )
        if params.get("distrito"):
            queryset = queryset.filter(
                parcela__comunidad__distrito_id=_id_numerico(
                    params["distrito"], "distrito"
                )
            )
        if params.get("provincia"):
            queryset = queryset.filter(
                parcela__comunidad__distrito__provincia_id=_id_numerico(
                    params["provincia"], "provincia"
                )
            )
        return queryset

    def perform_create(self, serializer):
        serializer.save(creado_por=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                self.perform_create(serializer)
        except IntegrityError:
            # Choque de los índices parciales (carrera entre la validación y
            # el INSERT): la traducimos a un 400 que nombra la campaña
            raise self._traducir_integridad(serializer)
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
            raise self._traducir_integridad(serializer)
        # El trigger mantiene actualizado_en: se releen las fechas
        serializer.instance.refresh_from_db()
        return Response(self._lectura(serializer.instance).data)

    def _lectura(self, obj):
        return CampaniaDetalleSerializer(obj, context=self.get_serializer_context())

    def _traducir_integridad(self, serializer):
        """400 claro cuando la base rechaza el duplicado o la clave
        compuesta (nunca un 500). Repite aquí las consultas (a propósito
        sin pasar por el serializador, para que las pruebas 72 y 73 puedan
        parchear solo la validación previa y fueren este camino)."""
        datos = serializer.validated_data
        instancia = serializer.instance
        parcela = datos.get(
            "parcela", getattr(instancia, "parcela", None) if instancia else None
        )
        periodo = datos.get(
            "periodo", getattr(instancia, "periodo", None) if instancia else None
        )
        excluido = instancia.pk if instancia is not None else None
        if parcela is not None and periodo is not None:
            consulta = (
                Campania.objects.filter(parcela=parcela, periodo=periodo)
                .exclude(estado=Campania.ESTADO_CANCELADA)
                .select_related("cultivo")
            )
            if excluido is not None:
                consulta = consulta.exclude(pk=excluido)
            existente = consulta.first()
            if existente is not None:
                return ValidationError(
                    {
                        "parcela": (
                            f"Ya existe una campaña de {existente.cultivo.nombre} "
                            f"en esta parcela para el período {existente.periodo} "
                            f"(id {existente.pk})."
                        ),
                        "campania_existente": str(existente.pk),
                    }
                )
            consulta = (
                Campania.objects.filter(
                    parcela=parcela, estado__in=Campania.ESTADOS_ACTIVOS
                )
                .select_related("cultivo")
            )
            if excluido is not None:
                consulta = consulta.exclude(pk=excluido)
            existente = consulta.first()
            if existente is not None:
                return ValidationError(
                    {
                        "parcela": (
                            f"Ya existe una campaña activa en esta parcela "
                            f"(id {existente.pk}, {existente.periodo}, "
                            f"{existente.cultivo.nombre})."
                        ),
                        "campania_existente": str(existente.pk),
                    }
                )
        variedad = datos.get(
            "variedad", getattr(instancia, "variedad", None) if instancia else None
        )
        cultivo = datos.get(
            "cultivo", getattr(instancia, "cultivo", None) if instancia else None
        )
        if variedad is not None and cultivo is not None:
            if variedad.cultivo_id != cultivo.pk:
                return ValidationError(
                    {"variedad": "La variedad indicada no pertenece al cultivo elegido."}
                )
        return ValidationError(
            "No se pudo guardar la campaña: los datos chocan con una "
            "restricción de la base de datos."
        )

    @action(detail=True, methods=("post",), url_path="iniciar")
    def iniciar(self, request, pk=None):
        """PLANIFICADA -> EN_PRODUCCION (HU-39). Al iniciar quedan
        bloqueados parcela, cultivo, variedad, período y fecha de inicio."""
        campania = self.get_object()
        if campania.estado != Campania.ESTADO_PLANIFICADA:
            raise ValidationError(
                {"estado": "Solo se puede iniciar una campaña planificada."}
            )
        campania.estado = Campania.ESTADO_EN_PRODUCCION
        campania.save(update_fields=("estado",))
        campania.refresh_from_db()
        return Response(self._lectura(campania).data)

    @action(detail=True, methods=("post",), url_path="cancelar")
    def cancelar(self, request, pk=None):
        """Cualquier estado vivo -> CANCELADA (HU-40). Exige motivo y el
        permiso campanias.desactivar; el motivo queda en observaciones y
        la parcela queda libre (los índices parciales no cuentan las
        canceladas)."""
        campania = self.get_object()
        if campania.estado == Campania.ESTADO_CANCELADA:
            raise ValidationError(
                {"estado": "La campaña ya está cancelada."}
            )
        if campania.estado not in (
            Campania.ESTADO_PLANIFICADA,
            Campania.ESTADO_EN_PRODUCCION,
        ):
            raise ValidationError(
                {
                    "estado": (
                        "Solo se puede cancelar una campaña planificada o "
                        "en producción."
                    )
                }
            )
        motivo = (request.data.get("motivo") or "").strip()
        if not motivo:
            raise ValidationError(
                {"motivo": "El motivo de cancelación es obligatorio."}
            )
        if campania.observaciones:
            campania.observaciones = f"{campania.observaciones}\n{motivo}"
        else:
            campania.observaciones = motivo
        campania.estado = Campania.ESTADO_CANCELADA
        campania.save(update_fields=("estado", "observaciones"))
        campania.refresh_from_db()
        return Response(self._lectura(campania).data)
