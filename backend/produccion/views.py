"""API de producciones (Semana 8): cosecha y rendimiento de la campaña.

Listar, ver detalle, crear, editar, revisar y deshacer cosecha. SIN borrado
general: DELETE responde 405; la única excepción al «nada se borra» es la
acción deshacer-cosecha, que elimina la fila mientras la campaña no esté
CERRADA, la devuelve a EN_PRODUCCION y limpia el comparativo predicho vs
real de las predicciones en la misma transacción (S22, decisión 236).
Registrar la producción pasa la campaña a COSECHADA (fn_produccion_post,
que también completa ese comparativo); los campos calculados (kg,
rendimiento, marca de revisión) los llena la base y aquí se releen antes
de responder.

El Técnico solo ve y registra producciones de campañas de SUS productores
asignados (mismo filtro de las Semanas 4-7): una campaña ajena al crear
responde el mismo mensaje que si no existiera y una producción ajena en
detalle responde 404. revisar y deshacer-cosecha exigen
produccion.desactivar (hoy solo del Administrador); cerrar la campaña
(campanias.desactivar) vive en la API de campañas. Búsqueda por código de
parcela, apellidos/nombres y cultivo; filtros por campaña, productor,
parcela, cultivo, período, distrito, provincia, estado de la campaña,
requiere_revision y fechas de cosecha (desde/hasta); orden por fecha de
cosecha descendente y paginación global (20 por página).
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
    _BOOLEANOS_NO,
    _BOOLEANOS_SI,
    _id_numerico,
)

from auditoria.mixins import AuditoriaMixin
from alertas.servicio import tras_confirmar
from ml.servicio import limpiar_comparacion

from .models import Produccion
from .serializers import (
    ProduccionDetalleSerializer,
    ProduccionEscrituraSerializer,
    ProduccionListaSerializer,
)

_ESTADOS_CAMPANIA = (
    "PLANIFICADA",
    "EN_PRODUCCION",
    "COSECHADA",
    "CERRADA",
    "CANCELADA",
)


class PermisosProduccion(PermisosPorAccion):
    """Permisos de producciones: produccion.ver/crear/editar/desactivar.
    revisar y deshacer-cosecha comparten produccion.desactivar (hoy solo
    del Administrador); crear y editar también están del Técnico."""

    permiso_requerido = "produccion.ver"
    PERMISOS = {
        "list": "produccion.ver",
        "retrieve": "produccion.ver",
        "create": "produccion.crear",
        "update": "produccion.editar",
        "partial_update": "produccion.editar",
        "revisar": "produccion.desactivar",
        "deshacer_cosecha": "produccion.desactivar",
    }


class ProduccionViewSet(
    AuditoriaMixin,
    PermisosProduccion,
    SoloSusProductores,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """CRUD de producciones sin DELETE (405) y con las acciones de revisión
    y deshacer cosecha."""

    auditoria_modulo = "produccion"
    queryset = Produccion.objects.select_related(
        "campania",
        "campania__parcela",
        "campania__parcela__productor",
        "campania__cultivo",
        "unidad",
        "registrado_por",
    )
    serializer_class = ProduccionDetalleSerializer
    escritura_serializer = ProduccionEscrituraSerializer
    filter_backends = (BusquedaPorNombre,)
    search_fields = (
        "campania__parcela__codigo",
        "campania__parcela__productor__apellidos",
        "campania__parcela__productor__nombres",
        "campania__cultivo__nombre",
    )

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return self.escritura_serializer
        if self.action == "list":
            return ProduccionListaSerializer
        return self.serializer_class

    def get_queryset(self):
        queryset = self._filtrar_asignados(
            super().get_queryset(), "campania__parcela__productor_id"
        )
        params = self.request.query_params
        if params.get("campania"):
            queryset = queryset.filter(
                campania_id=_id_numerico(params["campania"], "campania")
            )
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
        if params.get("periodo"):
            queryset = queryset.filter(campania__periodo=params["periodo"])
        if params.get("distrito"):
            queryset = queryset.filter(
                campania__parcela__comunidad__distrito_id=_id_numerico(
                    params["distrito"], "distrito"
                )
            )
        if params.get("provincia"):
            queryset = queryset.filter(
                campania__parcela__comunidad__distrito__provincia_id=_id_numerico(
                    params["provincia"], "provincia"
                )
            )
        if params.get("estado"):
            estado = params["estado"]
            if estado not in _ESTADOS_CAMPANIA:
                raise ValidationError(
                    {
                        "estado": (
                            "Use PLANIFICADA, EN_PRODUCCION, COSECHADA, "
                            "CERRADA o CANCELADA."
                        )
                    }
                )
            queryset = queryset.filter(campania__estado=estado)
        if params.get("requiere_revision") is not None:
            valor = params["requiere_revision"].strip().lower()
            if valor in _BOOLEANOS_SI:
                queryset = queryset.filter(requiere_revision=True)
            elif valor in _BOOLEANOS_NO:
                queryset = queryset.filter(requiere_revision=False)
            else:
                raise ValidationError({"requiere_revision": "Use true o false."})
        if params.get("fecha_desde"):
            queryset = queryset.filter(fecha_cosecha__gte=params["fecha_desde"])
        if params.get("fecha_hasta"):
            queryset = queryset.filter(fecha_cosecha__lte=params["fecha_hasta"])
        return queryset

    def perform_create(self, serializer):
        with transaction.atomic():
            obj = serializer.save(registrado_por=self.request.user)
            self._registrar_auditoria("CREAR", obj)
            # fn_produccion_post pasó la campaña a COSECHADA: se
            # reevalúan sus alertas pendientes tras el COMMIT
            tras_confirmar("campania", obj.campania)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                self.perform_create(serializer)
        except IntegrityError:
            raise self._traducir_integridad(serializer)
        # Los triggers pudieron calcular kg/rendimiento, marcar revisión y
        # pasar la campaña a COSECHADA: se releen antes de responder
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
            raise self._traducir_integridad(serializer)
        serializer.instance.refresh_from_db()
        serializer.instance.campania.refresh_from_db()
        return Response(self._lectura(serializer.instance).data)

    def _lectura(self, obj):
        return ProduccionDetalleSerializer(obj, context=self.get_serializer_context())

    def _traducir_integridad(self, serializer):
        """400 claro cuando la base rechaza el UNIQUE de campaña o los
        checks (nunca un 500). Repite aquí la consulta del duplicado."""
        datos = serializer.validated_data
        instancia = serializer.instance
        campania = datos.get(
            "campania", getattr(instancia, "campania", None) if instancia else None
        )
        excluido = instancia.pk if instancia is not None else None
        if campania is not None:
            consulta = Produccion.objects.filter(campania=campania)
            if excluido is not None:
                consulta = consulta.exclude(pk=excluido)
            existente = consulta.first()
            if existente is not None:
                return ValidationError(
                    {
                        "campania": (
                            f"Ya existe una producción para esta campaña "
                            f"(id {existente.pk})."
                        )
                    }
                )
        return ValidationError(
            "No se pudo guardar la producción: los datos chocan con una "
            "restricción de la base de datos."
        )

    @action(detail=True, methods=("post",), url_path="revisar")
    def revisar(self, request, pk=None):
        """Revisión del administrador (HU-59): quita la marca de revisión,
        conserva el motivo original para trazabilidad (añade la nota) y
        decide si la producción se incluye en el dataset de entrenamiento.
        Exige produccion.desactivar y nota de revisión."""
        produccion = self.get_object()
        if not produccion.requiere_revision:
            raise ValidationError({"estado": "La producción no requiere revisión."})
        nota = (request.data.get("nota") or "").strip()
        if not nota:
            raise ValidationError({"nota": "La nota de revisión es obligatoria."})
        incluir = request.data.get("incluir_en_entrenamiento")
        if not isinstance(incluir, bool):
            raise ValidationError(
                {
                    "incluir_en_entrenamiento": (
                        "Debe indicar si se incluye en el entrenamiento "
                        "(true o false)."
                    )
                }
            )
        with transaction.atomic():
            produccion.requiere_revision = False
            if produccion.motivo_revision:
                produccion.motivo_revision = (
                    f"{produccion.motivo_revision} — Revisión: {nota}"
                )[:200]
            else:
                produccion.motivo_revision = f"Revisión: {nota}"[:200]
            produccion.incluir_en_entrenamiento = incluir
            produccion.save(
                update_fields=(
                    "requiere_revision",
                    "motivo_revision",
                    "incluir_en_entrenamiento",
                )
            )
            self._registrar_auditoria(
                "MODIFICAR",
                produccion,
                detalle={"nota": nota, "incluir_en_entrenamiento": incluir},
            )
        produccion.refresh_from_db()
        return Response(self._lectura(produccion).data)

    @action(detail=True, methods=("post",), url_path="deshacer-cosecha")
    def deshacer_cosecha(self, request, pk=None):
        """Única excepción al «nada se borra» (HU-60): elimina la fila de
        producción mientras la campaña no esté CERRADA y devuelve la
        campaña a EN_PRODUCCION. Exige produccion.desactivar y motivo; la
        campaña vuelve a quedar abierta para registrar otra producción."""
        produccion = self.get_object()
        campania = produccion.campania
        if campania.estado == Campania.ESTADO_CERRADA:
            raise ValidationError(
                {
                    "estado": (
                        "No se puede deshacer la cosecha: la campaña está "
                        "cerrada."
                    )
                }
            )
        motivo = (request.data.get("motivo") or "").strip()
        if not motivo:
            raise ValidationError({"motivo": "El motivo es obligatorio."})
        with transaction.atomic():
            # Primero la campaña (fn_validar_campania permite
            # COSECHADA -> EN_PRODUCCION) y luego el borrado físico
            campania.estado = Campania.ESTADO_EN_PRODUCCION
            campania.save(update_fields=("estado",))
            produccion_pk = produccion.pk
            produccion.delete()
            # El trigger no corre al borrar: el comparativo predicho vs
            # real lo limpia el servicio en la MISMA transacción (S22,
            # decisión 236).
            limpiar_comparacion(campania)
            self._registrar_auditoria(
                "ELIMINAR",
                registro_id=produccion_pk,
                detalle={"motivo": motivo, "campania": campania.pk},
            )
            tras_confirmar("campania", campania)
        campania.refresh_from_db()
        return Response(
            {"campania": campania.id, "estado": campania.estado, "motivo": motivo}
        )
