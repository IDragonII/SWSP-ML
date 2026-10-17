"""API de ubicación y productores (Semana 3) y de parcelas (Semana 4).

Ubicación: provincias, distritos y comunidades — listar, ver detalle,
crear, editar y desactivar/reactivar. Productores: además, alta con código
automático, validación de DNI, búsqueda general, filtros por jerarquía y
estado, y DNI/teléfono enmascarados por rol. Parcelas: alta con código
P-00N, validaciones de terreno, filtros por jerarquía/productor/estado y
desactivación sin borrar.

Ningún recurso ofrece borrado: la API no ofrece DELETE (decisión 6 de
docs/decisiones_semana3.md). La paginación es global (20 por página,
API_PAGE_SIZE) y el orden de productores es por apellidos.
"""
from django.db import transaction
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.response import Response

from campanias.models import Campania
from usuarios.models import Usuario
from usuarios.permisos import DebeCambiarClave, TienePermiso

from auditoria.mixins import AuditoriaMixin

from .models import AsignacionTecnico, Comunidad, Distrito, Parcela, Productor, Provincia
from .serializers import (
    AsignacionEscrituraSerializer,
    AsignacionSerializer,
    ComunidadEscrituraSerializer,
    ComunidadSerializer,
    DistritoEscrituraSerializer,
    DistritoSerializer,
    ParcelaDetalleSerializer,
    ParcelaDesplegableSerializer,
    ParcelaEscrituraSerializer,
    ParcelaListaSerializer,
    ProductorDetalleSerializer,
    ProductorDesplegableSerializer,
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


class SoloSusProductores:
    """Filtro «solo mis productores» (decisión 6 de la Semana 4).

    Solo aplica a los roles con limita_a_asignados (Técnico de campo): su
    queryset queda reducido a los productores con una asignación ACTIVA.
    Como todo detalle/edición pasa por get_queryset, un productor ajeno
    responde 404 —nunca 403— y el listado solo muestra los suyos.
    Los demás roles (Administrador, Coordinador) no se ven limitados.
    """

    def _filtrar_asignados(self, queryset, campo="pk"):
        rol = getattr(self.request.user, "rol", None)
        if rol is None or not rol.limita_a_asignados:
            return queryset
        asignados = AsignacionTecnico.objects.filter(
            tecnico=self.request.user, activo=True
        ).values("productor_id")
        return queryset.filter(**{f"{campo}__in": asignados})


class PermisosPorAccion:
    """Asigna permiso_requerido según la acción (PERMISOS) y exige con
    la clase TienePermiso de la Semana 2.

    get_permissions() sustituye a la cadena por defecto, así que la
    puerta del cambio obligatorio de contraseña (HU-112, Semana 13) se
    antepone AQUÍ: con debe_cambiar_clave en TRUE, todo endpoint que
    escribe o lee datos responde 403 hasta cambiarla."""

    permiso_requerido = None
    PERMISOS = {}

    def get_permissions(self):
        self.permiso_requerido = self.PERMISOS.get(
            self.action, self.permiso_requerido
        )
        return [DebeCambiarClave(), TienePermiso()]


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
            with transaction.atomic():
                objeto.activo = activo
                objeto.save(update_fields=("activo",))
                self._registrar_auditoria(
                    "ACTIVAR" if activo else "DESACTIVAR", objeto
                )
        return Response(self.get_serializer(objeto).data)


class _VistaUbicacion(
    AuditoriaMixin,
    FiltrosUbicacion,
    PermisosCatalogo,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Sin DestroyModelMixin: DELETE responde 405 (decisión 6)."""

    auditoria_modulo = "ubicacion"
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
    AuditoriaMixin,
    PermisosProductor,
    SoloSusProductores,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Alta/edición sin DELETE (405). El código lo genera la base de datos
    y creado_por lo pone el servidor; ambos se releen tras guardar."""

    auditoria_modulo = "productores"
    queryset = Productor.objects.select_related(
        "comunidad",
        "comunidad__distrito",
        "comunidad__distrito__provincia",
        "creado_por",
    )
    serializer_class = ProductorDetalleSerializer
    escritura_serializer = ProductorEscrituraSerializer
    desplegable_serializer = ProductorDesplegableSerializer
    filter_backends = (BusquedaPorNombre,)
    search_fields = ("codigo", "nombres", "apellidos", "dni")

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
            return ProductorListaSerializer
        return self.serializer_class

    def paginate_queryset(self, queryset):
        # Los desplegables son listas cortas: sin paginación
        if self._es_desplegable():
            return None
        return super().paginate_queryset(queryset)

    def get_queryset(self):
        queryset = self._filtrar_asignados(super().get_queryset())
        if self._es_desplegable():
            # El selector de actividades solo ofrece productores activos
            queryset = queryset.filter(estado=Productor.ESTADO_ACTIVO)
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
        # Decisión 4: si el alta la hace un técnico, su asignación se crea
        # en la MISMA transacción: o se hace todo o no se hace nada. Si la
        # hace el Administrador, no se asigna a nadie.
        with transaction.atomic():
            productor = serializer.save(creado_por=self.request.user)
            rol = getattr(self.request.user, "rol", None)
            if rol is not None and rol.limita_a_asignados:
                AsignacionTecnico.objects.create(
                    tecnico=self.request.user, productor=productor
                )
            self._registrar_auditoria("CREAR", productor)

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
        """Desactiva o reactiva sin perder datos (decisión 6). Desde la
        Semana 6 no se desactiva un productor con campañas activas
        (HU-46; decisión pendiente de confirmar con el responsable:
        docs/decisiones_semana6.md)."""
        valor = request.data.get("estado")
        if valor not in ("ACTIVO", "INACTIVO"):
            raise ValidationError({"estado": "Use ACTIVO o INACTIVO."})
        productor = self.get_object()
        if valor == "INACTIVO":
            activas = Campania.objects.filter(
                parcela__productor=productor, estado__in=Campania.ESTADOS_ACTIVOS
            )
            if activas.exists():
                primera = activas.first()
                raise ValidationError(
                    {
                        "estado": (
                            f"No se puede desactivar el productor: tiene "
                            f"{activas.count()} campaña(s) activa(s) "
                            f"(id {primera.pk}, {primera.periodo}). Cancela o "
                            "cierra esas campañas primero."
                        )
                    }
                )
        if productor.estado != valor:
            with transaction.atomic():
                productor.estado = valor
                productor.save(update_fields=("estado",))
                self._registrar_auditoria(
                    "ACTIVAR" if valor == "ACTIVO" else "DESACTIVAR", productor
                )
            productor.refresh_from_db()
        return Response(self._detalle(productor).data)

    def _detalle(self, obj):
        return ProductorDetalleSerializer(obj, context=self.get_serializer_context())


class PermisosParcela(PermisosPorAccion):
    """Permisos de parcelas: parcelas.ver/crear/editar/desactivar."""

    permiso_requerido = "parcelas.ver"
    PERMISOS = {
        "list": "parcelas.ver",
        "retrieve": "parcelas.ver",
        "create": "parcelas.crear",
        "update": "parcelas.editar",
        "partial_update": "parcelas.editar",
        "estado": "parcelas.desactivar",
    }


class ParcelaViewSet(
    AuditoriaMixin,
    PermisosParcela,
    SoloSusProductores,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Alta/edición sin DELETE (405). El código P-00N lo genera la base de
    datos y creado_por lo pone el servidor; ambos se releen tras guardar.
    El productor de una parcela existente no se puede cambiar (decisión 1)."""

    auditoria_modulo = "parcelas"
    queryset = Parcela.objects.select_related(
        "productor",
        "comunidad",
        "comunidad__distrito",
        "comunidad__distrito__provincia",
        "creado_por",
    )
    serializer_class = ParcelaDetalleSerializer
    escritura_serializer = ParcelaEscrituraSerializer
    desplegable_serializer = ParcelaDesplegableSerializer
    filter_backends = (BusquedaPorNombre,)
    search_fields = (
        "codigo",
        "referencia_ubicacion",
        "productor__nombres",
        "productor__apellidos",
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
            return ParcelaListaSerializer
        return self.serializer_class

    def paginate_queryset(self, queryset):
        # Los desplegables son listas cortas: sin paginación
        if self._es_desplegable():
            return None
        return super().paginate_queryset(queryset)

    def get_queryset(self):
        queryset = self._filtrar_asignados(super().get_queryset(), "productor_id")
        if self._es_desplegable():
            # El selector de campañas solo ofrece parcelas activas
            queryset = queryset.filter(estado=Parcela.ESTADO_ACTIVA)
        params = self.request.query_params
        if params.get("productor"):
            queryset = queryset.filter(
                productor_id=_id_numerico(params["productor"], "productor")
            )
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
            if estado not in ("ACTIVA", "INACTIVA"):
                raise ValidationError({"estado": "Use ACTIVA o INACTIVA."})
            queryset = queryset.filter(estado=estado)
        return queryset

    def perform_create(self, serializer):
        with transaction.atomic():
            parcela = serializer.save(creado_por=self.request.user)
            self._registrar_auditoria("CREAR", parcela)

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
        """Desactiva o reactiva sin perder datos (decisión 3). Desde la
        Semana 6 no se desactiva una parcela con campaña activa (HU-45);
        con solo campañas canceladas sí se puede."""
        valor = request.data.get("estado")
        if valor not in ("ACTIVA", "INACTIVA"):
            raise ValidationError({"estado": "Use ACTIVA o INACTIVA."})
        parcela = self.get_object()
        if valor == "INACTIVA":
            activa = parcela.campanias.filter(
                estado__in=Campania.ESTADOS_ACTIVOS
            ).first()
            if activa is not None:
                raise ValidationError(
                    {
                        "estado": (
                            f"No se puede desactivar la parcela: tiene una "
                            f"campaña activa (id {activa.pk}, {activa.periodo}, "
                            f"{activa.cultivo.nombre}). Cancela esa campaña "
                            "primero."
                        )
                    }
                )
        if parcela.estado != valor:
            with transaction.atomic():
                parcela.estado = valor
                parcela.save(update_fields=("estado",))
                self._registrar_auditoria(
                    "ACTIVAR" if valor == "ACTIVA" else "DESACTIVAR", parcela
                )
            parcela.refresh_from_db()
        return Response(self._detalle(parcela).data)

    def _detalle(self, obj):
        return ParcelaDetalleSerializer(obj, context=self.get_serializer_context())


class PermisosAsignacion(PermisosPorAccion):
    """Gestionar asignaciones: solo quien tiene asignaciones.gestionar
    (Administrador). Técnico y Coordinador reciben 403 en todas las
    acciones de /api/asignaciones/."""

    permiso_requerido = "asignaciones.gestionar"
    PERMISOS = {}


class AsignacionViewSet(
    AuditoriaMixin,
    PermisosAsignacion,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Alta y consulta de asignaciones de técnico (decisiones 5 y 8).

    Sin PUT/PATCH completos ni DELETE (405): reasignar = desactivar +
    crear otra y nada se borra. El estado se cambia con
    PATCH /{id}/estado/ {"activo": true|false}.
    Filtros: ?tecnico=ID y ?productor=ID.
    """

    auditoria_modulo = "asignaciones"
    queryset = AsignacionTecnico.objects.select_related("tecnico", "productor")
    serializer_class = AsignacionSerializer

    def get_serializer_class(self):
        if self.action == "create":
            return AsignacionEscrituraSerializer
        return AsignacionSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        if params.get("tecnico"):
            queryset = queryset.filter(
                tecnico_id=_id_numerico(params["tecnico"], "tecnico")
            )
        if params.get("productor"):
            queryset = queryset.filter(
                productor_id=_id_numerico(params["productor"], "productor")
            )
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            asignacion = serializer.save()
            self._registrar_auditoria("ASIGNAR", asignacion)
        # Responde con el serializador de lectura (con id y anidados)
        return Response(
            AsignacionSerializer(
                asignacion, context=self.get_serializer_context()
            ).data,
            status=201,
        )

    @action(detail=True, methods=("patch",), url_path="estado")
    def estado(self, request, pk=None):
        """Desactivar o reactivar sin perder el registro (decisión 5)."""
        activo = request.data.get("activo")
        if not isinstance(activo, bool):
            raise ValidationError({"activo": "Debe ser true o false."})
        asignacion = self.get_object()
        if asignacion.activo != activo:
            with transaction.atomic():
                asignacion.activo = activo
                asignacion.save(update_fields=("activo",))
                self._registrar_auditoria(
                    "ASIGNAR" if activo else "DESASIGNAR", asignacion
                )
        return Response(
            AsignacionSerializer(
                asignacion, context=self.get_serializer_context()
            ).data
        )

    @action(detail=False, methods=("get",), url_path="tecnicos-disponibles")
    def tecnicos_disponibles(self, request):
        """Usuarios activos cuyo rol tiene limita_a_asignados: la API solo
        ofrece técnicos válidos (el trigger sería la red de seguridad)."""
        usuarios = (
            Usuario.objects.filter(is_active=True, rol__limita_a_asignados=True)
            .select_related("rol")
            .order_by("username")
        )
        return Response(
            [
                {
                    "id": u.id,
                    "username": u.username,
                    "nombre_completo": u.get_full_name() or u.username,
                }
                for u in usuarios
            ]
        )
