"""API de auditoría (Semana 13, RF-71/RF-72): solo lectura.

Sin POST/PATCH/DELETE (los eventos los inserta la API en el mismo
evento de negocio y un trigger los hace inmutables). Permiso
auditoria.ver (sembrado en la Semana 2; hoy solo el Administrador lo
tiene): quien no lo tiene recibe 403 y la tabla no se consulta.
"""
from rest_framework import mixins, viewsets

from productores.views import BusquedaPorNombre, PermisosPorAccion

from .models import Auditoria
from .serializers import AuditoriaSerializer


class PermisosAuditoria(PermisosPorAccion):
    """Solo consultar: auditoria.ver en listado y detalle."""

    permiso_requerido = "auditoria.ver"
    PERMISOS = {
        "list": "auditoria.ver",
        "retrieve": "auditoria.ver",
    }


class AuditoriaViewSet(
    PermisosAuditoria,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Listado pagado (20 por página, orden fecha descendente) y detalle.
    Filtros: ?usuario=ID, ?modulo=, ?accion=, ?tabla=, ?registro=ID,
    ?fecha_desde= y ?fecha_hasta=; ?busqueda= sobre módulo, acción y
    tabla."""

    queryset = Auditoria.objects.select_related("usuario")
    serializer_class = AuditoriaSerializer
    filter_backends = (BusquedaPorNombre,)
    search_fields = ("modulo", "accion", "tabla")

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        if params.get("usuario"):
            try:
                usuario_id = int(params["usuario"])
            except ValueError:
                from rest_framework.exceptions import ValidationError

                raise ValidationError({"usuario": "Debe ser un id numérico."})
            queryset = queryset.filter(usuario_id=usuario_id)
        if params.get("modulo"):
            queryset = queryset.filter(modulo=params["modulo"])
        if params.get("accion"):
            queryset = queryset.filter(accion=params["accion"])
        if params.get("tabla"):
            queryset = queryset.filter(tabla=params["tabla"])
        if params.get("registro"):
            try:
                registro_id = int(params["registro"])
            except ValueError:
                from rest_framework.exceptions import ValidationError

                raise ValidationError({"registro": "Debe ser un id numérico."})
            queryset = queryset.filter(registro_id=registro_id)
        if params.get("fecha_desde"):
            queryset = queryset.filter(fecha__date__gte=params["fecha_desde"])
        if params.get("fecha_hasta"):
            queryset = queryset.filter(fecha__date__lte=params["fecha_hasta"])
        return queryset
