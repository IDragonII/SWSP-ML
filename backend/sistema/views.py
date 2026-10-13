"""API de parámetros del sistema (Semana 8): umbrales configurables.

Listar y editar el valor de una clave fija. Todo con parametros.gestionar
(hoy solo del Administrador; el menú solo muestra la pantalla con ese
permiso). La clave no se crea ni se borra: nace con la migración 0001.
fn_validar_produccion lee los umbrales en cada INSERT/UPDATE, por lo que
cambiar un valor NO reevalúa las producciones ya marcadas (solo afectan a
las siguientes).
"""
from rest_framework import mixins, viewsets
from rest_framework.response import Response

from productores.views import PermisosPorAccion

from .models import ParametroSistema
from .serializers import ParametroEscrituraSerializer, ParametroSerializer


class PermisosParametro(PermisosPorAccion):
    """Parámetros: parametros.gestionar para leer y para editar."""

    permiso_requerido = "parametros.gestionar"
    PERMISOS = {
        "list": "parametros.gestionar",
        "retrieve": "parametros.gestionar",
        "partial_update": "parametros.gestionar",
    }


class ParametroViewSet(
    PermisosParametro,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Sin CREATE ni DELETE (405): las claves son fijas; por la API solo
    cambia el valor, con PATCH /api/parametros/{clave}/."""

    queryset = ParametroSistema.objects.all()
    serializer_class = ParametroSerializer
    escritura_serializer = ParametroEscrituraSerializer
    lookup_field = "clave"
    lookup_url_regex = r"[^/.]+"
    http_method_names = ("get", "patch", "head", "options")

    def get_serializer_class(self):
        if self.action == "partial_update":
            return self.escritura_serializer
        return self.serializer_class

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # trg_parametros_sistema_actualizado fija actualizado_en
        instance.refresh_from_db(fields=("valor", "actualizado_en"))
        return Response(ParametroSerializer(instance).data)
