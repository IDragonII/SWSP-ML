"""Autenticación JWT por cookie httpOnly o cabecera Authorization.

Decisión: los tokens viven en cookies httpOnly (docs/decisiones_seguridad.md §2);
la cabecera "Bearer" se acepta también para clientes nativos (curl, pruebas).
"""
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication

COOKIE_ACCESS = 'sigpa_access'
COOKIE_REFRESH = 'sigpa_refresh'
RUTA_COOKIE_REFRESH = '/api/auth/'


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
