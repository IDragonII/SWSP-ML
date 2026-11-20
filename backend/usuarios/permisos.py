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


# Rutas que siguen funcionando con las marcas de cambio obligatorio en
# TRUE (Semana 13, HU-112 + S24): entrar, renovar/cerrar la propia
# sesión, leer /me (para saber que hay que cambiar) y cambiarlo. El
# resto de la API queda cerrado con 403 hasta que se cambie.
RUTAS_LIBRES_CAMBIO_CLAVE = (
    '/api/auth/login/',
    '/api/auth/refresh/',
    '/api/auth/logout/',
    '/api/auth/me/',
    '/api/auth/cambiar-clave/',
)


class DebeCambiarClave(BasePermission):
    """Puerta del cambio obligatorio de credenciales (HU-112 + S24).

    Con debe_cambiar_clave (Semana 13) solo contraseña; con
    debe_cambiar_credenciales (S24, primer ingreso) usuario y
    contraseña. En ambos casos solo pasan las rutas de sesión/cambio;
    el resto responde 403 con el mensaje de su marca. Va ANTES de
    IsAuthenticated en DEFAULT_PERMISSION_CLASSES: los anónimos y las
    rutas libres siguen el resto de la cadena normal.
    """

    message = 'Debes cambiar tu contraseña antes de continuar.'

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return True  # IsAuthenticated (la siguiente) se ocupa
        if getattr(user, 'debe_cambiar_credenciales', False):
            # Instancia por petición (APIView.get_permissions): el
            # mensaje se puede ajustar aquí sin afectar a la otra marca
            self.message = 'Debes cambiar tus credenciales antes de continuar.'
            return self._ruta_libre(request)
        if not getattr(user, 'debe_cambiar_clave', False):
            return True
        self.message = 'Debes cambiar tu contraseña antes de continuar.'
        return self._ruta_libre(request)

    @staticmethod
    def _ruta_libre(request):
        ruta = request.path.rstrip('/')
        return any(ruta == ruta_libre.rstrip('/') for ruta_libre in RUTAS_LIBRES_CAMBIO_CLAVE)
