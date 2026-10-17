"""Autenticación JWT por cookie httpOnly o cabecera Authorization.

Decisión: los tokens viven en cookies httpOnly (docs/decisiones_seguridad.md §2);
la cabecera "Bearer" se acepta también para clientes nativos (curl, pruebas).

Semana 12: los tokens se invalidan también por MARCAS de sesión. Restablecer
la contraseña o desactivar la cuenta guarda en caché el instante del cambio
(marca `sigpa:sesion-cambiada:{id}`); todo token (access o refresh) emitido
antes de ese instante deja de servir aunque su firma y su exp sigan
válidos — es la única forma de cerrar las sesiones abiertas sin una lista
blanca por token, que el diseño no contempla. La marca caduca al vencer el
refresh (7 días): pasado ese tiempo el token viejo ya no sirve de todos
modos.
"""
import time
from datetime import datetime

from django.conf import settings
from django.core.cache import cache
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

COOKIE_ACCESS = 'sigpa_access'
COOKIE_REFRESH = 'sigpa_refresh'
RUTA_COOKIE_REFRESH = '/api/auth/'

PREFIJO_SESION = 'sigpa:sesion-cambiada:'


class AutenticacionJWT(JWTAuthentication):
    """Igual que JWTAuthentication, pero si no hay cabecera usa la cookie de acceso."""

    def authenticate(self, request):
        header = self.get_header(request)
        if header:
            return super().authenticate(request)
        bruto = request.COOKIES.get(COOKIE_ACCESS)
        if not bruto:
            return None
        validado = self.get_validated_token(bruto)
        return self.get_user(validado), validado

    def get_user(self, validated_token):
        """Además de lo que hace simplejwt (usuario inactivo → 401), un
        token emitido antes de la última marca de sesión ya no vale."""
        usuario = super().get_user(validated_token)
        if sesion_cambiada_despues(usuario.pk, validated_token.payload.get('iat')):
            raise AuthenticationFailed(
                'Sesión cerrada por cambio de credenciales.', code='token_not_valid'
            )
        return usuario


def _duracion_refresh():
    lifetime = settings.SIMPLE_JWT.get('REFRESH_TOKEN_LIFETIME')
    if hasattr(lifetime, 'total_seconds'):
        return int(lifetime.total_seconds())
    return 7 * 24 * 3600


def marcar_sesion_cambiada(user_id):
    """Invalida todos los tokens del usuario emitidos hasta ahora."""
    cache.set(PREFIJO_SESION + str(user_id), time.time(), timeout=_duracion_refresh())


def esperar_tras_marca(user_id):
    """Espera, como mucho ~1 s, a que arranque el segundo siguiente a la
    última marca de sesión (Semana 13).

    El iat de los tokens tiene precisión de segundo y la marca guarda la
    fracción: un token emitido en el mismo segundo que la marca se daría
    por anterior y la siguiente petición recibiría 401. Se usa justo
    antes de emitir cookies nuevas (login o cambio de contraseña
    propio) para que el recién emitido sí sea válido."""
    marca = cache.get(PREFIJO_SESION + str(user_id))
    if marca is None:
        return
    espera = (int(marca) + 1) - time.time() + 0.02
    if 0 < espera <= 1.2:
        time.sleep(espera)


def sesion_cambiada_despues(user_id, iat):
    """True si el token es anterior a la última marca de sesión (Semana 12).

    iat puede llegar como datetime (simplejwt) o como número; sin marca o
    sin iat, el token no se toca (quien lo valide es la firma y la exp)."""
    if user_id is None:
        return False
    marca = cache.get(PREFIJO_SESION + str(user_id))
    if marca is None or iat is None:
        return False
    if isinstance(iat, datetime):
        iat = iat.timestamp()
    return float(iat) < marca


def fijar_cookies_auth(response, access, refresh=None):
    """Fija las cookies httpOnly de sesión en la respuesta (login/refresh)."""
    response.set_cookie(
        COOKIE_ACCESS,
        str(access),
            max_age=int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
        httponly=True,
        samesite='Lax',
        secure=settings.JWT_COOKIE_SECURE,
        path='/',
    )
    if refresh is not None:
        response.set_cookie(
            COOKIE_REFRESH,
            str(refresh),
            max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
            httponly=True,
            samesite='Lax',
            secure=settings.JWT_COOKIE_SECURE,
            path=RUTA_COOKIE_REFRESH,
        )
    return response


def limpiar_cookies_auth(response):
    """Borra las cookies de sesión (logout)."""
    response.delete_cookie(COOKIE_ACCESS, path='/', samesite='Lax')
    response.delete_cookie(COOKIE_REFRESH, path=RUTA_COOKIE_REFRESH, samesite='Lax')
    return response
