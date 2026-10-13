"""API de los 8 catálogos (Semana 5).

Listado, detalle, creación, edición y estado de cultivos, variedades,
etapas fenológicas, unidades, tipos de actividad, recursos, tipos de
incidencia y agentes. Ningún recurso ofrece borrado: DELETE responde
405 (decisión 6 de la Semana 3) y los tipos de actividad además no
admiten altas (su código es fijo: los 7 sembrados).

?desplegable=1 devuelve la lista corta sin paginar y solo con activos
(las variedades y etapas exigen además cultivo activo). Las etapas no
tienen estado: se ocultan desactivando su cultivo y se reordenan con
POST etapas-fenologicas/reordenar/ de forma atómica (valor temporal).
Los permisos son los de la Semana 2 (catalogos.ver/crear/editar/
desactivar): sin permiso, la API responde 403.
"""
from django.db import transaction
from django.db.models import F
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from productores.views import (
    _BOOLEANOS_NO,
    _BOOLEANOS_SI,
    _id_numerico,
    BusquedaPorNombre,
    PermisosCatalogo,
)

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
from .serializers import (
    AgenteDesplegableSerializer,
    AgenteEscrituraSerializer,
    AgenteSerializer,
    CultivoDesplegableSerializer,
    CultivoEscrituraSerializer,
    CultivoSerializer,
    EtapaDesplegableSerializer,
    EtapaEscrituraSerializer,
    EtapaSerializer,
    RecursoDesplegableSerializer,
    RecursoEscrituraSerializer,
    RecursoSerializer,
    TipoActividadDesplegableSerializer,
    TipoActividadEscrituraSerializer,
    TipoActividadSerializer,
    TipoIncidenciaDesplegableSerializer,
    TipoIncidenciaEscrituraSerializer,
    TipoIncidenciaSerializer,
    UnidadDesplegableSerializer,
    UnidadEscrituraSerializer,
    UnidadSerializer,
    VariedadDesplegableSerializer,
    VariedadEscrituraSerializer,
    VariedadSerializer,
)


