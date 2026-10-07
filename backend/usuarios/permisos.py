"""Clase de permisos reutilizable de la API (Semana 2).

Cada vista declara el código que exige y la clase lo busca en roles_permisos
a través del rol del usuario. El superusuario se rige por su rol
(docs/decisiones_seguridad.md §7): no hay atajos para is_superuser.

Los códigos del usuario se resuelven UNA sola vez por petición y se guardan
en el objeto request; cualquier comprobación posterior reutiliza esa lista
sin consultar de nuevo (docs/decisiones_seguridad.md §7).

Uso en cualquier vista futura:
    class MiVista(APIView):
        permiso_requerido = 'productores.crear'
        permission_classes = (TienePermiso,)
"""
from rest_framework.permissions import BasePermission

from .models import RolPermiso


def permisos_de_peticion(request):
    """Códigos de permiso del usuario de la petición (máx. 1 consulta por petición)."""
    permisos = getattr(request, '_permisos_sigpa', None)
    if permisos is None:
        permisos = set()
        rol_id = getattr(request.user, 'rol_id', None)
        if rol_id is not None:
            permisos = set(
                RolPermiso.objects.filter(rol_id=rol_id)
                .values_list('permiso__codigo', flat=True)
            )
        request._permisos_sigpa = permisos
    return permisos


class TienePermiso(BasePermission):
    """Exige el código declarado en la vista (atributo `permiso_requerido`).

    Anónimo -> 401; autenticado sin el permiso -> 403.
    """

    message = 'No tienes permiso para realizar esta acción.'

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        codigo = getattr(view, 'permiso_requerido', None)
        if not codigo:
            return False
        return codigo in permisos_de_peticion(request)
