"""API de auditoría (Semana 13, RF-71/RF-72): solo lectura.

Sin POST/PATCH/DELETE (los eventos los inserta la API en el mismo
evento de negocio y un trigger los hace inmutables). Permiso
auditoria.ver (sembrado en la Semana 2; hoy solo el Administrador lo
tiene): quien no lo tiene recibe 403 y la tabla no se consulta.

Los filtros viven en auditoria.filtros (Semana 18): la misma función
los aplica aquí y en el reporte de auditoría.
"""
from rest_framework import mixins, viewsets

from productores.views import BusquedaPorNombre, PermisosPorAccion

from .filtros import aplicar_filtros
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
    ?ip=, ?fecha_desde= y ?fecha_hasta=; ?busqueda= sobre módulo, acción
    y tabla."""

    queryset = Auditoria.objects.select_related("usuario")
    serializer_class = AuditoriaSerializer
    filter_backends = (BusquedaPorNombre,)
    search_fields = ("modulo", "accion", "tabla")

    def get_queryset(self):
        return aplicar_filtros(super().get_queryset(), self.request.query_params)
