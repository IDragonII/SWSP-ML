"""API de campañas (Semanas 6, 8 y 12): el recurso central del sistema.

Listar, ver detalle, crear, editar, iniciar, cancelar y cerrar. SIN
borrado: DELETE responde 405 (las campañas se cancelan, nunca se borran).
El estado es de solo lectura: solo cambia con las acciones propias iniciar
(campanias.editar), cancelar (campanias.desactivar, hoy solo del
Administrador; el motivo queda en observaciones) y cerrar
(campanias.desactivar; Semana 8: exige producción registrada y sin revisión
pendiente; irreversible). La Semana 12 añade línea-tiempo (GET,
campanias.ver): etapas del cultivo (registradas y pendientes),
actividades, incidencias y cosecha en una sola cronología.

El Técnico solo ve y edita campañas de sus productores asignados
(reutiliza el filtro de la Semana 4): una campaña ajena responde 404,
nunca 403. Búsqueda general por código de parcela, apellidos/nombres del
productor, cultivo y variedad; filtros por estado, cultivo, variedad,
período, distrito, provincia, comunidad, productor y parcela; orden por
período descendente y paginación global (20 por página).
"""
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from django.db.models import Prefetch
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from catalogos.models import EtapaFenologica
from productores.views import (
    BusquedaPorNombre,
    PermisosPorAccion,
    SoloSusProductores,
    _BOOLEANOS_SI,
    _id_numerico,
)
from seguimiento.models import SeguimientoEtapa

from auditoria.mixins import AuditoriaMixin
from alertas.servicio import tras_confirmar

from .models import Campania
from .serializers import (
    CampaniaDesplegableSerializer,
    CampaniaDetalleSerializer,
    CampaniaEscrituraSerializer,
    CampaniaListaSerializer,
    _etapa_actual,
    _mini_cultivo,
    _mini_parcela,
)

_ESTADOS = ("PLANIFICADA", "EN_PRODUCCION", "COSECHADA", "CERRADA", "CANCELADA")

# Desempate de la línea de tiempo cuando dos hechos comparten fecha
# (Semana 12): primero lo que define la campaña (la etapa), luego lo que
# ocurrió dentro de ella.
_ORDEN_TIPO = {"ETAPA": 0, "ACTIVIDAD": 1, "INCIDENCIA": 2, "PRODUCCION": 3}


class PermisosCampania(PermisosPorAccion):
    """Permisos de campañas: campanias.ver/crear/editar/desactivar.
    Iniciar comparte campanias.editar; cancelar exige campanias.desactivar
    (hoy solo lo tiene el Administrador); línea-tiempo es de solo lectura
    (campanias.ver)."""

    permiso_requerido = "campanias.ver"
    PERMISOS = {
        "list": "campanias.ver",
        "retrieve": "campanias.ver",
        "create": "campanias.crear",
        "update": "campanias.editar",
        "partial_update": "campanias.editar",
        "iniciar": "campanias.editar",
        "cancelar": "campanias.desactivar",
        "cerrar": "campanias.desactivar",
        "linea_tiempo": "campanias.ver",
    }