class VistaCatalogo(
    PermisosCatalogo,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """CRUD de catálogo sin DELETE (405), con ?activo=, ?busqueda= y
    ?desplegable=1 (lista corta sin paginar y solo activos)."""

    escritura_serializer = None
    desplegable_serializer = None
    filter_backends = (BusquedaPorNombre,)
    search_fields = ("nombre",)

    def get_serializer_class(self):
        if self.action == "list" and self._es_desplegable():
            return self.desplegable_serializer
        if self.action in ("create", "update", "partial_update"):
            return self.escritura_serializer
        return self.serializer_class

    def _es_desplegable(self):
        return (
            self.request.query_params.get("desplegable", "").strip().lower()
            in _BOOLEANOS_SI
        )

    def paginate_queryset(self, queryset):
        # Los desplegables son listas cortas: sin paginación
        if self._es_desplegable():
            return None
        return super().paginate_queryset(queryset)

    def get_queryset(self):
        queryset = super().get_queryset()
        if self._es_desplegable():
            queryset = self._qs_desplegable(queryset)
        return self._qs_activo(queryset)

    def _qs_desplegable(self, queryset):
        return queryset.filter(activo=True)

    def _qs_activo(self, queryset):
        valor = self.request.query_params.get("activo")
        if valor is None:
            return queryset
        bajo = valor.strip().lower()
        if bajo in _BOOLEANOS_SI:
            return queryset.filter(activo=True)
        if bajo in _BOOLEANOS_NO:
            return queryset.filter(activo=False)
        raise ValidationError({"activo": "Use true o false."})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # Responde con el serializador de lectura (incluye id y jerarquía)
        return Response(self._lectura(serializer.instance).data, status=201)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(self._lectura(serializer.instance).data)

    def _lectura(self, obj):
        return self.serializer_class(obj, context=self.get_serializer_context())


class VistaCatalogoConEstado(VistaCatalogo):
    """Catálogos con desactivación/reactivación: nunca borrado."""

    @action(detail=True, methods=("patch",), url_path="estado")
    def estado(self, request, pk=None):
        activo = request.data.get("activo")
        if not isinstance(activo, bool):
            raise ValidationError({"activo": "Debe ser true o false."})
        objeto = self.get_object()
        self._validar_estado(objeto, activo)
        if objeto.activo != activo:
            objeto.activo = activo
            objeto.save(update_fields=("activo",))
        return Response(self.get_serializer(objeto).data)

    def _validar_estado(self, objeto, activo):
        """Gancho para las protecciones de cada catálogo."""


class CultivoViewSet(VistaCatalogoConEstado):
    queryset = Cultivo.objects.all()
    serializer_class = CultivoSerializer
    escritura_serializer = CultivoEscrituraSerializer
    desplegable_serializer = CultivoDesplegableSerializer


class VariedadViewSet(VistaCatalogoConEstado):
    queryset = Variedad.objects.select_related("cultivo")
    serializer_class = VariedadSerializer
    escritura_serializer = VariedadEscrituraSerializer
    desplegable_serializer = VariedadDesplegableSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        cultivo = self.request.query_params.get("cultivo")
        if cultivo:
            queryset = queryset.filter(
                cultivo_id=_id_numerico(cultivo, "cultivo")
            )
        return queryset

    def _qs_desplegable(self, queryset):
        return queryset.filter(activo=True, cultivo__activo=True)


class EtapaViewSet(VistaCatalogo):
    """Sin estado (se ocultan con su cultivo) y reordenar atómico que
    exige catalogos.editar (no basta con catalogos.ver)."""

    queryset = EtapaFenologica.objects.select_related("cultivo")
    serializer_class = EtapaSerializer
    escritura_serializer = EtapaEscrituraSerializer
    desplegable_serializer = EtapaDesplegableSerializer
    PERMISOS = {**PermisosCatalogo.PERMISOS, "reordenar": "catalogos.editar"}

    def get_queryset(self):
        queryset = super().get_queryset()
        cultivo = self.request.query_params.get("cultivo")
        if cultivo:
            queryset = queryset.filter(
                cultivo_id=_id_numerico(cultivo, "cultivo")
            )
        return queryset

    def _qs_desplegable(self, queryset):
        return queryset.filter(cultivo__activo=True)

    def _qs_activo(self, queryset):
        if self.request.query_params.get("activo") is not None:
            raise ValidationError({"activo": "Las etapas no tienen estado."})
        return queryset

    @action(detail=False, methods=("post",), url_path="reordenar")
    def reordenar(self, request):
        """Reordena las etapas de un cultivo de forma atómica: primero
        todas pasan a un valor temporal (+10000) y después cada una
        recibe su posición, así uq_etapa_orden nunca choca a mitad."""
        cultivo_id = request.data.get("cultivo")
        if not isinstance(cultivo_id, int) or isinstance(cultivo_id, bool):
            raise ValidationError({"cultivo": "Debe ser un id numérico."})
        posiciones = request.data.get("orden")
        if not isinstance(posiciones, list) or not posiciones:
            raise ValidationError(
                {"orden": "Debe ser la lista completa de ids de etapas."}
            )
        ids = []
        for item in posiciones:
            if not isinstance(item, int) or isinstance(item, bool):
                raise ValidationError({"orden": "Cada id debe ser un número."})
            ids.append(item)
        if len(set(ids)) != len(ids):
            raise ValidationError({"orden": "No puede repetir etapas."})
        cultivo = Cultivo.objects.filter(pk=cultivo_id).first()
        if cultivo is None:
            raise ValidationError({"cultivo": "El cultivo indicado no existe."})
        existentes = list(
            EtapaFenologica.objects.filter(cultivo=cultivo)
            .values_list("id", flat=True)
        )
        if set(ids) != set(existentes):
            raise ValidationError(
                {"orden": "Debe incluir exactamente las etapas del cultivo."}
            )
        with transaction.atomic():
            EtapaFenologica.objects.filter(cultivo=cultivo).update(
                orden=F("orden") + 10000
            )
            for posicion, etapa_id in enumerate(ids, start=1):
                EtapaFenologica.objects.filter(pk=etapa_id).update(
                    orden=posicion
                )
        etapas = EtapaFenologica.objects.filter(cultivo=cultivo)
        return Response(
            EtapaSerializer(
                etapas, many=True, context=self.get_serializer_context()
            ).data
        )


class UnidadViewSet(VistaCatalogoConEstado):
    """Catálogo de unidades. Semana 8: el factor de una unidad que ya
    tiene producciones registradas no se puede cambiar (afectaría el
    histórico convertido a kg): hay que crear otra unidad."""

    queryset = Unidad.objects.all()
    serializer_class = UnidadSerializer
    escritura_serializer = UnidadEscrituraSerializer
    desplegable_serializer = UnidadDesplegableSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        tipo = self.request.query_params.get("tipo")
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        return queryset

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if "factor_a_base" in request.data:
            nuevo = request.data.get("factor_a_base")
            if str(nuevo).strip() != str(instance.factor_a_base).strip():
                if instance.producciones.exists():
                    raise ValidationError(
                        {
                            "factor_a_base": (
                                "Esta unidad ya tiene producciones "
                                "registradas: su factor no se puede cambiar. "
                                "Cree otra unidad."
                            )
                        }
                    )
        return super().update(request, *args, **kwargs)

    def _validar_estado(self, objeto, activo):
        if objeto.es_base:
            raise ValidationError(
                {"activo": "Las unidades base no se pueden desactivar."}
            )


class TipoActividadViewSet(VistaCatalogoConEstado):
    """Sin POST ni DELETE (405): los códigos son fijos; el código no
    se envía al editar y Siembra/Cosecha no se desactivan."""

    queryset = TipoActividad.objects.all()
    serializer_class = TipoActividadSerializer
    escritura_serializer = TipoActividadEscrituraSerializer
    desplegable_serializer = TipoActividadDesplegableSerializer
    http_method_names = ("get", "put", "patch", "head", "options")
    search_fields = ("codigo", "nombre")

    def _validar_estado(self, objeto, activo):
        if not activo and objeto.codigo in ("SIEMBRA", "COSECHA"):
            raise ValidationError(
                {"activo": "Siembra y Cosecha no se pueden desactivar."}
            )


class RecursoViewSet(VistaCatalogoConEstado):
    queryset = Recurso.objects.all()
    serializer_class = RecursoSerializer
    escritura_serializer = RecursoEscrituraSerializer
    desplegable_serializer = RecursoDesplegableSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        categoria = self.request.query_params.get("categoria")
        if categoria:
            queryset = queryset.filter(categoria=categoria)
        return queryset


class TipoIncidenciaViewSet(VistaCatalogoConEstado):
    queryset = TipoIncidencia.objects.all()
    serializer_class = TipoIncidenciaSerializer
    escritura_serializer = TipoIncidenciaEscrituraSerializer
    desplegable_serializer = TipoIncidenciaDesplegableSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        categoria = self.request.query_params.get("categoria")
        if categoria:
            queryset = queryset.filter(categoria=categoria)
        return queryset


class AgenteViewSet(VistaCatalogoConEstado):
    queryset = Agente.objects.all()
    serializer_class = AgenteSerializer
    escritura_serializer = AgenteEscrituraSerializer
    desplegable_serializer = AgenteDesplegableSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        tipo = self.request.query_params.get("tipo")
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        return queryset
