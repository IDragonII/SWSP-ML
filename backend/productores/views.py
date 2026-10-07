"""API de ubicación y productores (Semana 3).

Ubicación: provincias, distritos y comunidades — listar, ver detalle,
crear, editar y desactivar/reactivar. Productores: además, alta con código
automático, validación de DNI, búsqueda general, filtros por jerarquía y
estado, y DNI/teléfono enmascarados por rol.

Ningún recurso ofrece borrado: la API no ofrece DELETE (decisión 6 de
docs/decisiones_semana3.md). La paginación es global (20 por página,
API_PAGE_SIZE) y el orden de productores es por apellidos.
"""
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.response import Response

from usuarios.permisos import TienePermiso

from .models import Comunidad, Distrito, Productor, Provincia
from .serializers import (
    ComunidadEscrituraSerializer,
    ComunidadSerializer,
    DistritoEscrituraSerializer,
    DistritoSerializer,
    ProductorDetalleSerializer,
    ProductorEscrituraSerializer,
    ProductorListaSerializer,
    ProvinciaSerializer,
)

_BOOLEANOS_SI = ("1", "true", "yes", "si", "sí", "verdadero")
_BOOLEANOS_NO = ("0", "false", "no", "falso")


def _id_numerico(parametro, campo):
    if not parametro.isdigit():
        raise ValidationError({campo: "Debe ser un id numérico."})
    return int(parametro)


class BusquedaPorNombre(SearchFilter):
    """?busqueda=... (en vez del ?search= por defecto de DRF)."""

    search_param = "busqueda"


class PermisosPorAccion:
    """Asigna permiso_requerido según la acción (PERMISOS) y exige con
    la clase TienePermiso de la Semana 2."""

    permiso_requerido = None
    PERMISOS = {}

    def get_permissions(self):
        self.permiso_requerido = self.PERMISOS.get(
            self.action, self.permiso_requerido
        )
        return [TienePermiso()]


class PermisosCatalogo(PermisosPorAccion):
    """Permisos de ubicación: catalogos.ver/crear/editar/desactivar."""

    permiso_requerido = "catalogos.ver"
    PERMISOS = {
        "list": "catalogos.ver",
        "retrieve": "catalogos.ver",
        "create": "catalogos.crear",
        "update": "catalogos.editar",
        "partial_update": "catalogos.editar",
        "estado": "catalogos.desactivar",
    }


class PermisosProductor(PermisosPorAccion):
    """Permisos de productores: productores.ver/crear/editar/desactivar."""

    permiso_requerido = "productores.ver"
    PERMISOS = {
        "list": "productores.ver",
        "retrieve": "productores.ver",
        "create": "productores.crear",
        "update": "productores.editar",
        "partial_update": "productores.editar",
        "estado": "productores.desactivar",
    }


class FiltrosUbicacion:
    """?activo=true|false y, según el recurso, ?provincia= o ?distrito=."""

    filter_backends = (BusquedaPorNombre,)
    search_fields = ("nombre",)

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

    @action(detail=True, methods=("patch",), url_path="estado")
    def estado(self, request, pk=None):
        """Desactiva o reactiva (decisión 3: nunca se borra nada)."""
        activo = request.data.get("activo")
        if not isinstance(activo, bool):
            raise ValidationError({"activo": "Debe ser true o false."})
        objeto = self.get_object()
        if objeto.activo != activo:
            objeto.activo = activo
            objeto.save(update_fields=("activo",))
        return Response(self.get_serializer(objeto).data)


class _VistaUbicacion(
    FiltrosUbicacion,
    PermisosCatalogo,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Sin DestroyModelMixin: DELETE responde 405 (decisión 6)."""

    escritura_serializer = None

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return self.escritura_serializer
        return self.serializer_class

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


class ProvinciaViewSet(_VistaUbicacion):
    queryset = Provincia.objects.all()
    serializer_class = ProvinciaSerializer
    escritura_serializer = ProvinciaSerializer

    def get_queryset(self):
        return self._qs_activo(super().get_queryset())


class DistritoViewSet(_VistaUbicacion):
    queryset = Distrito.objects.select_related("provincia")
    serializer_class = DistritoSerializer
    escritura_serializer = DistritoEscrituraSerializer

    def get_queryset(self):
        queryset = self._qs_activo(super().get_queryset())
        provincia = self.request.query_params.get("provincia")
        if provincia:
            queryset = queryset.filter(
                provincia_id=_id_numerico(provincia, "provincia")
            )
        return queryset


class ComunidadViewSet(_VistaUbicacion):
    queryset = Comunidad.objects.select_related("distrito", "distrito__provincia")
    serializer_class = ComunidadSerializer
    escritura_serializer = ComunidadEscrituraSerializer

    def get_queryset(self):
        queryset = self._qs_activo(super().get_queryset())
        distrito = self.request.query_params.get("distrito")
        if distrito:
            queryset = queryset.filter(
                distrito_id=_id_numerico(distrito, "distrito")
            )
        return queryset


class ProductorViewSet(
    PermisosProductor,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Alta/edición sin DELETE (405). El código lo genera la base de datos
    y creado_por lo pone el servidor; ambos se releen tras guardar."""

    queryset = Productor.objects.select_related(
        "comunidad",
        "comunidad__distrito",
        "comunidad__distrito__provincia",
        "creado_por",
    )
    serializer_class = ProductorDetalleSerializer
    escritura_serializer = ProductorEscrituraSerializer
    filter_backends = (BusquedaPorNombre,)
    search_fields = ("codigo", "nombres", "apellidos", "dni")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return self.escritura_serializer
        if self.action == "list":
            return ProductorListaSerializer
        return self.serializer_class

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        if params.get("comunidad"):
            queryset = queryset.filter(
                comunidad_id=_id_numerico(params["comunidad"], "comunidad")
            )
        if params.get("distrito"):
            queryset = queryset.filter(
                comunidad__distrito_id=_id_numerico(params["distrito"], "distrito")
            )
        if params.get("provincia"):
            queryset = queryset.filter(
                comunidad__distrito__provincia_id=_id_numerico(
                    params["provincia"], "provincia"
                )
            )
        estado = params.get("estado")
        if estado:
            if estado not in ("ACTIVO", "INACTIVO"):
                raise ValidationError({"estado": "Use ACTIVO o INACTIVO."})
            queryset = queryset.filter(estado=estado)
        return queryset

    def perform_create(self, serializer):
        serializer.save(creado_por=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # El trigger rellena el código después del INSERT
        serializer.instance.refresh_from_db()
        return Response(self._detalle(serializer.instance).data, status=201)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        # El trigger mantiene actualizado_en: se releen las fechas
        serializer.instance.refresh_from_db()
        return Response(self._detalle(serializer.instance).data)

    @action(detail=True, methods=("patch",), url_path="estado")
    def estado(self, request, pk=None):
        """Desactiva o reactiva sin perder datos (decisión 6)."""
        valor = request.data.get("estado")
        if valor not in ("ACTIVO", "INACTIVO"):
            raise ValidationError({"estado": "Use ACTIVO o INACTIVO."})
        productor = self.get_object()
        if productor.estado != valor:
            productor.estado = valor
            productor.save(update_fields=("estado",))
            productor.refresh_from_db()
        return Response(self._detalle(productor).data)

    def _detalle(self, obj):
        return ProductorDetalleSerializer(obj, context=self.get_serializer_context())