class CampaniaViewSet(
    AuditoriaMixin,
    PermisosCampania,
    SoloSusProductores,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """CRUD de campañas sin DELETE (405) y con las acciones de estado."""

    auditoria_modulo = "campanias"
    queryset = (
        Campania.objects.select_related(
            "parcela",
            "parcela__productor",
            "parcela__comunidad",
            "cultivo",
            "variedad",
            "creado_por",
        )
        # Semana 12: etapas prefetcheadas (fecha descendente) para que
        # etapa_actual en la tabla no cueste una consulta por fila
        .prefetch_related(
            Prefetch(
                "etapas",
                queryset=SeguimientoEtapa.objects.select_related("etapa").order_by(
                    "-fecha_inicio", "-id"
                ),
            )
        )
    )
    serializer_class = CampaniaDetalleSerializer
    escritura_serializer = CampaniaEscrituraSerializer
    desplegable_serializer = CampaniaDesplegableSerializer
    filter_backends = (BusquedaPorNombre,)
    search_fields = (
        "parcela__codigo",
        "parcela__productor__apellidos",
        "parcela__productor__nombres",
        "cultivo__nombre",
        "variedad__nombre",
    )

    def _es_desplegable(self):
        return (
            self.request.query_params.get("desplegable", "").strip().lower()
            in _BOOLEANOS_SI
        )

    def get_serializer_class(self):
        if self.action == "list" and self._es_desplegable():
            return self.desplegable_serializer
        if self.action in ("create", "update", "partial_update"):
            return self.escritura_serializer
        if self.action == "list":
            return CampaniaListaSerializer
        return self.serializer_class

    def paginate_queryset(self, queryset):
        # Los desplegables son listas cortas: sin paginación
        if self._es_desplegable():
            return None
        return super().paginate_queryset(queryset)

    def get_queryset(self):
        queryset = self._filtrar_asignados(
            super().get_queryset(), "parcela__productor_id"
        )
        if self._es_desplegable():
            # El selector de actividades solo ofrece campañas que admiten
            # registros (ni cerradas ni canceladas)
            queryset = queryset.filter(estado__in=Campania.ESTADOS_ACTIVOS)
        params = self.request.query_params
        if params.get("produccion") in _BOOLEANOS_SI:
            # Selector del formulario de producción (Semana 8): solo en
            # producción, con siembra registrada y sin producción todavía
            queryset = queryset.filter(
                estado=Campania.ESTADO_EN_PRODUCCION, fecha_siembra__isnull=False
            ).exclude(produccion__isnull=False)
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
        with transaction.atomic():
            campania = serializer.save(creado_por=self.request.user)
            self._registrar_auditoria("CREAR", campania)

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
        with transaction.atomic():
            campania.save(update_fields=("estado",))
            self._registrar_auditoria(
                "MODIFICAR", campania, detalle={"estado": "EN_PRODUCCION"}
            )
            tras_confirmar("campania", campania)
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
        with transaction.atomic():
            campania.save(update_fields=("estado", "observaciones"))
            self._registrar_auditoria(
                "MODIFICAR", campania, detalle={"estado": "CANCELADA", "motivo": motivo}
            )
            tras_confirmar("campania", campania)
        campania.refresh_from_db()
        return Response(self._lectura(campania).data)

    @action(detail=True, methods=("post",), url_path="cerrar")
    def cerrar(self, request, pk=None):
        """COSECHADA -> CERRADA (HU-61, Semana 8). Exige campanias.desactivar,
        producción registrada y que no quede ninguna marca de revisión
        pendiente. Cerrada, la campaña no admite actividades ni cambios en
        la producción (los triggers son la red de seguridad). Irreversible:
        no hay acción de reapertura."""
        campania = self.get_object()
        if campania.estado != Campania.ESTADO_COSECHADA:
            raise ValidationError(
                {"estado": "Solo se puede cerrar una campaña cosechada."}
            )
        try:
            produccion = campania.produccion
        except ObjectDoesNotExist:
            raise ValidationError(
                {
                    "estado": (
                        "No se puede cerrar la campaña: no tiene producción "
                        "registrada."
                    )
                }
            )
        if produccion.requiere_revision:
            raise ValidationError(
                {
                    "estado": (
                        "No se puede cerrar la campaña: la producción "
                        "requiere revisión pendiente. Revísala antes de "
                        "cerrar."
                    )
                }
            )
        campania.estado = Campania.ESTADO_CERRADA
        with transaction.atomic():
            campania.save(update_fields=("estado",))
            self._registrar_auditoria(
                "MODIFICAR", campania, detalle={"estado": "CERRADA"}
            )
            tras_confirmar("campania", campania)
        campania.refresh_from_db()
        return Response(self._lectura(campania).data)

    @action(detail=True, methods=("get",), url_path="linea-tiempo")
    def linea_tiempo(self, request, pk=None):
        """Línea de tiempo de la campaña (HU-94, Semana 12): etapas del
        catálogo (registradas y pendientes), actividades, incidencias y
        cosecha en una sola cronología. Fechas ascendente y, entre dos
        hechos del mismo día, etapa → actividad → incidencia → cosecha;
        las etapas pendientes cierran la lista por orden del catálogo.
        Tope de 500 elementos con aviso truncado. Lectura: campanias.ver
        y campaña ajena → 404 (get_object con el ámbito del Técnico)."""
        campania = self.get_object()
        registros = list(
            campania.etapas.select_related("etapa").order_by("fecha_inicio", "id")
        )
        registradas = {registro.etapa_id: registro for registro in registros}

        definidas = []
        elementos = []
        for etapa in EtapaFenologica.objects.filter(
            cultivo=campania.cultivo_id
        ).order_by("orden"):
            registro = registradas.get(etapa.pk)
            definidas.append(
                {
                    "id": etapa.pk,
                    "nombre": etapa.nombre,
                    "orden": etapa.orden,
                    "registrada": registro is not None,
                    "fecha_inicio": (
                        registro.fecha_inicio.isoformat() if registro else None
                    ),
                    "fecha_fin": (
                        registro.fecha_fin.isoformat()
                        if registro and registro.fecha_fin
                        else None
                    ),
                }
            )
            if registro is None:
                # Pendiente: se pinta al final de la cronología
                elementos.append(
                    {
                        "tipo": "ETAPA",
                        "fecha": None,
                        "fecha_fin": None,
                        "titulo": etapa.nombre,
                        "detalle": None,
                        "estado": "PENDIENTE",
                        "_orden_catalogo": etapa.orden,
                    }
                )
        for registro in registros:
            elementos.append(
                {
                    "tipo": "ETAPA",
                    "fecha": registro.fecha_inicio.isoformat(),
                    "fecha_fin": (
                        registro.fecha_fin.isoformat()
                        if registro.fecha_fin
                        else None
                    ),
                    "titulo": registro.etapa.nombre,
                    "detalle": registro.observaciones or None,
                    "estado": (
                        "EN_CURSO" if registro.fecha_fin is None else "REGISTRADA"
                    ),
                    "_orden_catalogo": registro.etapa.orden,
                }
            )
        for actividad in (
            campania.actividades.filter(anulada=False)
            .select_related("tipo_actividad")
            .order_by("fecha", "id")
        ):
            elementos.append(
                {
                    "tipo": "ACTIVIDAD",
                    "fecha": actividad.fecha.isoformat(),
                    "fecha_fin": None,
                    "titulo": actividad.tipo_actividad.nombre,
                    "detalle": actividad.observaciones or None,
                    "estado": "REGISTRADA",
                }
            )
        for incidencia in (
            campania.incidencias.filter(anulada=False)
            .select_related("tipo_incidencia")
            .order_by("fecha", "id")
        ):
            elementos.append(
                {
                    "tipo": "INCIDENCIA",
                    "fecha": incidencia.fecha.isoformat(),
                    "fecha_fin": None,
                    "titulo": incidencia.tipo_incidencia.nombre,
                    "detalle": incidencia.descripcion,
                    "estado": "REGISTRADA",
                    "severidad": incidencia.severidad,
                }
            )
        try:
            produccion = campania.produccion
        except ObjectDoesNotExist:
            produccion = None
        if produccion is not None:
            elementos.append(
                {
                    "tipo": "PRODUCCION",
                    "fecha": produccion.fecha_cosecha.isoformat(),
                    "fecha_fin": None,
                    "titulo": "Cosecha",
                    "detalle": f"{produccion.produccion_kg} kg",
                    "estado": "REGISTRADA",
                }
            )

        elementos.sort(
            key=lambda e: (
                # Sin fecha (pendientes) van al final; entre pendientes,
                # por el orden del catálogo
                e["fecha"] or "9999-12-31",
                _ORDEN_TIPO[e["tipo"]],
                e.get("_orden_catalogo") or 0,
            )
        )
        total = len(elementos)
        elementos = elementos[:500]
        for elemento in elementos:
            elemento.pop("_orden_catalogo", None)
        return Response(
            {
                "campania": {
                    "id": campania.id,
                    "periodo": campania.periodo,
                    "estado": campania.estado,
                    "cultivo": _mini_cultivo(campania),
                    "parcela": _mini_parcela(campania),
                    "fecha_inicio": campania.fecha_inicio.isoformat(),
                    "fecha_fin_prevista": campania.fecha_fin_prevista.isoformat(),
                },
                "etapa_actual": _etapa_actual(campania),
                "etapas_definidas": definidas,
                "elementos": elementos,
                "total_elementos": total,
                "truncado": total > len(elementos),
            }
        )
